"""会员端刀版买断与下载。"""

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from rest_framework.views import APIView

from apps.points.services import spend_points
from apps.simplequote.dieline_engines import build_segments_by_engine
from apps.simplequote.dieline_export import (
    calibrate_fixed_segments,
    normalize_fixed_segments,
    segments_to_ai_bytes,
    segments_to_dxf,
    segments_to_pdf_bytes,
)
from apps.simplequote.models import DielineTemplate, DielineTemplatePurchase
from apps.simplequote.packaging import PaperBoxGeometryError, unfold_by_code
from apps.simplequote.serializers import DielineTemplatePurchaseSerializer
from core.pagination import StandardPagination
from core.permissions import IsBuyerRole, IsEmailVerified
from core.responses import error_response, success_response


def _resolve_template(code):
    return (
        DielineTemplate.objects.filter(code=str(code or "").strip(), is_active=True)
        .prefetch_related("assets")
        .first()
    )


def _build_formula_segments(template, length_mm, width_mm, height_mm, thickness_mm, dimension_type):
    geo = unfold_by_code(
        template.code,
        length_mm,
        width_mm,
        height_mm,
        thickness_mm,
        dimension_type,
    )
    geometry = {
        "manufacturing": {
            "length": geo["manufacturing_length_mm"],
            "width": geo["manufacturing_width_mm"],
            "height": geo["manufacturing_height_mm"],
        },
        "thickness_mm": geo["thickness_mm"],
        "glue_tab_mm": geo["glue_tab_mm"],
    }
    flap_gap = template.flap_gap_mm
    return (
        build_segments_by_engine(
            template.engine_key,
            geometry,
            flap_gap_mm=float(flap_gap) if flap_gap is not None else None,
        ),
        geo,
    )


def _build_fixed_segments(template):
    asset = template.assets.filter(is_active=True).first()
    if not asset:
        raise PaperBoxGeometryError("固定图纸模板未配置可用资产")
    entities = (asset.parsed_geometry or {}).get("entities") or []
    cal_w = float(asset.calibrated_width_mm or 0)
    cal_h = float(asset.calibrated_height_mm or 0)
    if cal_w > 0 and cal_h > 0:
        return calibrate_fixed_segments(entities, cal_w, cal_h)
    return normalize_fixed_segments(entities)


class MemberDielinePurchaseListCreateView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsBuyerRole(), IsEmailVerified()]
        return [IsBuyerRole()]

    def get(self, request):
        qs = (
            DielineTemplatePurchase.objects.filter(user=request.user)
            .select_related("template")
            .order_by("-created_at")
        )
        code = request.query_params.get("template_code")
        if code:
            qs = qs.filter(template__code=code)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            DielineTemplatePurchaseSerializer(page, many=True).data
        )

    def post(self, request):
        code = str(request.data.get("template_code") or "").strip()
        if not code:
            return error_response(
                "DIELINE_TEMPLATE_NOT_AVAILABLE",
                "缺少 template_code",
                request=request,
            )
        template = _resolve_template(code)
        if not template or not template.purchase_enabled:
            return error_response(
                "DIELINE_TEMPLATE_NOT_AVAILABLE",
                "模板不可购买或不存在",
                request=request,
            )

        existing = DielineTemplatePurchase.objects.filter(
            user=request.user, template=template
        ).first()
        if existing:
            return success_response(
                {
                    **DielineTemplatePurchaseSerializer(existing).data,
                    "already_unlocked": True,
                },
                message="已解锁",
                request=request,
            )

        cost = int(template.points_cost or 0)
        try:
            with transaction.atomic():
                purchase = DielineTemplatePurchase.objects.create(
                    user=request.user,
                    template=template,
                    points_spent=cost,
                )
                tx = spend_points(
                    request.user,
                    cost,
                    source_type="dieline_purchase",
                    source_id=purchase.id,
                    description=f"解锁刀版模板 {template.code}",
                )
                if tx:
                    purchase.transaction_no = tx.transaction_no
                    purchase.save(update_fields=["transaction_no"])
        except IntegrityError:
            existing = DielineTemplatePurchase.objects.filter(
                user=request.user, template=template
            ).first()
            if existing:
                return success_response(
                    {
                        **DielineTemplatePurchaseSerializer(existing).data,
                        "already_unlocked": True,
                    },
                    message="已解锁",
                    request=request,
                )
            raise

        return success_response(
            {
                **DielineTemplatePurchaseSerializer(purchase).data,
                "already_unlocked": False,
            },
            message="解锁成功",
            request=request,
        )


class MemberDielineTemplateDownloadView(APIView):
    permission_classes = [IsBuyerRole, IsEmailVerified]

    def get(self, request, code):
        template = _resolve_template(code)
        if not template:
            return error_response(
                "DIELINE_TEMPLATE_NOT_AVAILABLE",
                "模板不存在",
                request=request,
            )

        purchased = DielineTemplatePurchase.objects.filter(
            user=request.user, template=template
        ).exists()
        # Free templates (0 points) still require an unlock record for audit,
        # but allow download if purchase_enabled and points_cost==0 after auto-check.
        if not purchased:
            if int(template.points_cost or 0) == 0 and template.purchase_enabled:
                # Auto-create free unlock
                DielineTemplatePurchase.objects.get_or_create(
                    user=request.user,
                    template=template,
                    defaults={"points_spent": 0},
                )
            else:
                return error_response(
                    "DIELINE_NOT_PURCHASED",
                    "请先解锁该刀版模板",
                    status=403,
                    request=request,
                )

        fmt = str(request.query_params.get("format") or "dxf").lower().strip()
        if fmt not in {"dxf", "pdf", "ai"}:
            return error_response(
                "DIELINE_FORMAT_INVALID",
                "仅支持 format=dxf|pdf|ai",
                request=request,
            )

        mode = template.resolve_geometry_mode()
        try:
            if mode == "formula":
                try:
                    length_mm = float(request.query_params.get("length_mm"))
                    width_mm = float(request.query_params.get("width_mm"))
                    height_mm = float(request.query_params.get("height_mm"))
                    thickness_mm = float(request.query_params.get("thickness_mm") or template.default_thickness_mm or 1.5)
                except (TypeError, ValueError):
                    return error_response(
                        "DIELINE_DIMS_OUT_OF_RANGE",
                        "公式模板下载须提供 length_mm/width_mm/height_mm",
                        request=request,
                    )
                dimension_type = str(
                    request.query_params.get("dimension_type")
                    or template.default_dimension_type
                    or "internal"
                )
                segments, _geo = _build_formula_segments(
                    template, length_mm, width_mm, height_mm, thickness_mm, dimension_type
                )
            else:
                segments = _build_fixed_segments(template)
        except (PaperBoxGeometryError, ValueError) as exc:
            code_name = (
                "DIELINE_DIMS_OUT_OF_RANGE"
                if "不能" in str(exc) or "范围" in str(exc) or "小于" in str(exc) or "超过" in str(exc)
                else "DIELINE_TEMPLATE_NOT_AVAILABLE"
            )
            return error_response(code_name, str(exc), request=request)

        filename = f"dieline-{template.code}.{fmt}"
        if fmt == "dxf":
            content = segments_to_dxf(segments)
            response = HttpResponse(content, content_type="application/dxf")
        elif fmt == "ai":
            content = segments_to_ai_bytes(segments)
            response = HttpResponse(content, content_type="application/postscript")
        else:
            content = segments_to_pdf_bytes(segments)
            response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response