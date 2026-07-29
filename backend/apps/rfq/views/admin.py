from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from apps.notification.services import notify
from apps.rfq.models import ProductionOrder, Quote, QuoteRequest, RFQ, ServiceCategory
from apps.rfq.serializers import (
    AdminProductionOrderSerializer,
    AdminQuoteCreateSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
    RFQDetailSerializer,
    RFQListSerializer,
    ServiceCategorySerializer,
)
from core.pagination import StandardPagination
from core.permissions import IsAdminRole
from core.responses import error_response, success_response

from ._helpers import get_lang, maybe_mark_quote_request_expired


class AdminProductionOrderListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = ProductionOrder.objects.select_related("rfq", "buyer", "supplier").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminProductionOrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminProductionOrderDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        order = get_object_or_404(
            ProductionOrder.objects.select_related("rfq", "buyer", "supplier"),
            pk=pk,
        )
        return success_response(AdminProductionOrderSerializer(order).data, request=request)

    def patch(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        new_status = request.data.get("status")
        valid = {c[0] for c in ProductionOrder.STATUS_CHOICES}
        if new_status not in valid:
            return error_response("PRODUCTION_ORDER_STATUS_INVALID", "无效的状态", request=request)
        order.status = new_status
        if new_status == "confirmed" and not order.confirmed_at:
            order.confirmed_at = timezone.now()
        order.save(update_fields=["status", "confirmed_at", "updated_at"])
        return success_response(AdminProductionOrderSerializer(order).data, request=request)


class AdminServiceCategoryListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = ServiceCategory.objects.all().order_by("sort_order", "id")
        return success_response(
            {"items": ServiceCategorySerializer(qs, many=True).data},
            request=request,
        )

    def post(self, request):
        serializer = ServiceCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminServiceCategoryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        obj = get_object_or_404(ServiceCategory, pk=pk)
        return success_response(ServiceCategorySerializer(obj).data, request=request)

    def patch(self, request, pk):
        obj = get_object_or_404(ServiceCategory, pk=pk)
        serializer = ServiceCategorySerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)


class AdminRFQListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = (
            RFQ.objects.select_related("service_category", "buyer")
            .annotate(quotes_count=Count("quotes", distinct=True))
            .order_by("-created_at")
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        category_id = request.query_params.get("service_category_id")
        if category_id:
            qs = qs.filter(service_category_id=category_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = RFQListSerializer(page, many=True, context={"lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)


class AdminRFQDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        rfq = get_object_or_404(
            RFQ.objects.select_related("service_category", "buyer")
            .prefetch_related("attachments", "quotes__supplier__factory_profile"),
            pk=pk,
        )
        return success_response(
            RFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class AdminRFQStatusView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk)
        update_fields = ["updated_at"]

        if "status" in request.data:
            new_status = request.data.get("status")
            valid_statuses = {choice[0] for choice in RFQ.STATUS_CHOICES}
            if new_status not in valid_statuses:
                return error_response(
                    "RFQ_STATUS_INVALID",
                    "无效的状态",
                    errors={"status": list(valid_statuses)},
                    request=request,
                )
            rfq.status = new_status
            update_fields.append("status")

        if "markup_percent" in request.data:
            try:
                markup = int(request.data.get("markup_percent") or 0)
            except (TypeError, ValueError):
                return error_response(
                    "RFQ_MARKUP_INVALID",
                    "无效的加价率",
                    request=request,
                )
            rfq.markup_percent = max(0, markup)
            update_fields.append("markup_percent")

        rfq.save(update_fields=update_fields)
        return success_response(
            RFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class AdminRFQQuoteCreateView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk)
        serializer = AdminQuoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = serializer.save(rfq=rfq, created_by=request.user, status="sent")
        if rfq.status in {"submitted", "quoting"}:
            rfq.status = "quoted"
            rfq.save(update_fields=["status", "updated_at"])
        return success_response(
            QuoteSerializer(quote).data,
            message="报价已发送",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminQuoteDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        quote = get_object_or_404(Quote, pk=pk)
        was_visible = quote.is_customer_visible
        serializer = AdminQuoteCreateSerializer(quote, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        rfq = quote.rfq
        if quote.is_customer_visible and rfq.status in {"quoted", "assigned", "quoting"}:
            rfq.status = "comparing"
            rfq.save(update_fields=["status", "updated_at"])
        if quote.is_customer_visible and not was_visible:
            notify(
                rfq.buyer,
                "quote",
                "报价方案已就绪",
                f"询价 {rfq.rfq_no} 的报价方案已开放，请登录查看并确认。",
                related_type="rfq",
                related_id=rfq.id,
                send_email=True,
            )
        return success_response(QuoteSerializer(quote).data, request=request)


class AdminRFQQuoteRequestListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk)
        qs = rfq.quote_requests.select_related("supplier__factory_profile").prefetch_related("quotes")
        items = []
        for qr in qs:
            maybe_mark_quote_request_expired(qr)
            items.append(qr)
        return success_response(
            {"items": QuoteRequestSerializer(items, many=True, context={"lang": get_lang(request)}).data},
            request=request,
        )


class AdminQuoteRequestReviseView(APIView):
    """管理员要求供应商修订报价。"""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        qr = get_object_or_404(QuoteRequest.objects.select_related("rfq"), pk=pk)
        if qr.status != "quoted":
            return error_response("QUOTE_REQUEST_STATUS_INVALID", "仅已报价的请求可要求修订", request=request)
        qr.status = "needs_revision"
        qr.save(update_fields=["status", "updated_at"])
        notify(
            qr.supplier,
            "quote_request",
            "报价需修订",
            f"报价请求 {qr.request_no} 需修订，请更新后重新提交。",
            related_type="quote_request",
            related_id=qr.id,
            send_email=True,
        )
        return success_response(
            QuoteRequestSerializer(qr, context={"lang": get_lang(request)}).data,
            message="已通知供应商修订",
            request=request,
        )


class AdminQuoteRequestCancelView(APIView):
    """管理员取消报价指派。"""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        qr = get_object_or_404(QuoteRequest.objects.select_related("rfq"), pk=pk)
        if qr.status not in {"assigned", "viewed"}:
            return error_response("QUOTE_REQUEST_STATUS_INVALID", "当前状态不可取消", request=request)
        qr.status = "cancelled"
        qr.save(update_fields=["status", "updated_at"])
        notify(
            qr.supplier,
            "quote_request",
            "报价请求已取消",
            f"报价请求 {qr.request_no} 已被管理员取消。",
            related_type="quote_request",
            related_id=qr.id,
        )
        return success_response(
            QuoteRequestSerializer(qr, context={"lang": get_lang(request)}).data,
            message="已取消指派",
            request=request,
        )
