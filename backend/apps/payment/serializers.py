from rest_framework import serializers

from apps.payment.models import Payment
from core.media_urls import api_absolute_uri

PREVIEWABLE_PROOF_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "pdf"}


def proof_file_meta(obj):
    """付款凭证文件元信息，供买卖双方预览使用。"""
    if not obj.proof:
        return {
            "proof_file_name": "",
            "proof_file_ext": "",
            "proof_is_previewable": False,
        }
    name = (obj.proof.name or "").rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return {
        "proof_file_name": name,
        "proof_file_ext": ext,
        "proof_is_previewable": ext in PREVIEWABLE_PROOF_EXTS,
    }


class PaymentSerializer(serializers.ModelSerializer):
    proof_url = serializers.SerializerMethodField()
    proof_file_name = serializers.SerializerMethodField()
    proof_file_ext = serializers.SerializerMethodField()
    proof_is_previewable = serializers.SerializerMethodField()
    contract_no = serializers.CharField(source="contract.contract_no", read_only=True, default="")
    rfq = serializers.SerializerMethodField()
    rfq_no = serializers.SerializerMethodField()
    quote_request_id = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_no",
            "contract",
            "contract_no",
            "rfq",
            "rfq_no",
            "quote_request_id",
            "amount",
            "currency",
            "method",
            "status",
            "proof_url",
            "proof_file_name",
            "proof_file_ext",
            "proof_is_previewable",
            "note",
            "confirmed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_proof_url(self, obj):
        if not obj.proof:
            return ""
        return api_absolute_uri(
            self.context.get("request"),
            f"/api/member/payments/{obj.id}/proof/download",
        )

    def get_proof_file_name(self, obj):
        return proof_file_meta(obj)["proof_file_name"]

    def get_proof_file_ext(self, obj):
        return proof_file_meta(obj)["proof_file_ext"]

    def get_proof_is_previewable(self, obj):
        return proof_file_meta(obj)["proof_is_previewable"]

    def get_rfq(self, obj):
        if obj.contract_id and obj.contract:
            return obj.contract.rfq_id
        return None

    def get_rfq_no(self, obj):
        if obj.contract_id and obj.contract and obj.contract.rfq_id:
            return obj.contract.rfq.rfq_no
        return ""

    def get_quote_request_id(self, obj):
        if not obj.contract_id or not obj.contract:
            return None
        c = obj.contract
        if c.quote_id:
            return getattr(c.quote, "quote_request_id", None)
        po = getattr(c, "production_order", None)
        if po and po.quote_id:
            return getattr(po.quote, "quote_request_id", None)
        return None


class AdminPaymentSerializer(PaymentSerializer):
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + ["buyer", "buyer_email"]
        read_only_fields = fields

    def get_proof_url(self, obj):
        if not obj.proof:
            return ""
        return api_absolute_uri(
            self.context.get("request"),
            f"/api/admin/payments/{obj.id}/proof/download",
        )
