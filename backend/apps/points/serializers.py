from rest_framework import serializers

from apps.points.models import PointRule, PointTransaction, PointWallet, RechargeOrder


class PointWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointWallet
        fields = [
            "balance",
            "frozen_balance",
            "total_earned",
            "total_spent",
            "total_recharged",
            "updated_at",
        ]
        read_only_fields = fields


class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTransaction
        fields = [
            "id",
            "transaction_no",
            "type",
            "amount",
            "balance_after",
            "source_type",
            "source_id",
            "description",
            "created_at",
        ]
        read_only_fields = fields


class PointRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointRule
        fields = [
            "id",
            "rule_code",
            "rule_name",
            "rule_type",
            "point_amount",
            "enabled",
            "description",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class RechargeOrderSerializer(serializers.ModelSerializer):
    proof_url = serializers.SerializerMethodField()

    class Meta:
        model = RechargeOrder
        fields = [
            "id",
            "recharge_no",
            "amount_krw",
            "vat_amount",
            "total_pay_amount",
            "point_amount",
            "payment_method",
            "status",
            "proof_url",
            "confirmed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_proof_url(self, obj):
        request = self.context.get("request")
        if obj.proof and request:
            return request.build_absolute_uri(obj.proof.url)
        return obj.proof.url if obj.proof else ""


class AdminRechargeOrderSerializer(RechargeOrderSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(RechargeOrderSerializer.Meta):
        fields = RechargeOrderSerializer.Meta.fields + ["user", "user_email"]
        read_only_fields = fields
