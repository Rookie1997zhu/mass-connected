from rest_framework import serializers

from apps.points.models import PointRule, PointTransaction, PointWallet, RechargeOrder
from core.media_urls import api_absolute_uri


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
        if not obj.proof:
            return ""
        return api_absolute_uri(
            self.context.get("request"),
            f"/api/member/points/recharges/{obj.id}/proof/download",
        )


class AdminRechargeOrderSerializer(RechargeOrderSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(RechargeOrderSerializer.Meta):
        fields = RechargeOrderSerializer.Meta.fields + ["user", "user_email"]
        read_only_fields = fields

    def get_proof_url(self, obj):
        if not obj.proof:
            return ""
        return api_absolute_uri(
            self.context.get("request"),
            f"/api/admin/points/recharges/{obj.id}/proof/download",
        )
