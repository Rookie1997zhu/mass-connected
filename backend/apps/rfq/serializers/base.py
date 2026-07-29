from rest_framework import serializers

from apps.rfq.models import ServiceCategory
from core.document_preview import CONVERT_TO_PDF_EXTS

PREVIEWABLE_EXTS = {
    "xlsx",
    "xls",
    "csv",
    "docx",
    "doc",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "pdf",
}
TRANSLATABLE_EXTS = {"pdf", *CONVERT_TO_PDF_EXTS, "docx", "doc", "xlsx", "xls", "csv"}
MAX_QUOTE_ATTACHMENTS = 10


def apply_markup(amount, markup_percent):
    if not amount:
        return amount
    return int(round(amount * (100 + (markup_percent or 0)) / 100))


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = [
            "id",
            "parent",
            "name",
            "slug",
            "icon",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
