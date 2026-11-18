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
    idempotency_key = serializers.CharField(
        max_length=64, required=False, allow_blank=True, write_only=True
    )

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
            "idempotency_key",
        ]

    def create(self, validated_data):
        scope = validated_data.get("scope") or "internal"
        validated_data["solicitation_status"] = (
            RFQ.SOLICITATION_OPEN if scope == "public" else RFQ.SOLICITATION_CLOSED
        )
        key = (validated_data.get("idempotency_key") or "").strip()
        validated_data["idempotency_key"] = key
        return super().create(validated_data)


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
            "solicitation_status",
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


def build_public_demand_summary(obj, *, lang="ko") -> str:
    """公开大厅摘要：只用安全字段，不拼接原始 remark。"""
    parts = []
    if obj.service_category_id:
        name = resolve_i18n(obj.service_category.name, lang)
        if name:
            parts.append(str(name))
    if obj.material:
        parts.append(str(obj.material).strip())
    if obj.quantity:
        parts.append(f"x{obj.quantity}")
    if obj.surface_finish:
        parts.append(str(obj.surface_finish).strip())
    return " · ".join(p for p in parts if p)


class DemandHallListSerializer(serializers.ModelSerializer):
    service_category_name = serializers.SerializerMethodField()
    quotes_count = serializers.SerializerMethodField()
    public_summary = serializers.SerializerMethodField()

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
            "public_summary",
            "status",
            "solicitation_status",
            "quotes_count",
            "created_at",
        ]

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.service_category.name, lang) if obj.service_category else ""

    def get_public_summary(self, obj):
        return build_public_demand_summary(obj, lang=self.context.get("lang", "ko"))

    def get_quotes_count(self, obj):
        annotated = getattr(obj, "quotes_count", None)
        if annotated is not None and not callable(annotated):
            return int(annotated)
        return obj.quotes.count()


class DemandHallDetailSerializer(serializers.ModelSerializer):
    service_category_name = serializers.SerializerMethodField()
    public_summary = serializers.SerializerMethodField()
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
            "public_summary",
            "status",
            "solicitation_status",
            "attachments",
            "my_quote",
            "my_quote_request",
            "created_at",
            "updated_at",
        ]

    def get_service_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.service_category.name, lang) if obj.service_category else ""

    def get_public_summary(self, obj):
        return build_public_demand_summary(obj, lang=self.context.get("lang", "ko"))

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
            "solicitation_status",
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
    participants = serializers.SerializerMethodField()
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
            "solicitation_status",
            "attachments",
            "plans",
            "participants",
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

    def get_participants(self, obj):
        """报价前也可沟通：仅返回参与身份信息，不含供货金额。"""
        from apps.chat.models import Conversation

        items = []
        qrs = list(
            obj.quote_requests.exclude(status="cancelled").select_related(
                "supplier", "supplier__factory_profile"
            )
        )
        conv_map = {
            c.quote_request_id: c.id
            for c in Conversation.objects.filter(quote_request_id__in=[qr.id for qr in qrs]).only(
                "id", "quote_request_id"
            )
        }
        quotes = list(obj.quotes.all())
        for qr in qrs:
            profile = getattr(qr.supplier, "factory_profile", None)
            company = ""
            if profile and profile.company_name:
                company = profile.company_name
            elif qr.supplier_id:
                company = (qr.supplier.name or "").strip() or f"Supplier#{qr.supplier_id}"
            has_visible = any(
                q.is_customer_visible and q.quote_request_id == qr.id for q in quotes
            )
            items.append(
                {
                    "quote_request_id": qr.id,
                    "supplier_company_name": company,
                    "status": qr.status,
                    "has_visible_quote": has_visible,
                    "conversation_id": conv_map.get(qr.id),
                }
            )
        return items

    def get_can_edit(self, obj):
        return not obj.quotes.filter(supplier__isnull=False).exists() and obj.status not in {
            "won",
            "closed",
        }
