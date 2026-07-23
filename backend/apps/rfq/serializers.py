from rest_framework import serializers

from apps.i18n.fields import resolve_i18n
from apps.rfq.models import (
    ProductionOrder,
    QuoteAttachment,
    RFQ,
    Quote,
    QuoteRequest,
    RFQAttachment,
    ServiceCategory,
)
from core.document_preview import CONVERT_TO_PDF_EXTS, preview_mode_for_ext

PREVIEWABLE_EXTS = {
    "xlsx",
    "xls",
    "csv",
    "docx",
    "doc",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "pdf",
}
TRANSLATABLE_EXTS = {"pdf", *CONVERT_TO_PDF_EXTS, "docx", "doc", "xlsx", "xls", "csv"}
MAX_QUOTE_ATTACHMENTS = 10


def apply_markup(amount, markup_percent):
    if not amount:
        return amount
    return int(round(amount * (100 + (markup_percent or 0)) / 100))


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = [
            "id",
            "parent",
            "name",
            "slug",
            "icon",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RFQAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()
    preview_mode = serializers.SerializerMethodField()
    preview_pdf_url = serializers.SerializerMethodField()
    is_translatable = serializers.SerializerMethodField()

    class Meta:
        model = RFQAttachment
        fields = [
            "id",
            "file_name",
            "file_type",
            "size",
            "url",
            "file_url",
            "file_ext",
            "is_previewable",
            "preview_mode",
            "preview_pdf_url",
            "is_translatable",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_file_ext(self, obj):
        name = obj.file_name or ""
        if "." not in name:
            return (obj.file_type or "").lower()
        return name.rsplit(".", 1)[-1].lower()

    def get_is_previewable(self, obj):
        return self.get_file_ext(obj) in PREVIEWABLE_EXTS

    def get_preview_mode(self, obj):
        return preview_mode_for_ext(self.get_file_ext(obj))

    def get_is_translatable(self, obj):
        return self.get_file_ext(obj) in TRANSLATABLE_EXTS

    def _rfq_attachment_api_base(self, obj):
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        user = request.user
        rfq = obj.rfq
        # Buyer owns the RFQ
        if rfq.buyer_id == user.id:
            return f"/api/member/rfqs/{rfq.id}/attachments/{obj.id}"
        # Supplier access goes through quote-request path
        qr_id = self.context.get("quote_request_id")
        if qr_id:
            return f"/api/supplier/quote-requests/{qr_id}/rfq-attachments/{obj.id}"
        qr = QuoteRequest.objects.filter(rfq=rfq, supplier=user).order_by("-id").first()
        if qr:
            return f"/api/supplier/quote-requests/{qr.id}/rfq-attachments/{obj.id}"
        return f"/api/member/rfqs/{rfq.id}/attachments/{obj.id}"

    def get_file_url(self, obj):
        request = self.context.get("request")
        base = self._rfq_attachment_api_base(obj)
        if not base or not request:
            return self.get_url(obj)
        return request.build_absolute_uri(f"{base}/download")

    def get_url(self, obj):
        """Backward-compatible alias; prefer authenticated file_url."""
        return self.get_file_url(obj)

    def get_preview_pdf_url(self, obj):
        ext = self.get_file_ext(obj)
        mode = preview_mode_for_ext(ext)
        if mode not in {"direct", "pdf_convert"}:
            return ""
        request = self.context.get("request")
        base = self._rfq_attachment_api_base(obj)
        if not base or not request:
            return ""
        return request.build_absolute_uri(f"{base}/preview-pdf")


class QuoteAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()
    preview_mode = serializers.SerializerMethodField()
    preview_pdf_url = serializers.SerializerMethodField()
    is_translatable = serializers.SerializerMethodField()

    class Meta:
        model = QuoteAttachment
        fields = [
            "id",
            "file_name",
            "file_type",
            "size",
            "file_url",
            "file_ext",
            "is_previewable",
            "preview_mode",
            "preview_pdf_url",
            "is_translatable",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_file_ext(self, obj):
        name = obj.file_name or ""
        if "." not in name:
            return obj.file_type or ""
        return name.rsplit(".", 1)[-1].lower()

    def get_is_previewable(self, obj):
        return self.get_file_ext(obj) in PREVIEWABLE_EXTS

    def get_preview_mode(self, obj):
        return preview_mode_for_ext(self.get_file_ext(obj))

    def get_is_translatable(self, obj):
        return self.get_file_ext(obj) in TRANSLATABLE_EXTS

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        user = request.user
        quote = obj.quote
        if quote.supplier_id == user.id:
            path = f"/api/supplier/quotes/{quote.id}/attachments/{obj.id}/download"
        else:
            path = f"/api/member/quotes/{quote.id}/attachments/{obj.id}/download"
        return request.build_absolute_uri(path)

    def get_preview_pdf_url(self, obj):
        ext = self.get_file_ext(obj)
        mode = preview_mode_for_ext(ext)
        if mode not in {"direct", "pdf_convert"}:
            return ""
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        user = request.user
        quote = obj.quote
        if quote.supplier_id == user.id:
            base = f"/api/supplier/quotes/{quote.id}/attachments/{obj.id}"
        else:
            base = f"/api/member/quotes/{quote.id}/attachments/{obj.id}"
        return request.build_absolute_uri(f"{base}/preview-pdf")


class QuoteSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    supplier_type = serializers.SerializerMethodField()
    attachments = QuoteAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Quote
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "supplier_type",
            "price_amount",
            "unit_price",
            "mold_fee",
            "sample_fee",
            "moq",
            "payment_terms",
            "currency",
            "lead_time_days",
            "valid_until",
            "note",
            "status",
            "is_customer_visible",
            "plan_label",
            "revision_version",
            "revised_at",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "supplier",
            "status",
            "revision_version",
            "revised_at",
            "attachments",
            "created_at",
            "updated_at",
        ]

    def get_supplier_name(self, obj):
        if obj.supplier_id:
            profile = getattr(obj.supplier, "factory_profile", None)
            if profile:
                return profile.company_name
            return obj.supplier.name or obj.supplier.email
        return "平台"

    def get_supplier_type(self, obj):
        return "factory" if obj.supplier_id else "platform"


class CustomerPlanSerializer(serializers.ModelSerializer):
    """面向客户的方案展示：显示供应商企业名（无联系方式），价格按平台加价率呈现。"""

    supplier_name = serializers.SerializerMethodField()
    price_amount = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    mold_fee = serializers.SerializerMethodField()
    sample_fee = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            "id",
            "plan_label",
            "quote_request_id",
            "supplier_name",
            "price_amount",
            "unit_price",
            "mold_fee",
            "sample_fee",
            "moq",
            "payment_terms",
            "currency",
            "lead_time_days",
            "valid_until",
            "note",
            "status",
            "revision_version",
            "attachment_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_supplier_name(self, obj):
        if obj.supplier_id:
            profile = getattr(obj.supplier, "factory_profile", None)
            if profile and profile.company_name:
                return profile.company_name
            return obj.supplier.name or "供应商"
        return "平台"

    def get_price_amount(self, obj):
        markup = self.context.get("markup_percent", 0)
        return apply_markup(obj.price_amount, markup)

    def get_unit_price(self, obj):
        if obj.unit_price is None:
            return None
        markup = self.context.get("markup_percent", 0)
        return apply_markup(obj.unit_price, markup)

    def get_mold_fee(self, obj):
        if obj.mold_fee is None:
            return None
        markup = self.context.get("markup_percent", 0)
        return apply_markup(obj.mold_fee, markup)

    def get_sample_fee(self, obj):
        if obj.sample_fee is None:
            return None
        markup = self.context.get("markup_percent", 0)
        return apply_markup(obj.sample_fee, markup)

    def get_attachment_count(self, obj):
        if hasattr(obj, "_prefetched_objects_cache") and "attachments" in obj._prefetched_objects_cache:
            return len(obj.attachments.all())
        return obj.attachments.count()


class CustomerQuoteDetailSerializer(CustomerPlanSerializer):
    """买家报价详情：含分项客户价、供应商公开资料与报价附件。"""

    supplier_profile = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta(CustomerPlanSerializer.Meta):
        fields = CustomerPlanSerializer.Meta.fields + [
            "supplier_profile",
            "attachments",
            "revised_at",
        ]

    def get_supplier_profile(self, obj):
        from apps.accounts.serializers import PublicSupplierProfileSerializer

        if not obj.supplier_id:
            return None
        profile = getattr(obj.supplier, "factory_profile", None)
        if not profile:
            return None
        ctx = {
            **self.context,
            "quote_id": obj.id,
            "rfq_id": obj.rfq_id,
        }
        return PublicSupplierProfileSerializer(profile, context=ctx).data

    def get_attachments(self, obj):
        return QuoteAttachmentSerializer(
            obj.attachments.all(), many=True, context=self.context
        ).data


class FactoryQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = [
            "price_amount",
            "unit_price",
            "mold_fee",
            "sample_fee",
            "moq",
            "currency",
            "lead_time_days",
            "valid_until",
            "note",
        ]

    def create(self, validated_data):
        from apps.rfq.constants import PLATFORM_PAYMENT_TERMS

        validated_data["payment_terms"] = PLATFORM_PAYMENT_TERMS
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from apps.rfq.constants import PLATFORM_PAYMENT_TERMS

        validated_data["payment_terms"] = PLATFORM_PAYMENT_TERMS
        return super().update(instance, validated_data)


class AdminQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = [
            "price_amount",
            "unit_price",
            "mold_fee",
            "sample_fee",
            "moq",
            "currency",
            "lead_time_days",
            "valid_until",
            "note",
            "is_customer_visible",
            "plan_label",
        ]

    def create(self, validated_data):
        from apps.rfq.constants import PLATFORM_PAYMENT_TERMS

        validated_data["payment_terms"] = PLATFORM_PAYMENT_TERMS
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from apps.rfq.constants import PLATFORM_PAYMENT_TERMS

        validated_data["payment_terms"] = PLATFORM_PAYMENT_TERMS
        return super().update(instance, validated_data)


class QuoteRequestSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    rfq_no = serializers.CharField(source="rfq.rfq_no", read_only=True)
    service_category_name = serializers.SerializerMethodField()
    quantity = serializers.IntegerField(source="rfq.quantity", read_only=True)
    has_quote = serializers.SerializerMethodField()

    class Meta:
        model = QuoteRequest
        fields = [
            "id",
            "request_no",
            "rfq",
            "rfq_no",
            "service_category_name",
            "quantity",
            "supplier",
            "supplier_name",
            "status",
            "deadline",
            "admin_note",
            "is_urgent",
            "has_quote",
            "created_at",
        ]
        read_only_fields = fields

    def get_supplier_name(self, obj):
        profile = getattr(obj.supplier, "factory_profile", None)
        if profile:
            return profile.company_name
        return obj.supplier.name or obj.supplier.email

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        sc = obj.rfq.service_category
        return resolve_i18n(sc.name, lang) if sc else ""

    def get_has_quote(self, obj):
        return obj.quotes.exists()


class RFQCreateSerializer(serializers.ModelSerializer):
    service_category = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.filter(is_active=True)
    )
    scope = serializers.ChoiceField(choices=["internal", "public"], default="internal")

    class Meta:
        model = RFQ
        fields = [
            "service_category",
            "scope",
            "contact_name",
            "contact_phone",
            "company",
            "material",
            "quantity",
            "tolerance",
            "surface_finish",
            "target_delivery_date",
            "budget_amount",
            "currency",
            "remark",
        ]


class RFQListSerializer(serializers.ModelSerializer):
    service_category_name = serializers.SerializerMethodField()
    quotes_count = serializers.SerializerMethodField()

    class Meta:
        model = RFQ
        fields = [
            "id",
            "rfq_no",
            "service_category",
            "service_category_name",
            "scope",
            "status",
            "quantity",
            "quotes_count",
            "created_at",
        ]

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.service_category.name, lang) if obj.service_category else ""

    def get_quotes_count(self, obj):
        return obj.quotes.count()


