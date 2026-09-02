from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.rfq.models import RFQ, ServiceCategory
from apps.simplequote.calculator import (
    InjectionQuoteError,
    PaperBoxQuoteError,
    PcbaQuoteError,
    PcbQuoteError,
    calculate,
)
from apps.simplequote.models import Print3dSliceJob, SimpleQuote
from apps.simplequote.serializers import (
    SimpleQuoteCreateSerializer,
    SimpleQuoteListSerializer,
    SimpleQuoteSerializer,
)
from apps.simplequote.shipping import ShippingError, estimate_shipping
from apps.points.services import get_rule_amount, spend_points
from apps.notification.services import notify
from core.pagination import StandardPagination
from core.permissions import IsBuyerRole, IsEmailVerified
from core.responses import error_response, success_response

from apps.simplequote.views._helpers import (
    TYPE_LABELS,
    attach_live_fx,
    merged_pcb_params,
    param_overrides,
    render_pdf,
    table_overrides,
)


class FefcoCatalogView(APIView):
    """FEFCO 标准盒型库（分类 + 盒型模板元数据）。"""

    permission_classes = [AllowAny]  # 公开可读，便于未登录浏览盒型库

    def get(self, request):
        from apps.simplequote.fefco_catalog import build_fefco_catalog

        return success_response(build_fefco_catalog(request=request), message="OK", request=request)


class MemberSimpleQuoteListCreateView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsBuyerRole(), IsEmailVerified()]
        return [IsBuyerRole()]

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
        inputs = dict(serializer.validated_data.get("inputs", {}) or {})

        if quote_type == "print3d":
            slice_job_id = inputs.pop("slice_job_id", None)
            if slice_job_id:
                try:
                    job = Print3dSliceJob.objects.get(pk=int(slice_job_id), buyer=request.user)
                except (Print3dSliceJob.DoesNotExist, TypeError, ValueError):
                    return error_response(
                        "PRINT3D_JOB_NOT_FOUND", "切片任务不存在", request=request
                    )
                if job.status != Print3dSliceJob.STATUS_DONE:
                    return error_response(
                        "PRINT3D_JOB_NOT_READY",
                        "切片尚未完成，无法生成报价",
                        request=request,
                    )
                result_data = job.result or {}
                weight = result_data.get("filament_weight_g")
                hours = result_data.get("print_hours")
                if weight is None or hours is None:
                    return error_response(
                        "PRINT3D_JOB_NOT_READY",
                        "切片结果缺少重量或时长",
                        request=request,
                    )
                # Server-trusted weight/time — ignore client overrides
                inputs["model_weight_g"] = weight
                inputs["print_hours"] = hours
                inputs["config_snapshot"] = job.config_snapshot or {}
                snap = inputs["config_snapshot"]
                if snap.get("material"):
                    inputs.setdefault("material", snap["material"].get("key", "PLA"))
                if snap.get("post_processing"):
                    inputs.setdefault(
                        "post_process", snap["post_processing"].get("key", "none")
                    )
                inputs.setdefault("quantity", snap.get("quantity", 1))
                inputs.setdefault("rush", snap.get("rush", False))
                inputs["slice_job_id"] = job.id

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
            elif quote_type == "print3d":
                snap_params = (inputs.get("config_snapshot") or {}).get("params") or {}
                overrides = {**param_overrides("print3d"), **snap_params}
                result = calculate(quote_type, inputs, overrides)
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

        result = attach_live_fx(result, currency)

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
    """简单报价实时试算：仅计算、不扣点、不落库、不生成 PDF（注塑 / 3D 打印）。"""

    permission_classes = [IsBuyerRole]

    def post(self, request):
        data = request.data or {}
        quote_type = data.get("quote_type")
        if quote_type not in ("injection", "print3d"):
            return error_response(
                "SIMPLE_QUOTE_TYPE_INVALID", "预览仅支持注塑或 3D 打印", request=request
            )
        inputs = dict(data.get("inputs") or {})
        if quote_type == "print3d":
            slice_job_id = inputs.get("slice_job_id")
            if slice_job_id:
                try:
                    job = Print3dSliceJob.objects.get(pk=int(slice_job_id), buyer=request.user)
                except (Print3dSliceJob.DoesNotExist, TypeError, ValueError):
                    return error_response(
                        "PRINT3D_JOB_NOT_FOUND", "切片任务不存在", request=request
                    )
                if job.status != Print3dSliceJob.STATUS_DONE:
                    return error_response(
                        "PRINT3D_JOB_NOT_READY", "切片尚未完成", request=request
                    )
                inputs["model_weight_g"] = job.result.get("filament_weight_g")
                inputs["print_hours"] = job.result.get("print_hours")
                inputs["config_snapshot"] = job.config_snapshot or {}
        try:
            if quote_type == "injection":
                result = calculate(
                    quote_type,
                    inputs,
                    param_overrides(quote_type),
                    table_overrides("shipping"),
                )
            else:
                snap_params = (inputs.get("config_snapshot") or {}).get("params") or {}
                overrides = {**param_overrides("print3d"), **snap_params}
                result = calculate(quote_type, inputs, overrides)
        except InjectionQuoteError as exc:
            return error_response("SIMPLE_QUOTE_INPUT_INVALID", str(exc), request=request)
        except ValueError:
            return error_response("SIMPLE_QUOTE_TYPE_INVALID", "暂不支持该报价类型", request=request)
        currency = "CNY" if quote_type == "injection" else "KRW"
        result = attach_live_fx(result, currency)
        result["currency"] = currency
        return success_response(result, message="试算完成", request=request)


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
