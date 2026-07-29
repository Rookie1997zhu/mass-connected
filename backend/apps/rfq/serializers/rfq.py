from rest_framework import serializers

from apps.i18n.fields import resolve_i18n
from apps.rfq.models import RFQ, ServiceCategory
from apps.rfq.serializers.attachments import RFQAttachmentSerializer
from apps.rfq.serializers.quotes import CustomerPlanSerializer, QuoteSerializer


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
        annotated = getattr(obj, "quotes_count", None)
        if annotated is not None and not callable(annotated):
            return int(annotated)
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
        annotated = getattr(obj, "quotes_count", None)
        if annotated is not None and not callable(annotated):
            return int(annotated)
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
