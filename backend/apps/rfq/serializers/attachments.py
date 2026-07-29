from rest_framework import serializers

from apps.rfq.models import (
    QuoteAttachment,
    QuoteRequest,
    RFQAttachment,
)
from apps.rfq.serializers.base import PREVIEWABLE_EXTS, TRANSLATABLE_EXTS
from core.document_preview import preview_mode_for_ext


class RFQAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()
    preview_mode = serializers.SerializerMethodField()
    preview_pdf_url = serializers.SerializerMethodField()
    is_translatable = serializers.SerializerMethodField()

    class Meta:
        model = RFQAttachment
        fields = [
            "id",
            "file_name",
            "file_type",
            "size",
            "url",
            "file_url",
            "file_ext",
            "is_previewable",
            "preview_mode",
            "preview_pdf_url",
            "is_translatable",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_file_ext(self, obj):
        name = obj.file_name or ""
        if "." not in name:
            return (obj.file_type or "").lower()
        return name.rsplit(".", 1)[-1].lower()

    def get_is_previewable(self, obj):
        return self.get_file_ext(obj) in PREVIEWABLE_EXTS

    def get_preview_mode(self, obj):
        return preview_mode_for_ext(self.get_file_ext(obj))

    def get_is_translatable(self, obj):
        return self.get_file_ext(obj) in TRANSLATABLE_EXTS

    def _rfq_attachment_api_base(self, obj):
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        user = request.user
        rfq = obj.rfq
        # Buyer owns the RFQ
        if rfq.buyer_id == user.id:
            return f"/api/member/rfqs/{rfq.id}/attachments/{obj.id}"
        # Supplier access goes through quote-request path
        qr_id = self.context.get("quote_request_id")
        if qr_id:
            return f"/api/supplier/quote-requests/{qr_id}/rfq-attachments/{obj.id}"
        qr = QuoteRequest.objects.filter(rfq=rfq, supplier=user).order_by("-id").first()
        if qr:
            return f"/api/supplier/quote-requests/{qr.id}/rfq-attachments/{obj.id}"
        return f"/api/member/rfqs/{rfq.id}/attachments/{obj.id}"

    def get_file_url(self, obj):
        request = self.context.get("request")
        base = self._rfq_attachment_api_base(obj)
        if not base or not request:
            return self.get_url(obj)
        return request.build_absolute_uri(f"{base}/download")

    def get_url(self, obj):
        """Backward-compatible alias; prefer authenticated file_url."""
        return self.get_file_url(obj)

    def get_preview_pdf_url(self, obj):
        ext = self.get_file_ext(obj)
        mode = preview_mode_for_ext(ext)
        if mode not in {"direct", "pdf_convert"}:
            return ""
        request = self.context.get("request")
        base = self._rfq_attachment_api_base(obj)
        if not base or not request:
            return ""
        return request.build_absolute_uri(f"{base}/preview-pdf")


class QuoteAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()
    preview_mode = serializers.SerializerMethodField()
    preview_pdf_url = serializers.SerializerMethodField()
    is_translatable = serializers.SerializerMethodField()

    class Meta:
        model = QuoteAttachment
        fields = [
            "id",
            "file_name",
            "file_type",
            "size",
            "file_url",
            "file_ext",
            "is_previewable",
            "preview_mode",
            "preview_pdf_url",
            "is_translatable",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_file_ext(self, obj):
        name = obj.file_name or ""
        if "." not in name:
            return obj.file_type or ""
        return name.rsplit(".", 1)[-1].lower()

    def get_is_previewable(self, obj):
        return self.get_file_ext(obj) in PREVIEWABLE_EXTS

    def get_preview_mode(self, obj):
        return preview_mode_for_ext(self.get_file_ext(obj))

    def get_is_translatable(self, obj):
        return self.get_file_ext(obj) in TRANSLATABLE_EXTS

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        user = request.user
        quote = obj.quote
        if quote.supplier_id == user.id:
            path = f"/api/supplier/quotes/{quote.id}/attachments/{obj.id}/download"
        else:
            path = f"/api/member/quotes/{quote.id}/attachments/{obj.id}/download"
        return request.build_absolute_uri(path)

    def get_preview_pdf_url(self, obj):
        ext = self.get_file_ext(obj)
        mode = preview_mode_for_ext(ext)
        if mode not in {"direct", "pdf_convert"}:
            return ""
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        user = request.user
        quote = obj.quote
        if quote.supplier_id == user.id:
            base = f"/api/supplier/quotes/{quote.id}/attachments/{obj.id}"
        else:
            base = f"/api/member/quotes/{quote.id}/attachments/{obj.id}"
        return request.build_absolute_uri(f"{base}/preview-pdf")