class DemandHallListSerializer(serializers.ModelSerializer):
    service_category_name = serializers.SerializerMethodField()
    quotes_count = serializers.SerializerMethodField()

    class Meta:
        model = RFQ
        fields = [
            "id",
            "rfq_no",
            "service_category",
            "service_category_name",
            "material",
            "quantity",
            "tolerance",
            "surface_finish",
            "target_delivery_date",
            "budget_amount",
            "currency",
            "remark",
            "status",
            "quotes_count",
            "created_at",
        ]

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.service_category.name, lang) if obj.service_category else ""

    def get_quotes_count(self, obj):
        return obj.quotes.count()


class DemandHallDetailSerializer(serializers.ModelSerializer):
    service_category_name = serializers.SerializerMethodField()
    attachments = RFQAttachmentSerializer(many=True, read_only=True)
    my_quote = serializers.SerializerMethodField()
    my_quote_request = serializers.SerializerMethodField()

    class Meta:
        model = RFQ
        fields = [
            "id",
            "rfq_no",
            "service_category",
            "service_category_name",
            "material",
            "quantity",
            "tolerance",
            "surface_finish",
            "target_delivery_date",
            "budget_amount",
            "currency",
            "remark",
            "status",
            "attachments",
            "my_quote",
            "my_quote_request",
            "created_at",
            "updated_at",
        ]

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.service_category.name, lang) if obj.service_category else ""

    def get_my_quote(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        quote = obj.quotes.filter(supplier=request.user).first()
        if not quote:
            return None
        return QuoteSerializer(quote).data

    def get_my_quote_request(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        qr = obj.quote_requests.filter(supplier=request.user).exclude(status="cancelled").first()
        if not qr:
            return None
        return {
            "id": qr.id,
            "request_no": qr.request_no,
            "status": qr.status,
        }


class RFQDetailSerializer(serializers.ModelSerializer):
    service_category_name = serializers.SerializerMethodField()
    attachments = RFQAttachmentSerializer(many=True, read_only=True)
    quotes = QuoteSerializer(many=True, read_only=True)
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)
    buyer_name = serializers.CharField(source="buyer.name", read_only=True)

    class Meta:
        model = RFQ
        fields = [
            "id",
            "rfq_no",
            "buyer",
            "buyer_email",
            "buyer_name",
            "scope",
            "service_category",
            "service_category_name",
            "contact_name",
            "contact_phone",
            "company",
            "material",
            "quantity",
            "tolerance",
            "surface_finish",
            "target_delivery_date",
            "budget_amount",
            "currency",
            "remark",
            "markup_percent",
            "status",
            "attachments",
            "quotes",
            "created_at",
            "updated_at",
        ]

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.service_category.name, lang) if obj.service_category else ""


