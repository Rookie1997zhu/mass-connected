from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.rfq.models import (
    ProductionOrder,
    QuoteAttachment,
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
    CustomerQuoteDetailSerializer,
    DemandHallDetailSerializer,
    DemandHallListSerializer,
    FactoryQuoteCreateSerializer,
    MAX_QUOTE_ATTACHMENTS,
    MemberRFQDetailSerializer,
    ProductionOrderSerializer,
    QuoteAttachmentSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
    RFQCreateSerializer,
    RFQDetailSerializer,
    RFQListSerializer,
    ServiceCategorySerializer,
    apply_markup,
)
from core.file_validation import validate_upload_file
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


def next_plan_label(rfq):
    """为自动开放的供应商报价分配方案标签 Plan A/B/C…"""
    used = set(
        Quote.objects.filter(rfq=rfq)
        .exclude(plan_label="")
        .values_list("plan_label", flat=True)
    )
    for letter in "ABCDEF":
        candidate = f"Plan {letter}"
        if candidate not in used and letter not in used:
            return candidate
    return ""


def publish_supplier_quote_to_buyer(quote, rfq, *, notify_buyer=True):
    """供应商报价提交后立即对买家可见，并推进 RFQ 至比价状态。"""
    was_visible = bool(quote.is_customer_visible)
    update_fields = []
    if not quote.is_customer_visible:
        quote.is_customer_visible = True
        update_fields.append("is_customer_visible")
    if not (quote.plan_label or "").strip():
        quote.plan_label = next_plan_label(rfq)
        update_fields.append("plan_label")
    if update_fields:
        quote.save(update_fields=[*update_fields, "updated_at"])

    if rfq.status in {
        "submitted",
        "pending_review",
        "assigned",
        "quoting",
        "quoted",
    }:
        rfq.status = "comparing"
        rfq.save(update_fields=["status", "updated_at"])

    if notify_buyer and not was_visible:
        notify(
            rfq.buyer,
            "quote",
            "报价方案已就绪",
            f"询价 {rfq.rfq_no} 有新的报价方案可供对比确认。",
            related_type="rfq",
            related_id=rfq.id,
            send_email=True,
        )
    return quote


def _quote_upload_files(request):
    files = list(request.FILES.getlist("attachments"))
    if not files and request.FILES.get("file"):
        files = [request.FILES.get("file")]
    return [f for f in files if f]


def _validate_quote_attachment_files(files, existing_count=0, request=None):
    if existing_count + len(files) > MAX_QUOTE_ATTACHMENTS:
        return error_response(
            "QUOTE_ATTACHMENT_LIMIT",
            f"每份报价最多上传 {MAX_QUOTE_ATTACHMENTS} 个附件",
            request=request,
        )
    for file_obj in files:
        code, msg = validate_upload_file(file_obj)
        if code:
            return error_response(code, msg, request=request)
    return None


def _save_quote_attachments(quote, files, uploader):
    created = []
    for file_obj in files:
        code, ext = validate_upload_file(file_obj)
        if code:
            continue
        att = QuoteAttachment.objects.create(
            quote=quote,
            file=file_obj,
            file_name=file_obj.name,
            file_type=ext or "",
            size=file_obj.size or 0,
            uploader=uploader,
        )
        created.append(att)
    return created


def _quote_is_locked(quote):
    return quote.status == "accepted" or quote.rfq.status == "won"


