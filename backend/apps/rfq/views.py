from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.rfq.models import (
    ProductionOrder,
    RFQ,
    Quote,
    QuoteRequest,
    RFQAttachment,
    ServiceCategory,
)
from apps.rfq.serializers import (
    AdminProductionOrderSerializer,
    AdminQuoteCreateSerializer,
    CustomerPlanSerializer,
    DemandHallDetailSerializer,
    DemandHallListSerializer,
    FactoryQuoteCreateSerializer,
    MemberRFQDetailSerializer,
    ProductionOrderSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
    RFQCreateSerializer,
    RFQDetailSerializer,
    RFQListSerializer,
    ServiceCategorySerializer,
    apply_markup,
)
from core.pdf import build_comparison_pdf
from apps.notification.services import notify, notify_staff
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response

ALLOWED_ATTACHMENT_EXTENSIONS = {
    "pdf", "step", "stp", "igs", "iges", "dwg", "dxf", "x_t", "x_b",
    "sldprt", "stl", "3mf", "zip", "rar", "7z",
    "jpg", "jpeg", "png", "gif", "webp", "xlsx", "xls", "docx", "doc", "csv", "txt",
}
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024
OPEN_RFQ_STATUSES = {"submitted", "quoting", "quoted", "negotiating"}


def open_demand_hall_queryset():
    return (
        RFQ.objects.filter(scope="public", status__in=OPEN_RFQ_STATUSES)
        .select_related("service_category")
        .order_by("-created_at")
    )


def get_lang(request):
    return request.query_params.get("lang") or request.headers.get("Accept-Language", "ko")[:2]


def maybe_mark_quote_request_expired(qr):
    """读取时对超过 deadline 的 assigned/viewed 报价请求标记为 expired。"""
    today = timezone.now().date()
    if qr.deadline and qr.deadline < today and qr.status in {"assigned", "viewed"}:
        qr.status = "expired"
        qr.save(update_fields=["status", "updated_at"])
    return qr


class PublicServiceCategoryListView(APIView):
    def get(self, request):
        qs = ServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id")
        return success_response(
            {"items": ServiceCategorySerializer(qs, many=True).data},
            request=request,
        )


