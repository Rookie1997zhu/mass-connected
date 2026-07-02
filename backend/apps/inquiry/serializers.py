from rest_framework import serializers

from apps.inquiry.models import Inquiry


class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            "id",
            "name",
            "company",
            "email",
            "phone",
            "product_interest",
            "message",
            "status",
            "source",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]
