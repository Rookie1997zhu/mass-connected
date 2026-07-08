import os
import tempfile
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.rfq.models import RFQ, ServiceCategory
from apps.simplequote.calculator import (
    InjectionQuoteError,
    PaperBoxQuoteError,
    PcbaQuoteError,
    PcbQuoteError,
    build_param_map,
    calculate,
    weight_from_volume,
)
from apps.simplequote.geometry import parse_step
from apps.simplequote.dieline_import import (
    DielineImportError,
    default_mapping_schema,
    parse_uploaded_dieline,
    source_format_from_name,
)
from apps.simplequote.ocr import parse_drawing
from apps.simplequote.models import (
    DielineCategory,
    DielineTemplate,
    DielineTemplateAsset,
    QuoteParam,
    QuoteTable,
    SimpleQuote,
)
from apps.simplequote.serializers import (
    DielineCategorySerializer,
    DielineTemplateAssetSerializer,
    DielineTemplateSerializer,
    QuoteParamSerializer,
    QuoteTableSerializer,
    SimpleQuoteCreateSerializer,
    SimpleQuoteListSerializer,
    SimpleQuoteSerializer,
)
from apps.simplequote.shipping import ShippingError, estimate_shipping
from apps.points.services import get_rule_amount, spend_points
from apps.notification.services import notify
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole
from core.pdf import (
    build_injection_quotation_pdf,
    build_paper_box_quotation_pdf,
    build_pcba_quotation_pdf,
    build_pcb_dev_quotation_pdf,
    build_quotation_pdf,
)
from core.responses import error_response, success_response

TYPE_LABELS = {
    "injection": "注塑模具报价书",
    "print3d": "3D 打印报价书",
    "pcba": "PCBA 加工费报价书",
    "pcb": "PCB 开发报价书",
    "software": "软件开发报价书",
    "ic": "IC 方案报价书",
    "paper_box": "纸盒包装报价书",
}


def param_overrides(quote_type):
    overrides = {}
    for param in QuoteParam.objects.filter(quote_type=quote_type, is_active=True):
        overrides[param.param_key] = param.value
    return overrides


def table_overrides(quote_type):
    tables = {}
    for table in QuoteTable.objects.filter(quote_type=quote_type, is_active=True):
        tables[table.table_key] = table.rows or []
    return tables


def merged_pcb_params():
    """PCB 开发报价合并 shipping 域的配送简化规则参数。"""
    params = param_overrides("pcb")
    for key in ("pcb_shipping_under_1kg", "pcb_shipping_per_kg"):
        sp = QuoteParam.objects.filter(quote_type="shipping", param_key=key, is_active=True).first()
        if sp:
            params[key] = sp.value
        else:
            defaults = build_param_map("shipping", {})
            if key in defaults:
                params[key] = defaults[key]
    return params


