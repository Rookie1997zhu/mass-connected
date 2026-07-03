from rest_framework import serializers

from apps.payment.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    proof_url = serializers.SerializerMethodField()
    contract_no = serializers.CharField(source="contract.contract_no", read_only=True, default="")

    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_no",
            "contract",
            "contract_no",
            "amount",
            "currency",
            "method",
            "status",
            "proof_url",
            "note",
            "confirmed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_proof_url(self, obj):
        request = self.context.get("request")
        if obj.proof and request:
            return request.build_absolute_uri(obj.proof.url)
        return obj.proof.url if obj.proof else ""


class AdminPaymentSerializer(PaymentSerializer):
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + ["buyer", "buyer_email"]
        read_only_fields = fields
