from rest_framework import serializers

from apps.accounts.models import FactoryProfile, SupplierAttachment
from apps.accounts.serializers.base import (
    PREVIEWABLE_EXTS,
    PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES,
)


class PublicSupplierAttachmentSerializer(serializers.ModelSerializer):
    """买家可见的公开企业资料附件（不含敏感字段）。"""

    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()

    class Meta:
        model = SupplierAttachment
        fields = [
            "id",
            "file_name",
            "category",
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
        quote_id = self.context.get("quote_id")
        rfq_id = self.context.get("rfq_id")
        if not request or not obj.pk or not quote_id or not rfq_id:
            return ""
        path = (
            f"/api/member/rfqs/{rfq_id}/quotes/{quote_id}/supplier-attachments/{obj.id}/download"
        )
        return request.build_absolute_uri(path)


class PublicSupplierProfileSerializer(serializers.ModelSerializer):
    """买家甄别用公开企业资料：不含联系方式与营业执照。"""

    process_names = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    public_attachments = serializers.SerializerMethodField()

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
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "score",
            "process_names",
            "tags",
            "public_attachments",
        ]
        read_only_fields = fields

    def get_process_names(self, obj):
        lang = self.context.get("lang", "ko")
        from apps.i18n.fields import resolve_i18n

        return [resolve_i18n(p.name, lang) for p in obj.processes.filter(is_active=True)]

    def get_tags(self, obj):
        return [t.tag_name for t in obj.tags.all()]

    def get_public_attachments(self, obj):
        qs = obj.attachments.filter(
            is_public=True, category__in=PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES
        )
        return PublicSupplierAttachmentSerializer(qs, many=True, context=self.context).data


class PublicPartnerSerializer(serializers.ModelSerializer):
    process_names = serializers.SerializerMethodField()

    class Meta:
        model = FactoryProfile
        fields = ["id", "company_name", "region", "intro", "process_names", "created_at"]

    def get_process_names(self, obj):
        lang = self.context.get("lang", "ko")
        from apps.i18n.fields import resolve_i18n

        return [
            resolve_i18n(p.name, lang)
            for p in obj.processes.filter(is_active=True)
        ]


class PublicWebsiteAttachmentSerializer(serializers.ModelSerializer):
    """网站匿名可见的企业附件（独立公开下载 URL）。"""

    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()

    class Meta:
        model = SupplierAttachment
        fields = [
            "id",
            "file_name",
            "category",
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
        path = f"/api/public/partner-attachments/{obj.id}/download"
        return request.build_absolute_uri(path)


class PublicWebsitePartnerDetailSerializer(serializers.ModelSerializer):
    """网站企业能力页：白名单字段，不含电话/执照/内部备注。"""

    process_names = serializers.SerializerMethodField()
    process_ids = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    public_attachments = serializers.SerializerMethodField()

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
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "score",
            "process_names",
            "process_ids",
            "tags",
            "public_attachments",
        ]
        read_only_fields = fields

    def get_process_names(self, obj):
        lang = self.context.get("lang", "ko")
        from apps.i18n.fields import resolve_i18n

        return [resolve_i18n(p.name, lang) for p in obj.processes.filter(is_active=True)]

    def get_process_ids(self, obj):
        return list(obj.processes.filter(is_active=True).values_list("id", flat=True))

    def get_tags(self, obj):
        return [t.tag_name for t in obj.tags.all()]

    def get_public_attachments(self, obj):
        qs = obj.attachments.filter(
            is_public=True, category__in=PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES
        )
        return PublicWebsiteAttachmentSerializer(qs, many=True, context=self.context).data