class MemberRFQDetailSerializer(serializers.ModelSerializer):
    """会员端 RFQ 详情：仅展示平台已公开的方案，显示供应商企业名与加价后价格。"""

    service_category_name = serializers.SerializerMethodField()
    attachments = RFQAttachmentSerializer(many=True, read_only=True)
    plans = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = RFQ
        fields = [
            "id",
            "rfq_no",
            "scope",
            "service_category",
            "service_category_name",
            "contact_name",
            "contact_phone",
            "company",
            "material",
            "quantity",
            "tolerance",
            "surface_finish",
            "target_delivery_date",
            "budget_amount",
            "currency",
            "remark",
            "status",
            "attachments",
            "plans",
            "can_edit",
            "created_at",
            "updated_at",
        ]

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.service_category.name, lang) if obj.service_category else ""

    def get_plans(self, obj):
        visible = [q for q in obj.quotes.all() if q.is_customer_visible]
        visible.sort(key=lambda q: (q.plan_label or "", q.id))
        return CustomerPlanSerializer(
            visible, many=True, context={"markup_percent": obj.markup_percent}
        ).data

    def get_can_edit(self, obj):
        return not obj.quotes.filter(supplier__isnull=False).exists() and obj.status not in {
            "won",
            "closed",
        }


class AdminQuoteRequestCreateSerializer(serializers.Serializer):
    supplier_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    deadline = serializers.DateField(required=False, allow_null=True)
    admin_note = serializers.CharField(required=False, allow_blank=True)
    is_urgent = serializers.BooleanField(default=False)


