from rest_framework import serializers

from apps.i18n.fields import resolve_i18n
from apps.rfq.models import RFQ, Quote, RFQAttachment, ServiceCategory


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
            "currency",
            "lead_time_days",
            "valid_until",
            "note",
            "status",
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
        return "Rysen"

    def get_supplier_type(self, obj):
        return "factory" if obj.supplier_id else "platform"


class FactoryQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ["price_amount", "currency", "lead_time_days", "valid_until", "note"]


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
            "status",
            "attachments",
            "quotes",
            "created_at",
            "updated_at",
        ]

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.service_category.name, lang) if obj.service_category else ""


class AdminQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ["price_amount", "currency", "lead_time_days", "valid_until", "note"]
