from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.notification.services import notify, notify_staff
from apps.rfq.constants import PLATFORM_PAYMENT_TERMS
from apps.rfq.models import ProductionOrder, Quote, QuoteAttachment, QuoteRequest
from apps.rfq.serializers import (
    DemandHallDetailSerializer,
    FactoryQuoteCreateSerializer,
    ProductionOrderSerializer,
    QuoteAttachmentSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
)
from core.pagination import StandardPagination
from core.permissions import IsSupplierRole
from core.responses import error_response, success_response

from ._helpers import (
    _download_quote_attachment,
    _quote_is_locked,
    _quote_upload_files,
    _save_quote_attachments,
    _validate_quote_attachment_files,
    get_lang,
    maybe_mark_quote_request_expired,
    open_demand_hall_queryset,
    publish_supplier_quote_to_buyer,
)


class SupplierDemandHallGrabView(APIView):
    """供应商在需求大厅自主抢单。"""

    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        rfq = get_object_or_404(open_demand_hall_queryset(), pk=pk)
        qr, is_new = QuoteRequest.objects.get_or_create(
            rfq=rfq,
            supplier=request.user,
            defaults={
                "status": "viewed",
                "created_by": request.user,
            },
        )
        if not is_new:
            if qr.status == "cancelled":
                return error_response(
                    "QUOTE_REQUEST_CANCELLED",
                    "该需求的抢单已取消，无法再次抢单",
                    request=request,
                )
            return success_response(
                QuoteRequestSerializer(qr, context={"lang": get_lang(request)}).data,
                message="您已抢过此需求",
                request=request,
            )
        if rfq.status in {"submitted", "pending_review"}:
            rfq.status = "quoting"
            rfq.save(update_fields=["status", "updated_at"])
        supplier_name = getattr(getattr(request.user, "factory_profile", None), "company_name", "") or request.user.email
        notify_staff(
            "quote_request",
            "供应商已抢单",
            f"供应商 {supplier_name} 已抢单 RFQ {rfq.rfq_no}，请及时跟进。",
            related_type="quote_request",
            related_id=qr.id,
        )
        return success_response(
            QuoteRequestSerializer(qr, context={"lang": get_lang(request)}).data,
            message="抢单成功",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class SupplierQuoteRequestListView(APIView):
    """供应商查看自己抢单或参与的报价请求。"""

    permission_classes = [IsSupplierRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = (
            QuoteRequest.objects.filter(supplier=request.user)
            .exclude(status="cancelled")
            .select_related("rfq", "rfq__service_category")
            .prefetch_related("quotes")
            .order_by("-created_at")
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = QuoteRequestSerializer(page, many=True, context={"lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)


class SupplierQuoteRequestDetailView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        qr = get_object_or_404(
            QuoteRequest.objects.select_related("rfq", "rfq__service_category").prefetch_related(
                "rfq__attachments", "quotes", "quotes__attachments"
            ),
            pk=pk,
            supplier=request.user,
        )
        if qr.status == "assigned":
            qr.status = "viewed"
            qr.save(update_fields=["status", "updated_at"])
        maybe_mark_quote_request_expired(qr)
        data = QuoteRequestSerializer(qr, context={"lang": get_lang(request)}).data
        data["rfq_detail"] = DemandHallDetailSerializer(
            qr.rfq,
            context={
                "request": request,
                "lang": get_lang(request),
                "quote_request_id": qr.id,
            },
        ).data
        my_quote = qr.quotes.filter(supplier=request.user).first()
        data["my_quote"] = (
            QuoteSerializer(my_quote, context={"request": request}).data if my_quote else None
        )
        return success_response(data, request=request)


class SupplierQuoteRequestFulfillmentView(APIView):
    """供应商：按报价请求聚合接单、合同、付款摘要、项目与本单文件。"""

    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        from apps.rfq.fulfillment import build_supplier_fulfillment

        qr = get_object_or_404(
            QuoteRequest.objects.select_related("rfq").prefetch_related("rfq__attachments"),
            pk=pk,
            supplier=request.user,
        )
        return success_response(build_supplier_fulfillment(qr, request), request=request)


class SupplierQuoteRequestQuoteView(APIView):
    """供应商提交或修订报价（方案确认前可修改），支持附件。"""

    permission_classes = [IsSupplierRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        qr = get_object_or_404(QuoteRequest, pk=pk, supplier=request.user)
        if qr.status in {"cancelled", "expired", "not_adopted", "adopted"}:
            return error_response(
                "QUOTE_REQUEST_CLOSED",
                "该报价请求已关闭，无法提交报价",
                request=request,
            )
        if qr.rfq.status == "won":
            return error_response(
                "QUOTE_LOCKED_AFTER_ACCEPT",
                "客户已确认方案，报价不可再修改",
                request=request,
            )
        existing = (
            Quote.objects.filter(quote_request=qr, supplier=request.user)
            .prefetch_related("attachments")
            .first()
        )
        upload_files = _quote_upload_files(request)
        existing_count = existing.attachments.count() if existing else 0
        err = _validate_quote_attachment_files(
            upload_files, existing_count=existing_count, request=request
        )
        if err:
            return err
        serializer = FactoryQuoteCreateSerializer(data=request.data, partial=bool(existing))
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            if existing:
                if existing.status == "accepted":
                    return error_response(
                        "QUOTE_LOCKED_AFTER_ACCEPT",
                        "客户已确认方案，报价不可再修改",
                        request=request,
                    )
                for field, value in serializer.validated_data.items():
                    setattr(existing, field, value)
                existing.payment_terms = PLATFORM_PAYMENT_TERMS
                existing.revision_version = (existing.revision_version or 1) + 1
                existing.revised_at = timezone.now()
                existing.status = "sent"
                existing.save()
                quote = existing
                message = "报价已更新"
            else:
                quote = serializer.save(
                    rfq=qr.rfq,
                    quote_request=qr,
                    supplier=request.user,
                    created_by=request.user,
                    status="sent",
                    revision_version=1,
                )
                message = "报价已提交"
            if upload_files:
                _save_quote_attachments(quote, upload_files, request.user)
            qr.status = "quoted"
            qr.save(update_fields=["status", "updated_at"])
            rfq = qr.rfq
            first_open = not quote.is_customer_visible
            quote = publish_supplier_quote_to_buyer(quote, rfq, notify_buyer=False)
        if first_open:
            notify(
                rfq.buyer,
                "quote",
                "报价方案已就绪",
                f"询价 {rfq.rfq_no} 有新的报价方案可供对比确认。",
                related_type="rfq",
                related_id=rfq.id,
                send_email=True,
            )
        elif existing:
            notify(
                rfq.buyer,
                "quote",
                "报价已修订",
                f"询价 {rfq.rfq_no} 的方案 {quote.plan_label or quote.id} 已更新至 v{quote.revision_version}，请重新对比确认。",
                related_type="rfq",
                related_id=rfq.id,
                send_email=True,
            )
        quote = Quote.objects.prefetch_related("attachments").get(pk=quote.pk)
        return success_response(
            QuoteSerializer(quote, context={"request": request}).data,
            message=message,
            status=status.HTTP_201_CREATED if not existing else status.HTTP_200_OK,
            request=request,
        )

    def patch(self, request, pk):
        return self.post(request, pk)


class SupplierQuoteAttachmentListCreateView(APIView):
    permission_classes = [IsSupplierRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, quote_id):
        quote = get_object_or_404(Quote, pk=quote_id, supplier=request.user)
        return success_response(
            {
                "items": QuoteAttachmentSerializer(
                    quote.attachments.all(), many=True, context={"request": request}
                ).data
            },
            request=request,
        )

    def post(self, request, quote_id):
        quote = get_object_or_404(
            Quote.objects.select_related("rfq").prefetch_related("attachments"),
            pk=quote_id,
            supplier=request.user,
        )
        if _quote_is_locked(quote):
            return error_response(
                "QUOTE_LOCKED_AFTER_ACCEPT",
                "客户已确认方案，报价不可再修改",
                request=request,
            )
        upload_files = _quote_upload_files(request)
        if not upload_files:
            return error_response("MEDIA_FILE_TYPE_INVALID", "请上传文件", request=request)
        err = _validate_quote_attachment_files(
            upload_files, existing_count=quote.attachments.count(), request=request
        )
        if err:
            return err
        created = _save_quote_attachments(quote, upload_files, request.user)
        return success_response(
            {
                "items": QuoteAttachmentSerializer(
                    created, many=True, context={"request": request}
                ).data
            },
            message="附件已上传",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class SupplierQuoteAttachmentDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, quote_id, file_id):
        quote = get_object_or_404(Quote, pk=quote_id, supplier=request.user)
        attachment = get_object_or_404(QuoteAttachment, pk=file_id, quote=quote)
        return _download_quote_attachment(attachment)


class SupplierQuoteAttachmentDeleteView(APIView):
    permission_classes = [IsSupplierRole]

    def delete(self, request, quote_id, file_id):
        quote = get_object_or_404(
            Quote.objects.select_related("rfq"),
            pk=quote_id,
            supplier=request.user,
        )
        if _quote_is_locked(quote):
            return error_response(
                "QUOTE_LOCKED_AFTER_ACCEPT",
                "客户已确认方案，报价不可再修改",
                request=request,
            )
        attachment = get_object_or_404(QuoteAttachment, pk=file_id, quote=quote)
        from apps.rfq.translate_views import cleanup_quote_attachment_cache

        cleanup_quote_attachment_cache(attachment.id)
        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()
        return success_response({}, message="附件已删除", request=request)


class FactoryQuoteListView(APIView):
    permission_classes = [IsSupplierRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = (
            Quote.objects.filter(supplier=request.user)
            .select_related("rfq", "rfq__service_category")
            .order_by("-created_at")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        items = []
        for quote in page:
            items.append(
                {
                    **QuoteSerializer(quote).data,
                    "rfq_no": quote.rfq.rfq_no,
                    "rfq_id": quote.rfq_id,
                    "rfq_status": quote.rfq.status,
                }
            )
        return paginator.get_paginated_response(items)


class SupplierProductionOrderListView(APIView):
    permission_classes = [IsSupplierRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = ProductionOrder.objects.filter(supplier=request.user).select_related(
            "rfq", "buyer", "quote", "quote__quote_request"
        ).order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductionOrderSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class SupplierProductionOrderConfirmView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk, supplier=request.user)
        if order.status != "pending_confirm":
            return error_response("PRODUCTION_ORDER_STATUS_INVALID", "当前状态不可接单", request=request)
        order.status = "confirmed"
        order.confirmed_at = timezone.now()
        order.save(update_fields=["status", "confirmed_at", "updated_at"])
        return success_response(
            ProductionOrderSerializer(order, context={"request": request}).data,
            message="已确认接单",
            request=request,
        )


class SupplierProductionOrderRejectView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        order = get_object_or_404(
            ProductionOrder.objects.select_related("rfq", "quote", "buyer"),
            pk=pk,
            supplier=request.user,
        )
        if order.status != "pending_confirm":
            return error_response("PRODUCTION_ORDER_STATUS_INVALID", "当前状态不可拒单", request=request)

        from apps.contract.models import Contract
        from apps.payment.models import Payment

        with transaction.atomic():
            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])

            rfq = order.rfq
            if rfq.status == "won":
                rfq.status = "comparing"
                rfq.save(update_fields=["status", "updated_at"])

            quote = order.quote
            if quote.status == "accepted":
                quote.status = "sent"
                quote.save(update_fields=["status", "updated_at"])
            if quote.quote_request_id:
                QuoteRequest.objects.filter(pk=quote.quote_request_id).update(status="quoted")

            contract = Contract.objects.filter(production_order=order).first()
            if contract and contract.status != "cancelled":
                contract.status = "cancelled"
                contract.save(update_fields=["status", "updated_at"])
                Payment.objects.filter(contract=contract).exclude(status="confirmed").update(
                    status="cancelled"
                )

        notify(
            order.buyer,
            "production_order",
            "供应商已拒单",
            f"生产订单 {order.order_no} 已被供应商拒绝，RFQ 已回退至比选阶段。",
            related_type="production_order",
            related_id=order.id,
            send_email=True,
        )
        notify_staff(
            "production_order",
            "供应商拒单",
            f"供应商 {request.user.email} 拒绝订单 {order.order_no}，相关合同/付款已作废。",
            related_type="production_order",
            related_id=order.id,
        )
        return success_response(
            ProductionOrderSerializer(order, context={"request": request}).data,
            message="已拒绝订单",
            request=request,
        )
