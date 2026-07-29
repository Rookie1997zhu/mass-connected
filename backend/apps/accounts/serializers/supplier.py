from rest_framework import serializers

from apps.accounts.models import FactoryProfile
from apps.accounts.serializers.base import (
    SupplierAttachmentSerializer,
    SupplierTagSerializer,
)


class FactoryProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    process_ids = serializers.PrimaryKeyRelatedField(
        source="processes", many=True, read_only=True
    )
    tags = SupplierTagSerializer(many=True, read_only=True)
    attachments = SupplierAttachmentSerializer(many=True, read_only=True)
    business_license_url = serializers.SerializerMethodField()

    class Meta:
        model = FactoryProfile
        fields = [
            "id",
            "email",
            "name",
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "contact_phone",
            "payment_terms",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "process_ids",
            "tags",
            "attachments",
            "score",
            "is_public",
            "status",
            "business_license_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "name",
            "process_ids",
            "tags",
            "attachments",
            "score",
            "status",
            "business_license_url",
            "created_at",
            "updated_at",
        ]

    def get_business_license_url(self, obj):
        if not obj.business_license:
            return ""
        from core.media_urls import api_absolute_uri

        return api_absolute_uri(
            self.context.get("request"),
            f"/api/admin/suppliers/{obj.id}/license/download",
        )


class SupplierProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactoryProfile
        fields = [
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "contact_phone",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "is_public",
        ]