class SupplierPaymentSummarySerializer(serializers.Serializer):
    """供应商只读付款摘要：含凭证预览信息，不含内部备注。"""

    id = serializers.IntegerField()
    payment_no = serializers.CharField()
    status = serializers.CharField()
    amount = serializers.SerializerMethodField()
    currency = serializers.CharField()
    updated_at = serializers.DateTimeField()
    confirmed_at = serializers.DateTimeField(allow_null=True)
    proof_url = serializers.SerializerMethodField()
    proof_file_name = serializers.SerializerMethodField()
    proof_file_ext = serializers.SerializerMethodField()
    proof_is_previewable = serializers.SerializerMethodField()

    def get_amount(self, obj):
        order = self.context.get("production_order")
        if order is not None:
            return order.display_supplier_amount()
        return obj.amount

    def get_proof_url(self, obj):
        request = self.context.get("request")
        if obj.proof and request:
            return request.build_absolute_uri(obj.proof.url)
        return obj.proof.url if obj.proof else ""

    def get_proof_file_name(self, obj):
        from apps.payment.serializers import proof_file_meta

        return proof_file_meta(obj)["proof_file_name"]

    def get_proof_file_ext(self, obj):
        from apps.payment.serializers import proof_file_meta

        return proof_file_meta(obj)["proof_file_ext"]

    def get_proof_is_previewable(self, obj):
        from apps.payment.serializers import proof_file_meta

        return proof_file_meta(obj)["proof_is_previewable"]


