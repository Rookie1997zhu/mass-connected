from rest_framework import serializers

from apps.accounts.models import FactoryProfile, SupplierAttachment, SupplierTag, User

PREVIEWABLE_EXTS = {"xlsx", "xls", "csv", "jpg", "jpeg", "png", "gif", "webp", "pdf"}
PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES = {
    "company_profile",
    "certification",
    "equipment",
    "case",
}


class FactoryProfileSummarySerializer(serializers.ModelSerializer):
    business_license_url = serializers.SerializerMethodField()

    class Meta:
        model = FactoryProfile
        fields = [
            "id",
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
            "status",
            "business_license_url",
        ]
        read_only_fields = fields

    def get_business_license_url(self, obj):
        if not obj.business_license:
            return ""
        from core.media_urls import api_absolute_uri

        return api_absolute_uri(
            self.context.get("request"),
            "/api/factory/profile/license/download",
        )


class SupplierTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierTag
        fields = ["id", "tag_name"]
        read_only_fields = ["id"]


class SupplierAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()

    class Meta:
        model = SupplierAttachment
        fields = [
            "id",
            "file_name",
            "category",
            "is_public",
            "file_url",
            "file_ext",
            "is_previewable",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_file_ext(self, obj):
        name = obj.file_name or ""
        if "." not in name:
            return ""
        return name.rsplit(".", 1)[-1].lower()

    def get_is_previewable(self, obj):
        return self.get_file_ext(obj) in PREVIEWABLE_EXTS

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        role = getattr(request.user, "role", "")
        if role in {"super_admin", "operator", "sales"} or getattr(request.user, "is_staff", False):
            path = f"/api/admin/suppliers/{obj.profile_id}/attachments/{obj.id}/download"
        else:
            path = f"/api/supplier/profile/attachments/{obj.id}/download"
        return request.build_absolute_uri(path)


class UserSerializer(serializers.ModelSerializer):
    factory_profile = FactoryProfileSummarySerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "phone",
            "role",
            "member_type",
            "factory_profile",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "role", "member_type", "created_at"]