def render_pdf(quote):
    if quote.quote_type == "injection":
        pdf_bytes = build_injection_quotation_pdf(
            quote_no=quote.quote_no,
            product_name=quote.product_name or "-",
            inputs=quote.inputs or {},
            result=quote.result or {},
            valid_until=quote.valid_until.isoformat() if quote.valid_until else "-",
            created_at=quote.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
        return

    if quote.quote_type == "pcba":
        pdf_bytes = build_pcba_quotation_pdf(
            quote_no=quote.quote_no,
            product_name=quote.product_name or "-",
            inputs=quote.inputs or {},
            result=quote.result or {},
            valid_until=quote.valid_until.isoformat() if quote.valid_until else "-",
            created_at=quote.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
        return

    if quote.quote_type == "pcb":
        pdf_bytes = build_pcb_dev_quotation_pdf(
            quote_no=quote.quote_no,
            product_name=quote.product_name or "-",
            inputs=quote.inputs or {},
            result=quote.result or {},
            valid_until=quote.valid_until.isoformat() if quote.valid_until else "-",
            created_at=quote.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
        return

    if quote.quote_type == "paper_box":
        pdf_bytes = build_paper_box_quotation_pdf(
            quote_no=quote.quote_no,
            product_name=quote.product_name or "-",
            inputs=quote.inputs or {},
            result=quote.result or {},
            valid_until=quote.valid_until.isoformat() if quote.valid_until else "-",
            created_at=quote.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
        return

    result = quote.result or {}
    line_items = [(item["label"], item["amount"]) for item in result.get("breakdown", [])]
    meta_rows = [
        ("产品名称", quote.product_name or "-"),
        ("报价类型", TYPE_LABELS.get(quote.quote_type, quote.quote_type)),
        ("数量", result.get("quantity", 1)),
        ("有效期", quote.valid_until.isoformat() if quote.valid_until else "-"),
        ("生成时间", quote.created_at.strftime("%Y-%m-%d %H:%M")),
    ]
    pdf_bytes = build_quotation_pdf(
        title=TYPE_LABELS.get(quote.quote_type, "报价书"),
        quote_no=quote.quote_no,
        meta_rows=meta_rows,
        line_items=line_items,
        total_label="合计 / Total",
        total_amount=quote.total_amount,
        currency=quote.currency,
    )
    quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)


class FefcoCatalogView(APIView):
    """FEFCO 标准盒型库（分类 + 盒型模板元数据）。"""

    permission_classes = []  # 公开可读，便于未登录浏览盒型库

    def get(self, request):
        from apps.simplequote.fefco_catalog import build_fefco_catalog

        return success_response(build_fefco_catalog(request=request), message="OK", request=request)


class MemberSimpleQuoteListCreateView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = SimpleQuote.objects.filter(buyer=request.user).order_by("-created_at")
        quote_type = request.query_params.get("quote_type")
        if quote_type:
            qs = qs.filter(quote_type=quote_type)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(SimpleQuoteListSerializer(page, many=True).data)

    def post(self, request):
        serializer = SimpleQuoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote_type = serializer.validated_data["quote_type"]
        inputs = serializer.validated_data.get("inputs", {})
        try:
            if quote_type == "pcb":
                result = calculate(
                    quote_type,
                    inputs,
                    merged_pcb_params(),
                    table_overrides("pcb"),
                )
            elif quote_type == "pcba":
                result = calculate(
                    quote_type,
                    inputs,
                    param_overrides("pcba"),
                    table_overrides("pcba"),
                )
            elif quote_type == "injection":
                result = calculate(
                    quote_type,
                    inputs,
                    param_overrides(quote_type),
                    table_overrides("shipping"),
                )
            else:
                result = calculate(quote_type, inputs, param_overrides(quote_type))
        except (InjectionQuoteError, PcbQuoteError, PcbaQuoteError, PaperBoxQuoteError) as exc:
            return error_response("SIMPLE_QUOTE_INPUT_INVALID", str(exc), request=request)
        except ValueError:
            return error_response("SIMPLE_QUOTE_TYPE_INVALID", "暂不支持该报价类型", request=request)

        if quote_type == "injection":
            currency = "CNY"
            valid_days = 14
        elif quote_type == "pcba":
            currency = "CNY"
            valid_days = 30
        elif quote_type == "pcb":
            currency = "KRW"
            pcb_params = merged_pcb_params()
            valid_days = max(1, int(pcb_params.get("valid_days", 30)))
        elif quote_type == "paper_box":
            currency = "CNY"
            valid_days = 14
        else:
            currency = "KRW"
            valid_days = 30

        cost = get_rule_amount("SIMPLE_QUOTE")
        with transaction.atomic():
            if cost > 0:
                spend_points(
                    request.user,
                    cost,
                    source_type="simple_quote",
                    description=f"生成{TYPE_LABELS.get(quote_type, '报价')}",
                )
            quote = SimpleQuote.objects.create(
                quote_no=SimpleQuote.generate_no(),
                buyer=request.user,
                quote_type=quote_type,
                product_name=serializer.validated_data.get("product_name", ""),
                inputs=inputs,
                result=result,
                total_amount=result.get("total", 0),
                currency=currency,
                status="calculated",
                valid_until=timezone.now().date() + timedelta(days=valid_days),
                points_spent=cost,
            )
            render_pdf(quote)
            quote.status = "pdf_generated"
            quote.save()
        return success_response(
            SimpleQuoteSerializer(quote, context={"request": request}).data,
            message="报价已生成",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class MemberSimpleQuoteDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        quote = get_object_or_404(SimpleQuote, pk=pk, buyer=request.user)
        return success_response(
            SimpleQuoteSerializer(quote, context={"request": request}).data, request=request
        )


class MemberSimpleQuoteConvertView(APIView):
    """将简单报价转为详细报价（RFQ）。"""

    permission_classes = [IsBuyerRole]

    def post(self, request, pk):
        quote = get_object_or_404(SimpleQuote, pk=pk, buyer=request.user)
        if quote.converted_rfq_id:
            return error_response("SIMPLE_QUOTE_ALREADY_CONVERTED", "该报价已转为详细报价", request=request)
        category_id = request.data.get("service_category_id")
        category = None
        if category_id:
            category = ServiceCategory.objects.filter(id=category_id, is_active=True).first()
        if not category:
            category = ServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id").first()
        if not category:
            return error_response("SERVICE_CATEGORY_MISSING", "缺少可用的服务分类", request=request)

        rfq = RFQ.objects.create(
            buyer=request.user,
            scope="internal",
            service_category=category,
            company="",
            material=str(quote.inputs.get("material", "")),
            quantity=max(1, int(quote.result.get("quantity", 1) or 1)),
            remark=f"由简单报价 {quote.quote_no} 转入，预估金额 {quote.total_amount} {quote.currency}",
            status="submitted",
        )
        quote.converted_rfq = rfq
        quote.status = "converted"
        quote.save(update_fields=["converted_rfq", "status", "updated_at"])
        notify(request.user, "quote", "已转为详细报价", f"简单报价 {quote.quote_no} 已生成询价 {rfq.rfq_no}。")
        return success_response(
            {"rfq_id": rfq.id, "rfq_no": rfq.rfq_no},
            message="已转为详细报价",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class SimpleQuotePreviewView(APIView):
    """注塑报价实时试算：仅计算、不扣点、不落库、不生成 PDF。"""

    permission_classes = [IsBuyerRole]

    def post(self, request):
        data = request.data or {}
        quote_type = data.get("quote_type")
        if quote_type != "injection":
            return error_response(
                "SIMPLE_QUOTE_TYPE_INVALID", "预览仅支持注塑报价", request=request
            )
        inputs = data.get("inputs") or {}
        try:
            result = calculate(
                quote_type,
                inputs,
                param_overrides(quote_type),
                table_overrides("shipping"),
            )
        except InjectionQuoteError as exc:
            return error_response("SIMPLE_QUOTE_INPUT_INVALID", str(exc), request=request)
        except ValueError:
            return error_response("SIMPLE_QUOTE_TYPE_INVALID", "暂不支持该报价类型", request=request)
        return success_response(result, message="试算完成", request=request)


INJECTION_MATERIALS = ["ABS", "ABS+Gf", "PC", "PA66", "PP"]
MAX_STP_SIZE = 30 * 1024 * 1024  # 30MB
ALLOWED_STP_EXT = (".stp", ".step")
STP_MAGIC = b"ISO-10303-21"


def injection_densities():
    """返回各材料密度映射（后台 QuoteParam 覆盖 DEFAULT_PARAMS 兜底），键为展示材料名。"""
    params = build_param_map("injection", param_overrides("injection"))
    result = {}
    for material in INJECTION_MATERIALS:
        weight = weight_from_volume(1.0, material, params)  # 体积 1cm³ 的重量即密度
        if weight is not None:
            result[material] = weight
    return result


class StpParseView(APIView):
    """上传 STP/STEP 文件，解析体积/包围盒/表面积，供注塑报价表单回填。

    不保存原始文件：写入临时路径解析后立即删除。返回几何结果与材料密度表，
    前端据密度按「体积 × 密度」回填单件重量，客户可覆盖。
    """

    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return error_response(
                "STP_FILE_INVALID", "请上传 STP/STEP 文件", request=request
            )
        name = (upload.name or "").lower()
        if not name.endswith(ALLOWED_STP_EXT):
            return error_response(
                "STP_FILE_INVALID", "仅支持 .stp / .step 文件", request=request
            )
        if upload.size > MAX_STP_SIZE:
            return error_response(
                "STP_FILE_INVALID", "文件超过 30MB 上限，请压缩或改为手动填写", request=request
            )

        head = upload.read(64)
        upload.seek(0)
        if STP_MAGIC not in head:
            return error_response(
                "STP_FILE_INVALID", "文件不是有效的 STEP 格式", request=request
            )

        tmp_path = None
        try:
            suffix = ".step" if name.endswith(".step") else ".stp"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in upload.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            geometry = parse_step(tmp_path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        parse_status = geometry.get("parse_status")
        if parse_status == "timeout":
            return error_response(
                "STP_PARSE_TIMEOUT",
                "文件解析超时，请改为手动填写参数",
                request=request,
            )
        if parse_status != "ok":
            return error_response(
                "STP_PARSE_FAILED",
                "文件解析失败，请改为手动填写参数",
                errors={"reason": geometry.get("error")},
                request=request,
            )

        return success_response(
            {"geometry": geometry, "densities": injection_densities()},
            message="解析成功",
            request=request,
        )


MAX_DRAWING_SIZE = 15 * 1024 * 1024  # 15MB
ALLOWED_DRAWING_EXT = (".pdf", ".png", ".jpg", ".jpeg")
# 文件魔数：PDF / PNG / JPEG
_DRAWING_MAGICS = (b"%PDF", b"\x89PNG", b"\xff\xd8\xff")


class DrawingParseView(APIView):
    """上传 2D 工程图（PDF/图片），OCR 抽取材料/精密度/颜色作为建议值。

    不保存原始文件：写入临时路径解析后立即删除。结果为低置信度建议，需人工确认。
    """

    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return error_response(
                "DRAWING_FILE_INVALID", "请上传工程图（PDF/PNG/JPG）", request=request
            )
        name = (upload.name or "").lower()
        if not name.endswith(ALLOWED_DRAWING_EXT):
            return error_response(
                "DRAWING_FILE_INVALID", "仅支持 PDF / PNG / JPG 文件", request=request
            )
        if upload.size > MAX_DRAWING_SIZE:
            return error_response(
                "DRAWING_FILE_INVALID", "文件超过 15MB 上限，请压缩或改为手动填写", request=request
            )

        head = upload.read(8)
        upload.seek(0)
        if not any(head.startswith(magic) for magic in _DRAWING_MAGICS):
            return error_response(
                "DRAWING_FILE_INVALID", "文件不是有效的 PDF/图片格式", request=request
            )

        kind = "pdf" if name.endswith(".pdf") else "image"
        suffix = ".pdf" if kind == "pdf" else os.path.splitext(name)[1]
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in upload.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            ocr = parse_drawing(tmp_path, kind)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        parse_status = ocr.get("parse_status")
        if parse_status == "unavailable":
            return error_response(
                "OCR_UNAVAILABLE", "OCR 服务不可用，请改为手动填写参数", request=request
            )
        if parse_status == "timeout":
            return error_response(
                "DRAWING_PARSE_TIMEOUT", "图纸解析超时，请改为手动填写参数", request=request
            )
        if parse_status != "ok":
            return error_response(
                "DRAWING_PARSE_FAILED",
                "图纸解析失败，请改为手动填写参数",
                errors={"reason": ocr.get("error")},
                request=request,
            )

        return success_response({"ocr": ocr}, message="解析成功", request=request)


class ShippingEstimateView(APIView):
    """运输费估算：空运阶梯 / 海运 LCL / PCB 简化配送。"""

    permission_classes = [IsBuyerRole]

    def post(self, request):
        data = request.data or {}
        mode = data.get("mode", "air")
        try:
            params = param_overrides("shipping")
            tables = table_overrides("shipping")
            result = estimate_shipping(data, params, tables)
            if mode == "lcl" and not data.get("has_battery"):
                alt_days = 5 if int(data.get("service_days", 4)) == 4 else 4
                alt_data = dict(data)
                alt_data["service_days"] = alt_days
                alt = estimate_shipping(alt_data, params, tables)
                result["comparison"] = {
                    "service_days": alt_days,
                    "fee_krw": alt.get("fee_krw"),
                    "delta_krw": (result.get("fee_krw") or 0) - (alt.get("fee_krw") or 0),
                }
        except ShippingError as exc:
            return error_response("SHIPPING_INPUT_INVALID", str(exc), request=request)
        return success_response(result, message="估算完成", request=request)


class AdminQuoteParamView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = QuoteParam.objects.all()
        quote_type = request.query_params.get("quote_type")
        if quote_type:
            qs = qs.filter(quote_type=quote_type)
        return success_response({"items": QuoteParamSerializer(qs, many=True).data}, request=request)

    def post(self, request):
        serializer = QuoteParamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminQuoteParamDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        param = get_object_or_404(QuoteParam, pk=pk)
        serializer = QuoteParamSerializer(param, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)


class AdminQuoteTableView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = QuoteTable.objects.all()
        quote_type = request.query_params.get("quote_type")
        if quote_type:
            qs = qs.filter(quote_type=quote_type)
        return success_response({"items": QuoteTableSerializer(qs, many=True).data}, request=request)

    def post(self, request):
        serializer = QuoteTableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminQuoteTableDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        table = get_object_or_404(QuoteTable, pk=pk)
        serializer = QuoteTableSerializer(table, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)


class AdminDielineCategoryView(APIView):
    """刀版盒型分类（管理员维护）。"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = DielineCategory.objects.all().order_by("sort_order", "code")
        return success_response(
            {"items": DielineCategorySerializer(qs, many=True).data},
            request=request,
        )

    def post(self, request):
        serializer = DielineCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminDielineCategoryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        category = get_object_or_404(DielineCategory, pk=pk)
        serializer = DielineCategorySerializer(
            category, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)

    def delete(self, request, pk):
        category = get_object_or_404(DielineCategory, pk=pk)
        if category.templates.exists():
            return error_response(
                "DIELINE_CATEGORY_IN_USE",
                "该分类下仍有模板，无法删除。请先迁移或删除模板，或停用分类。",
                request=request,
            )
        category.delete()
        return success_response({"id": pk}, message="已删除", request=request)


class AdminDielineTemplateView(APIView):
    """刀版参数化模板库（管理员维护）。"""

    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        qs = DielineTemplate.objects.all().order_by("sort_order", "code")
        return success_response(
            {
                "items": DielineTemplateSerializer(
                    qs, many=True, context={"request": request}
                ).data
            },
            request=request,
        )

    def post(self, request):
        serializer = DielineTemplateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminDielineTemplateDetailView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        template = get_object_or_404(DielineTemplate, pk=pk)
        serializer = DielineTemplateSerializer(
            template, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)

    def delete(self, request, pk):
        template = get_object_or_404(DielineTemplate, pk=pk)
        template.delete()
        return success_response({"id": pk}, message="已删除", request=request)


MAX_DIELINE_ASSET_SIZE = 20 * 1024 * 1024
ALLOWED_DIELINE_ASSET_EXT = ("dxf", "svg", "ai", "pdf")


class AdminDielineTemplateAssetView(APIView):
    """刀版模板资产版本：上传真实 DXF/SVG 并保存解析 JSON。"""

    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, template_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        qs = template.assets.all()
        return success_response(
            {"items": DielineTemplateAssetSerializer(qs, many=True, context={"request": request}).data},
            request=request,
        )

    def post(self, request, template_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        upload = request.FILES.get("source_file")
        if not upload:
            return error_response("DIELINE_ASSET_FILE_REQUIRED", "请上传刀版文件", request=request)
        if upload.size > MAX_DIELINE_ASSET_SIZE:
            return error_response("DIELINE_ASSET_TOO_LARGE", "文件超过 20MB 上限", request=request)
        source_format = source_format_from_name(upload.name)
        if source_format not in ALLOWED_DIELINE_ASSET_EXT:
            return error_response("DIELINE_ASSET_FORMAT_INVALID", "仅支持 DXF/SVG/AI/PDF 文件", request=request)

        latest = template.assets.order_by("-version").first()
        version = (latest.version if latest else 0) + 1
        try:
            base_dimensions = {
                "length": float(request.data.get("base_length") or template.default_length_mm),
                "width": float(request.data.get("base_width") or template.default_width_mm),
                "height": float(request.data.get("base_height") or template.default_height_mm),
                "thickness": float(request.data.get("base_thickness") or template.default_thickness_mm),
            }
        except (TypeError, ValueError):
            return error_response(
                "DIELINE_ASSET_BASE_DIMENSIONS_INVALID",
                "基准尺寸必须为数字",
                request=request,
            )
        if min(base_dimensions.values()) <= 0:
            return error_response(
                "DIELINE_ASSET_BASE_DIMENSIONS_INVALID",
                "基准尺寸必须大于 0",
                request=request,
            )
        asset = DielineTemplateAsset.objects.create(
            template=template,
            source_file=upload,
            source_format=source_format,
            base_dimensions=base_dimensions,
            version=version,
            mapping_status="uploaded",
        )
        if source_format in {"ai", "pdf"}:
            asset.mapping_status = "attachment_only"
            asset.parse_errors = {
                "message": "AI/PDF 已保存为附件；参数化映射请上传 DXF/SVG 文件。"
            }
            asset.save(update_fields=["mapping_status", "parse_errors", "updated_at"])
            return success_response(
                DielineTemplateAssetSerializer(asset, context={"request": request}).data,
                message="附件已保存，需 DXF/SVG 才能参数化",
                status=status.HTTP_201_CREATED,
                request=request,
            )

        try:
            upload.seek(0)
            parsed_geometry = parse_uploaded_dieline(upload, source_format)
            asset.parsed_geometry = parsed_geometry
            asset.mapping_schema = default_mapping_schema(parsed_geometry, base_dimensions)
            asset.mapping_status = "parsed"
            asset.parse_errors = {}
            asset.save(update_fields=["parsed_geometry", "mapping_schema", "mapping_status", "parse_errors", "updated_at"])
        except (DielineImportError, ValueError) as exc:
            asset.mapping_status = "failed"
            asset.parse_errors = {"message": str(exc)}
            asset.save(update_fields=["mapping_status", "parse_errors", "updated_at"])
            return error_response(
                "DIELINE_ASSET_PARSE_FAILED",
                "刀版文件解析失败",
                errors=asset.parse_errors,
                request=request,
            )

        return success_response(
            DielineTemplateAssetSerializer(asset, context={"request": request}).data,
            message="解析成功",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminDielineTemplateAssetDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, template_id, asset_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        asset = get_object_or_404(DielineTemplateAsset, pk=asset_id, template=template)
        serializer = DielineTemplateAssetSerializer(
            asset,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(mapping_status="mapped")
        return success_response(serializer.data, message="映射已保存", request=request)

    def delete(self, request, template_id, asset_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        asset = get_object_or_404(DielineTemplateAsset, pk=asset_id, template=template)
        asset.delete()
        return success_response({"id": asset_id}, message="已删除", request=request)


class AdminDielineTemplateAssetActivateView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, template_id, asset_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        asset = get_object_or_404(DielineTemplateAsset, pk=asset_id, template=template)
        if asset.mapping_status != "mapped":
            return error_response("DIELINE_ASSET_NOT_MAPPED", "请先保存映射后再启用", request=request)
        with transaction.atomic():
            template.assets.exclude(pk=asset.pk).update(is_active=False)
            asset.is_active = True
            asset.save(update_fields=["is_active", "updated_at"])
        return success_response(
            DielineTemplateAssetSerializer(asset, context={"request": request}).data,
            message="已启用",
            request=request,
        )
