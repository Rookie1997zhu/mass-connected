from rest_framework import serializers

from apps.rfq.models import ProductionOrder


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
        if not obj.proof:
            return ""
        from core.media_urls import api_absolute_uri

        return api_absolute_uri(
            self.context.get("request"),
            f"/api/supplier/payments/{obj.id}/proof/download",
        )

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
