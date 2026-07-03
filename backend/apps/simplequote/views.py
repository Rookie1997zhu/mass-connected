from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from apps.rfq.models import RFQ, ServiceCategory
from apps.simplequote.calculator import calculate
from apps.simplequote.models import QuoteParam, SimpleQuote
from apps.simplequote.serializers import (
    QuoteParamSerializer,
    SimpleQuoteCreateSerializer,
    SimpleQuoteListSerializer,
    SimpleQuoteSerializer,
)
from apps.points.services import get_rule_amount, spend_points
from apps.notification.services import notify
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole
from core.pdf import build_quotation_pdf
from core.responses import error_response, success_response

TYPE_LABELS = {
    "injection": "注塑模具报价书",
    "print3d": "3D 打印报价书",
    "pcb": "PCB 报价书",
    "software": "软件开发报价书",
    "ic": "IC 方案报价书",
}


def param_overrides(quote_type):
    overrides = {}
    for param in QuoteParam.objects.filter(quote_type=quote_type, is_active=True):
        overrides[param.param_key] = param.value
    return overrides


def render_pdf(quote):
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
            result = calculate(quote_type, inputs, param_overrides(quote_type))
        except ValueError:
            return error_response("SIMPLE_QUOTE_TYPE_INVALID", "暂不支持该报价类型", request=request)

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
                status="calculated",
                valid_until=timezone.now().date() + timedelta(days=30),
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
