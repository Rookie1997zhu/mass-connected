from django.db import transaction
from django.db.models import Count
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.notification.services import notify, notify_staff
from apps.rfq.constants import PLATFORM_PAYMENT_TERMS
from apps.rfq.models import (
    ProductionOrder,
    Quote,
    QuoteAttachment,
    QuoteRequest,
    RFQ,
    RFQAttachment,
)
from apps.rfq.serializers import (
    CustomerQuoteDetailSerializer,
    MemberRFQDetailSerializer,
    ProductionOrderSerializer,
    QuoteSerializer,
    RFQCreateSerializer,
    RFQDetailSerializer,
    RFQListSerializer,
    apply_markup,
)
from core.pagination import StandardPagination
from core.pdf import build_comparison_pdf
from core.permissions import IsBuyerRole, IsEmailVerified
from core.responses import error_response, success_response

from ._helpers import (
    ALLOWED_ATTACHMENT_EXTENSIONS,
    MAX_ATTACHMENT_SIZE,
    _download_quote_attachment,
    get_lang,
)


class MemberRFQListCreateView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsBuyerRole(), IsEmailVerified()]
        return [IsBuyerRole()]

    def get(self, request):
        qs = (
            RFQ.objects.filter(buyer=request.user)
            .select_related("service_category")
            .annotate(quotes_count=Count("quotes", distinct=True))
            .order_by("-created_at")
        )
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
            from apps.chat.services import link_conversation_to_order

            if quote.quote_request_id:
                link_conversation_to_order(
                    quote.quote_request_id, production_order=production_order
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
            ["付款条件"] + [(q.payment_terms or PLATFORM_PAYMENT_TERMS) for q in visible],
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