def _download_quote_attachment(attachment):
    if not attachment.file:
        return error_response("QUOTE_ATTACHMENT_MISSING", "文件不存在")
    return FileResponse(
        attachment.file.open("rb"),
        as_attachment=False,
        filename=attachment.file_name,
    )


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
            RFQ.objects.select_related("service_category", "buyer").prefetch_related(
                "attachments",
                "quotes__attachments",
                "quotes__supplier__factory_profile",
            ),
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

    def patch(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        if rfq.quotes.filter(supplier__isnull=False).exists():
            return error_response(
                "RFQ_LOCKED_AFTER_QUOTE",
                "已有供应商报价，询价不可再修改",
                request=request,
            )
        if rfq.status in {"won", "closed"}:
            return error_response("RFQ_STATUS_LOCKED", "当前状态不可修改询价", request=request)
        serializer = RFQCreateSerializer(rfq, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data.get("scope", rfq.scope)
        if scope not in {"internal", "public"}:
            scope = rfq.scope
        rfq = serializer.save(scope=scope)
        return success_response(
            MemberRFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            message="询价已更新",
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


class MemberRfqFulfillmentView(APIView):
    """买家：按 RFQ 聚合合同、付款、项目与本单文件。"""

    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        from apps.rfq.fulfillment import build_buyer_fulfillment

        rfq = get_object_or_404(
            RFQ.objects.prefetch_related("attachments"),
            pk=pk,
            buyer=request.user,
        )
        return success_response(build_buyer_fulfillment(rfq, request), request=request)


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
            markup = rfq.markup_percent or 0
            supplier_amount = quote.price_amount
            customer_amount = apply_markup(supplier_amount, markup)
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
                price_amount=customer_amount,
                supplier_amount=supplier_amount,
                customer_amount=customer_amount,
                markup_percent_snapshot=markup,
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
                "production_order": ProductionOrderSerializer(
                    production_order, context={"request": request}
                ).data,
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
        quote = Quote.objects.prefetch_related("attachments").get(pk=quote.pk)
        return success_response(
            QuoteSerializer(quote, context={"request": request}).data,
            message=message,
            status=status.HTTP_201_CREATED if not existing else status.HTTP_200_OK,
            request=request,
        )

    def patch(self, request, pk):
        return self.post(request, pk)


class MemberQuoteDetailView(APIView):
    """买家查看单个已开放报价详情（含企业公开资料与附件）。"""

    permission_classes = [IsBuyerRole]

    def get(self, request, pk, quote_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        quote = get_object_or_404(
            Quote.objects.select_related(
                "supplier",
                "supplier__factory_profile",
            ).prefetch_related(
                "attachments",
                "supplier__factory_profile__processes",
                "supplier__factory_profile__tags",
                "supplier__factory_profile__attachments",
            ),
            pk=quote_id,
            rfq=rfq,
        )
        if not quote.is_customer_visible:
            return error_response(
                "QUOTE_NOT_VISIBLE",
                "该方案暂未开放",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        return success_response(
            CustomerQuoteDetailSerializer(
                quote,
                context={
                    "request": request,
                    "lang": get_lang(request),
                    "markup_percent": rfq.markup_percent,
                    "quote_id": quote.id,
                    "rfq_id": rfq.id,
                },
            ).data,
            request=request,
        )


class MemberQuoteAttachmentDownloadView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, quote_id, file_id):
        quote = get_object_or_404(
            Quote.objects.select_related("rfq"),
            pk=quote_id,
            rfq__buyer=request.user,
            is_customer_visible=True,
        )
        attachment = get_object_or_404(QuoteAttachment, pk=file_id, quote=quote)
        return _download_quote_attachment(attachment)


class MemberSupplierAttachmentDownloadView(APIView):
    """买家下载报价关联供应商的公开企业资料附件。"""

    permission_classes = [IsBuyerRole]

    def get(self, request, pk, quote_id, attachment_id):
        from apps.accounts.models import SupplierAttachment
        from apps.accounts.serializers import PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES

        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        quote = get_object_or_404(
            Quote,
            pk=quote_id,
            rfq=rfq,
            is_customer_visible=True,
        )
        if not quote.supplier_id:
            return error_response(
                "SUPPLIER_ATTACHMENT_FORBIDDEN",
                "无权访问该文件",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        profile = getattr(quote.supplier, "factory_profile", None)
        if not profile:
            return error_response(
                "SUPPLIER_ATTACHMENT_FORBIDDEN",
                "无权访问该文件",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        att = get_object_or_404(
            SupplierAttachment,
            pk=attachment_id,
            profile=profile,
            is_public=True,
            category__in=PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES,
        )
        if not att.file:
            return error_response("SUPPLIER_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


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


class MemberProductionOrderListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = ProductionOrder.objects.filter(buyer=request.user).select_related("rfq", "supplier").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductionOrderSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class MemberProductionOrderDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        order = get_object_or_404(
            ProductionOrder.objects.select_related("rfq", "supplier", "quote"),
            pk=pk,
            buyer=request.user,
        )
        return success_response(
            ProductionOrderSerializer(order, context={"request": request}).data,
            request=request,
        )


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
        rfq = get_object_or_404(
            RFQ.objects.prefetch_related("quotes__supplier__factory_profile"),
            pk=pk,
            buyer=request.user,
        )
        visible = [q for q in rfq.quotes.all() if q.is_customer_visible]
        if not visible:
            return error_response("QUOTE_PLANS_EMPTY", "暂无可下载的报价方案", request=request)
        visible.sort(key=lambda q: (q.plan_label or "", q.id))
        markup = rfq.markup_percent
        headers = ["项目"] + [f"方案 {q.plan_label or q.id}" for q in visible]
        supplier_names = []
        for q in visible:
            if q.supplier_id:
                profile = getattr(q.supplier, "factory_profile", None)
                supplier_names.append(
                    (profile.company_name if profile and profile.company_name else None)
                    or q.supplier.name
                    or "供应商"
                )
            else:
                supplier_names.append("平台")
        rows = [
            ["供应商"] + supplier_names,
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
