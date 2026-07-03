from rest_framework import serializers

from apps.i18n.fields import resolve_i18n
from apps.rfq.models import (
    ProductionOrder,
    RFQ,
    Quote,
    QuoteRequest,
    RFQAttachment,
    ServiceCategory,
)


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

    class Meta:
        model = RFQAttachment
        fields = ["id", "file_name", "file_type", "size", "url", "uploaded_at"]
        read_only_fields = fields

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""


class QuoteSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    supplier_type = serializers.SerializerMethodField()

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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "supplier", "status", "created_at", "updated_at"]

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
    """面向客户的方案展示：隐藏供应商身份，价格按平台加价率呈现。"""

    price_amount = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    mold_fee = serializers.SerializerMethodField()
    sample_fee = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            "id",
            "plan_label",
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
            "created_at",
        ]
        read_only_fields = fields

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


class FactoryQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = [
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
        ]


class AdminQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = [
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
            "is_customer_visible",
            "plan_label",
        ]


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
    """会员端 RFQ 详情：仅展示平台已公开的方案 A/B/C，隐藏供应商身份。"""

    service_category_name = serializers.SerializerMethodField()
    attachments = RFQAttachmentSerializer(many=True, read_only=True)
    plans = serializers.SerializerMethodField()

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


class AdminQuoteRequestCreateSerializer(serializers.Serializer):
    supplier_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    deadline = serializers.DateField(required=False, allow_null=True)
    admin_note = serializers.CharField(required=False, allow_blank=True)
    is_urgent = serializers.BooleanField(default=False)


class ProductionOrderSerializer(serializers.ModelSerializer):
    rfq_no = serializers.CharField(source="rfq.rfq_no", read_only=True)
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
            "supplier",
            "supplier_name",
            "status",
            "price_amount",
            "currency",
            "lead_time_days",
            "confirmed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_supplier_name(self, obj):
        profile = getattr(obj.supplier, "factory_profile", None)
        if profile:
            return profile.company_name
        return obj.supplier.name or obj.supplier.email


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
            "currency",
            "lead_time_days",
            "confirmed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "order_no", "rfq", "rfq_no", "quote", "buyer", "buyer_email", "supplier", "supplier_name", "created_at"]

    def get_supplier_name(self, obj):
        profile = getattr(obj.supplier, "factory_profile", None)
        if profile:
            return profile.company_name
        return obj.supplier.name or obj.supplier.email
