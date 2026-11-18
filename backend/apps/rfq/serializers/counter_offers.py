from rest_framework import serializers

from apps.rfq.models import QuoteCounterOffer


class QuoteCounterOfferSerializer(serializers.ModelSerializer):
    """买卖双方可见：仅客户侧意向字段，不含供货底价。"""

    class Meta:
        model = QuoteCounterOffer
        fields = [
            "id",
            "quote_id",
            "rfq_id",
            "quantity",
            "target_total_amount",
            "currency",
            "lead_time_days",
            "note",
            "status",
            "valid_until",
            "responded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class QuoteCounterOfferCreateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    target_total_amount = serializers.IntegerField(min_value=1)
    currency = serializers.CharField(required=False, max_length=3, default="KRW")
    lead_time_days = serializers.IntegerField(required=False, min_value=0, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")
    valid_until = serializers.DateField(required=False, allow_null=True)