class MemberRFQListCreateView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = RFQ.objects.filter(buyer=request.user).select_related("service_category").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = RFQListSerializer(page, many=True, context={"lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = RFQCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data.get("scope", "internal")
        if scope not in {"internal", "public"}:
            scope = "internal"
        rfq = serializer.save(buyer=request.user, scope=scope, status="submitted")
        notify_staff(
            "quote",
            "新 RFQ 提交",
            f"会员提交询价 {rfq.rfq_no}，请及时受理。",
            related_type="rfq",
            related_id=rfq.id,
        )
        return success_response(
            RFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            message="询价已提交",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class MemberRFQDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        rfq = get_object_or_404(
            RFQ.objects.select_related("service_category", "buyer")
            .prefetch_related("attachments", "quotes__supplier__factory_profile"),
            pk=pk,
            buyer=request.user,
        )
        visible_plans = [q for q in rfq.quotes.all() if q.is_customer_visible]
        if visible_plans and rfq.status in {"quoted", "comparing"}:
            rfq.status = "customer_confirming"
            rfq.save(update_fields=["status", "updated_at"])
        return success_response(
            MemberRFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class MemberRFQAttachmentView(APIView):
    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        file_obj = request.FILES.get("file")
        if not file_obj:
            return error_response("MEDIA_FILE_TYPE_INVALID", "请上传文件", request=request)
        ext = file_obj.name.rsplit(".", 1)[-1].lower() if "." in file_obj.name else ""
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            return error_response(
                "MEDIA_FILE_TYPE_INVALID",
                "不支持的文件类型",
                errors={"ext": ext},
                request=request,
            )
        if file_obj.size > MAX_ATTACHMENT_SIZE:
            return error_response(
                "MEDIA_FILE_SIZE_EXCEEDED",
                "文件大小超限（最大 20MB）",
                request=request,
            )
        attachment = RFQAttachment.objects.create(
            rfq=rfq,
            file=file_obj,
            file_name=file_obj.name,
            file_type=ext,
            size=file_obj.size,
        )
        from apps.rfq.serializers import RFQAttachmentSerializer

        return success_response(
            RFQAttachmentSerializer(attachment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class MemberQuoteAcceptView(APIView):
    permission_classes = [IsBuyerRole]

    def post(self, request, pk, quote_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        quote = Quote.objects.filter(pk=quote_id, rfq=rfq).first()
        if not quote:
            return error_response(
                "QUOTE_NOT_FOUND",
                "报价不存在",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        if not quote.is_customer_visible:
            return error_response(
                "QUOTE_NOT_AVAILABLE",
                "该方案暂未开放确认",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        if quote.valid_until and quote.valid_until < timezone.now().date():
            return error_response("QUOTE_EXPIRED", "报价已过期", request=request)
        if not quote.supplier_id:
            return error_response(
                "QUOTE_SUPPLIER_REQUIRED",
                "平台报价无法生成生产订单，请联系客服线下履约",
                request=request,
            )
        if ProductionOrder.objects.filter(quote=quote).exists():
            return error_response("PRODUCTION_ORDER_EXISTS", "该报价已生成生产订单", request=request)

        with transaction.atomic():
            quote.status = "accepted"
            quote.save(update_fields=["status", "updated_at"])
            rfq.quotes.exclude(pk=quote.pk).update(status="rejected")
            if quote.quote_request_id:
                QuoteRequest.objects.filter(pk=quote.quote_request_id).update(status="adopted")
                not_adopted = QuoteRequest.objects.filter(rfq=rfq).exclude(pk=quote.quote_request_id)
                for qr in not_adopted:
                    qr.status = "not_adopted"
                    qr.save(update_fields=["status", "updated_at"])
                    notify(
                        qr.supplier,
                        "quote_request",
                        "报价未被采用",
                        f"询价 {rfq.rfq_no} 的报价未被客户采用。",
                        related_type="quote_request",
                        related_id=qr.id,
                    )
            rfq.status = "won"
            rfq.save(update_fields=["status", "updated_at"])
            production_order = ProductionOrder.objects.create(
                rfq=rfq,
                quote=quote,
                buyer=request.user,
                supplier=quote.supplier,
                price_amount=quote.price_amount,
                currency=quote.currency,
                lead_time_days=quote.lead_time_days,
                status="pending_confirm",
            )
            from apps.contract.services import create_contract_for_order
            from apps.payment.models import Payment

            contract = create_contract_for_order(production_order, quote)
            payment = Payment.objects.create(
                payment_no=Payment.generate_no(),
                contract=contract,
                buyer=request.user,
                amount=contract.amount,
                currency=contract.currency,
                status="unpaid",
            )
        notify(
            quote.supplier,
            "production_order",
            "新的生产订单待确认",
            f"询价 {rfq.rfq_no} 的报价已被客户采纳，请确认接单。",
            related_type="production_order",
            related_id=production_order.id,
            send_email=True,
        )
        if quote.quote_request_id:
            notify(
                quote.supplier,
                "quote_request",
                "报价已被采用",
                f"询价 {rfq.rfq_no} 的报价已被客户采用。",
                related_type="quote_request",
                related_id=quote.quote_request_id,
            )
        notify(
            request.user,
            "contract",
            "合同已生成",
            f"合同 {contract.contract_no} 已生成，请完成付款以启动项目。",
            related_type="contract",
            related_id=contract.id,
            send_email=True,
        )

        from apps.contract.serializers import ContractSerializer
        from apps.payment.serializers import PaymentSerializer

        return success_response(
            {
                "quote": QuoteSerializer(quote).data,
                "production_order": ProductionOrderSerializer(production_order).data,
                "contract": ContractSerializer(contract, context={"request": request}).data,
                "payment": PaymentSerializer(payment, context={"request": request}).data,
            },
            message="已确认方案，合同与付款单已生成",
            request=request,
        )


class PublicDemandHallListView(APIView):
    pagination_class = StandardPagination

    def get(self, request):
        qs = open_demand_hall_queryset()
        category_id = request.query_params.get("service_category_id")
        if category_id:
            qs = qs.filter(service_category_id=category_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = DemandHallListSerializer(page, many=True, context={"lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)


class PublicDemandHallDetailView(APIView):
    def get(self, request, pk):
        rfq = get_object_or_404(
            open_demand_hall_queryset().prefetch_related("attachments", "quotes"),
            pk=pk,
        )
        return success_response(
            DemandHallDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
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
                "rfq__attachments", "quotes"
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
            qr.rfq, context={"request": request, "lang": get_lang(request)}
        ).data
        my_quote = qr.quotes.filter(supplier=request.user).first()
        data["my_quote"] = QuoteSerializer(my_quote).data if my_quote else None
        return success_response(data, request=request)


class SupplierQuoteRequestQuoteView(APIView):
    """供应商针对抢单后的报价请求提交报价。"""

    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        qr = get_object_or_404(QuoteRequest, pk=pk, supplier=request.user)
        if qr.status in {"cancelled", "expired", "not_adopted", "adopted"}:
            return error_response(
                "QUOTE_REQUEST_CLOSED",
                "该报价请求已关闭，无法提交报价",
                request=request,
            )
        if Quote.objects.filter(quote_request=qr, supplier=request.user).exists():
            return error_response(
                "QUOTE_ALREADY_EXISTS",
                "您已对该报价请求提交过报价",
                request=request,
            )
        serializer = FactoryQuoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            quote = serializer.save(
                rfq=qr.rfq,
                quote_request=qr,
                supplier=request.user,
                created_by=request.user,
                status="sent",
            )
            qr.status = "quoted"
            qr.save(update_fields=["status", "updated_at"])
            rfq = qr.rfq
            if rfq.status in {"submitted", "pending_review", "assigned", "quoting"}:
                rfq.status = "quoting"
                rfq.save(update_fields=["status", "updated_at"])
        return success_response(
            QuoteSerializer(quote).data,
            message="报价已提交",
            status=status.HTTP_201_CREATED,
            request=request,
        )


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


class MemberProductionOrderListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = ProductionOrder.objects.filter(buyer=request.user).select_related("rfq", "supplier").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductionOrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MemberProductionOrderDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        order = get_object_or_404(
            ProductionOrder.objects.select_related("rfq", "supplier", "quote"),
            pk=pk,
            buyer=request.user,
        )
        return success_response(ProductionOrderSerializer(order).data, request=request)


class SupplierProductionOrderListView(APIView):
    permission_classes = [IsSupplierRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = ProductionOrder.objects.filter(supplier=request.user).select_related("rfq", "buyer").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductionOrderSerializer(page, many=True)
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
            ProductionOrderSerializer(order).data,
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
            ProductionOrderSerializer(order).data,
            message="已拒绝订单",
            request=request,
        )


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
        qs = RFQ.objects.select_related("service_category", "buyer").order_by("-created_at")
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


class MemberRFQQuotePdfView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        visible = [q for q in rfq.quotes.all() if q.is_customer_visible]
        if not visible:
            return error_response("QUOTE_PLANS_EMPTY", "暂无可下载的报价方案", request=request)
        visible.sort(key=lambda q: (q.plan_label or "", q.id))
        markup = rfq.markup_percent
        headers = ["项目"] + [f"方案 {q.plan_label or q.id}" for q in visible]
        rows = [
            ["总价"] + [f"{apply_markup(q.price_amount, markup):,}" for q in visible],
            ["单价"] + [f"{apply_markup(q.unit_price, markup):,}" if q.unit_price else "—" for q in visible],
            ["模具费"] + [f"{apply_markup(q.mold_fee, markup):,}" if q.mold_fee else "—" for q in visible],
            ["样品费"] + [f"{apply_markup(q.sample_fee, markup):,}" if q.sample_fee else "—" for q in visible],
            ["MOQ"] + [str(q.moq or "—") for q in visible],
            ["交期(天)"] + [str(q.lead_time_days) for q in visible],
            ["付款条件"] + [q.payment_terms or "—" for q in visible],
        ]
        pdf_bytes = build_comparison_pdf(
            title="比较报价书",
            quote_no=rfq.rfq_no,
            headers=headers,
            rows=rows,
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{rfq.rfq_no}-comparison.pdf"'
        return response