class ProductionOrderSerializer(serializers.ModelSerializer):
    rfq_no = serializers.CharField(source="rfq.rfq_no", read_only=True)
    quote_request_id = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()
    price_amount = serializers.SerializerMethodField()
    supplier_amount = serializers.SerializerMethodField()
    customer_amount = serializers.SerializerMethodField()

    class Meta:
        model = ProductionOrder
        fields = [
            "id",
            "order_no",
            "rfq",
            "rfq_no",
            "quote",
            "quote_request_id",
            "buyer",
            "supplier",
            "supplier_name",
            "status",
            "price_amount",
            "supplier_amount",
            "customer_amount",
            "markup_percent_snapshot",
            "currency",
            "lead_time_days",
            "confirmed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_quote_request_id(self, obj):
        if not obj.quote_id:
            return None
        return obj.quote.quote_request_id

    def get_supplier_name(self, obj):
        profile = getattr(obj.supplier, "factory_profile", None)
        if profile:
            return profile.company_name
        return obj.supplier.name or obj.supplier.email

    def get_price_amount(self, obj):
        request = self.context.get("request")
        if request and request.user.id == obj.supplier_id:
            return obj.display_supplier_amount()
        return obj.display_customer_amount()

    def get_supplier_amount(self, obj):
        request = self.context.get("request")
        if request and (
            request.user.id == obj.supplier_id
            or getattr(request.user, "role", "") == "admin"
        ):
            return obj.display_supplier_amount()
        return None

    def get_customer_amount(self, obj):
        return obj.display_customer_amount()


class AdminProductionOrderSerializer(serializers.ModelSerializer):
    rfq_no = serializers.CharField(source="rfq.rfq_no", read_only=True)
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)
    supplier_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductionOrder
        fields = [
            "id",
            "order_no",
            "rfq",
            "rfq_no",
            "quote",
            "buyer",
            "buyer_email",
            "supplier",
            "supplier_name",
            "status",
            "price_amount",
            "supplier_amount",
            "customer_amount",
            "markup_percent_snapshot",
            "currency",
            "lead_time_days",
            "confirmed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "order_no",
            "rfq",
            "rfq_no",
            "quote",
            "buyer",
            "buyer_email",
            "supplier",
            "supplier_name",
            "supplier_amount",
            "customer_amount",
            "markup_percent_snapshot",
            "created_at",
        ]

    def get_supplier_name(self, obj):
        profile = getattr(obj.supplier, "factory_profile", None)
        if profile:
            return profile.company_name
        return obj.supplier.name or obj.supplier.email
