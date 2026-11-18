from rest_framework import serializers

from apps.i18n.fields import resolve_i18n
from apps.rfq.models import Quote, QuoteRequest
from apps.rfq.serializers.attachments import QuoteAttachmentSerializer
from apps.rfq.serializers.base import apply_markup


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
            "revised_at",
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


class AdminQuoteRequestCreateSerializer(serializers.Serializer):
    supplier_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    deadline = serializers.DateField(required=False, allow_null=True)
    admin_note = serializers.CharField(required=False, allow_blank=True)
    is_urgent = serializers.BooleanField(default=False)
