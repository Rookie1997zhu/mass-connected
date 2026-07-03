from rest_framework import serializers

from apps.simplequote.models import QuoteParam, SimpleQuote


class SimpleQuoteSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = SimpleQuote
        fields = [
            "id",
            "quote_no",
            "quote_type",
            "product_name",
            "inputs",
            "result",
            "total_amount",
            "currency",
            "status",
            "valid_until",
            "points_spent",
            "pdf_url",
            "converted_rfq",
            "created_at",
        ]
        read_only_fields = fields

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf and request:
            return request.build_absolute_uri(obj.pdf.url)
        return obj.pdf.url if obj.pdf else ""


class SimpleQuoteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimpleQuote
        fields = [
            "id",
            "quote_no",
            "quote_type",
            "product_name",
            "total_amount",
            "currency",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class SimpleQuoteCreateSerializer(serializers.Serializer):
    quote_type = serializers.ChoiceField(
        choices=["injection", "print3d", "pcb", "software", "ic"]
    )
    product_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    inputs = serializers.DictField(required=False, default=dict)


class QuoteParamSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteParam
        fields = [
            "id",
            "quote_type",
            "param_key",
            "label",
            "value",
            "unit",
            "note",
            "is_active",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
