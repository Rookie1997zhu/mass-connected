from rest_framework import serializers

from apps.subscription.models import (
    FeatureEntitlement,
    PlanVersion,
    Subscription,
    SubscriptionOrder,
    UsageLedger,
)


class PlanVersionSerializer(serializers.ModelSerializer):
    is_orderable = serializers.BooleanField(read_only=True)

    class Meta:
        model = PlanVersion
        fields = [
            "id",
            "code",
            "name",
            "status",
            "billing_period",
            "price_amount",
            "currency",
            "features_json",
            "description",
            "published_at",
            "is_orderable",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "published_at", "created_at", "updated_at", "is_orderable"]


class FeatureEntitlementSerializer(serializers.ModelSerializer):
    remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = FeatureEntitlement
        fields = [
            "id",
            "feature_code",
            "period_limit",
            "period_used",
            "period_reserved",
            "remaining",
            "period_reset_at",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanVersionSerializer(source="plan_version", read_only=True)
    entitlements = FeatureEntitlementSerializer(many=True, read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "user_id",
            "user_email",
            "status",
            "source",
            "starts_at",
            "ends_at",
            "note",
            "plan",
            "entitlements",
            "created_at",
        ]


class UsageLedgerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UsageLedger
        fields = [
            "id",
            "ledger_no",
            "user_id",
            "user_email",
            "feature_code",
            "action",
            "quantity",
            "status",
            "idempotency_key",
            "source_type",
            "source_id",
            "created_at",
        ]


class SubscriptionOrderSerializer(serializers.ModelSerializer):
    plan = PlanVersionSerializer(source="plan_version", read_only=True)
    proof_url = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SubscriptionOrder
        fields = [
            "id",
            "order_no",
            "status",
            "price_amount",
            "currency",
            "proof_url",
            "note",
            "plan",
            "user_email",
            "subscription_id",
            "confirmed_at",
            "created_at",
        ]

    def get_proof_url(self, obj):
        if not obj.proof:
            return ""
        request = self.context.get("request")
        url = obj.proof.url
        if request:
            return request.build_absolute_uri(url)
        return url
