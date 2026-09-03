"""AI translate + attachment preview endpoints for RFQ / Quote."""

from __future__ import annotations

from pathlib import Path

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.project.translation import TranslationError, translate_file_by_path, translate_text
from apps.rfq.models import Quote, QuoteAttachment, QuoteRequest, RFQ, RFQAttachment
from core.document_preview import (
    PreviewError,
    cleanup_preview_cache,
    file_ext,
    get_or_create_preview_pdf,
    preview_mode_for_ext,
)
from core.permissions import IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response
from core.storage_utils import local_file_path, materialize_field_file

RFQ_ATT_CACHE_NS = "rfq_att"
QUOTE_ATT_CACHE_NS = "quote_att"

_AI_TRANSLATE_THROTTLE = [ScopedRateThrottle]
_AI_TRANSLATE_SCOPE = "ai_translate"


def _text_translate_response(request):
    text = request.data.get("text", "")
    target_lang = request.data.get("target_lang", "")
    try:
        translated = translate_text(text, target_lang)
    except TranslationError as exc:
        status_code = 503 if exc.code == "TRANSLATE_NOT_CONFIGURED" else 400
        if exc.code == "TRANSLATE_FAILED":
            status_code = 502
        return error_response(exc.code, exc.message, status=status_code, request=request)
    return success_response({"translated_text": translated}, request=request)


def _file_translate_response(request, cache_ns, file_id, source_path, name):
    target_lang = request.data.get("target_lang", "")
    ext = file_ext(name)
    try:
        result = translate_file_by_path(cache_ns, file_id, source_path, ext, target_lang)
    except PreviewError as exc:
        return error_response(
            exc.code, exc.message, status=status.HTTP_400_BAD_REQUEST, request=request
        )
    except TranslationError as exc:
        status_code = 503 if exc.code == "TRANSLATE_NOT_CONFIGURED" else 400
        if exc.code == "TRANSLATE_FAILED":
            status_code = 502
        if exc.code == "PREVIEW_EXTRACT_EMPTY":
            status_code = 400
        return error_response(exc.code, exc.message, status=status_code, request=request)

    return success_response(
        {
            "translated_text": result.get("translated_text", ""),
            "source_text": result.get("source_text", ""),
            "truncated": result.get("truncated", False),
            "extraction_method": result.get("extraction_method", ""),
            "page_count": result.get("page_count", 0),
            "processed_pages": result.get("processed_pages", 0),
            "char_count": result.get("char_count", 0),
        },
        request=request,
    )


def _preview_pdf_response(request, source_path, file_id, name, cache_ns):
    if not source_path:
        return error_response("PROJECT_FILE_MISSING", "文件不存在", request=request)
    ext = file_ext(name)
    mode = preview_mode_for_ext(ext)
    if mode not in {"direct", "pdf_convert"}:
        return error_response(
            "PREVIEW_PDF_NOT_APPLICABLE",
            "该文件类型不支持 PDF 预览",
            status=status.HTTP_400_BAD_REQUEST,
            request=request,
        )
    try:
        pdf_path = get_or_create_preview_pdf(source_path, file_id, ext, cache_ns=cache_ns)
    except PreviewError as exc:
        code_status = (
            status.HTTP_502_BAD_GATEWAY
            if exc.code in {"PREVIEW_CONVERT_FAILED", "PREVIEW_CONVERT_TIMEOUT", "PREVIEW_CONVERT_UNAVAILABLE"}
            else status.HTTP_400_BAD_REQUEST
        )
        return error_response(exc.code, exc.message, status=code_status, request=request)

    response = FileResponse(
        pdf_path.open("rb"),
        content_type="application/pdf",
        as_attachment=False,
        filename=f"{Path(name or 'preview').stem}.pdf",
    )
    response["Content-Disposition"] = 'inline; filename="preview.pdf"'
    return response


def _member_visible_quote(request, quote_id):
    return get_object_or_404(
        Quote.objects.select_related("rfq"),
        pk=quote_id,
        rfq__buyer=request.user,
        is_customer_visible=True,
    )


# ----- Text translate -----


class MemberRfqTranslateView(APIView):
    permission_classes = [IsBuyerRole]
    throttle_classes = _AI_TRANSLATE_THROTTLE
    throttle_scope = _AI_TRANSLATE_SCOPE

    def post(self, request, pk):
        get_object_or_404(RFQ, pk=pk, buyer=request.user)
        return _text_translate_response(request)


class SupplierQuoteRequestTranslateView(APIView):
    permission_classes = [IsSupplierRole]
    throttle_classes = _AI_TRANSLATE_THROTTLE
    throttle_scope = _AI_TRANSLATE_SCOPE

    def post(self, request, pk):
        get_object_or_404(QuoteRequest, pk=pk, supplier=request.user)
        return _text_translate_response(request)


class MemberQuoteTranslateView(APIView):
    permission_classes = [IsBuyerRole]
    throttle_classes = _AI_TRANSLATE_THROTTLE
    throttle_scope = _AI_TRANSLATE_SCOPE

    def post(self, request, quote_id):
        _member_visible_quote(request, quote_id)
        return _text_translate_response(request)


class SupplierQuoteTranslateView(APIView):
    permission_classes = [IsSupplierRole]
    throttle_classes = _AI_TRANSLATE_THROTTLE
    throttle_scope = _AI_TRANSLATE_SCOPE

    def post(self, request, quote_id):
        get_object_or_404(Quote, pk=quote_id, supplier=request.user)
        return _text_translate_response(request)


# ----- RFQ attachment -----


class MemberRfqAttachmentDownloadView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk, file_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        att = get_object_or_404(RFQAttachment, pk=file_id, rfq=rfq)
        if not att.file:
            return error_response("RFQ_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


class MemberRfqAttachmentPreviewPdfView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk, file_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        att = get_object_or_404(RFQAttachment, pk=file_id, rfq=rfq)
        if not att.file:
            return error_response("RFQ_ATTACHMENT_MISSING", "文件不存在", request=request)
        source_path = materialize_field_file(att.file)
        return _preview_pdf_response(
            request, source_path, att.id, att.file_name, RFQ_ATT_CACHE_NS
        )


class MemberRfqAttachmentTranslateView(APIView):
    permission_classes = [IsBuyerRole]
    throttle_classes = _AI_TRANSLATE_THROTTLE
    throttle_scope = _AI_TRANSLATE_SCOPE

    def post(self, request, pk, file_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        att = get_object_or_404(RFQAttachment, pk=file_id, rfq=rfq)
        if not att.file:
            return error_response("RFQ_ATTACHMENT_MISSING", "文件不存在", request=request)
        with local_file_path(att.file) as source_path:
            return _file_translate_response(
                request, RFQ_ATT_CACHE_NS, att.id, source_path, att.file_name
            )


class SupplierRfqAttachmentDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk, file_id):
        """pk = quote_request id; RFQ must be assigned to this supplier."""
        qr = get_object_or_404(
            QuoteRequest.objects.select_related("rfq"),
            pk=pk,
            supplier=request.user,
        )
        att = get_object_or_404(RFQAttachment, pk=file_id, rfq=qr.rfq)
        if not att.file:
            return error_response("RFQ_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


class SupplierRfqAttachmentPreviewPdfView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk, file_id):
        qr = get_object_or_404(
            QuoteRequest.objects.select_related("rfq"),
            pk=pk,
            supplier=request.user,
        )
        att = get_object_or_404(RFQAttachment, pk=file_id, rfq=qr.rfq)
        if not att.file:
            return error_response("RFQ_ATTACHMENT_MISSING", "文件不存在", request=request)
        source_path = materialize_field_file(att.file)
        return _preview_pdf_response(
            request, source_path, att.id, att.file_name, RFQ_ATT_CACHE_NS
        )


class SupplierRfqAttachmentTranslateView(APIView):
    permission_classes = [IsSupplierRole]
    throttle_classes = _AI_TRANSLATE_THROTTLE
    throttle_scope = _AI_TRANSLATE_SCOPE

    def post(self, request, pk, file_id):
        qr = get_object_or_404(
            QuoteRequest.objects.select_related("rfq"),
            pk=pk,
            supplier=request.user,
        )
        att = get_object_or_404(RFQAttachment, pk=file_id, rfq=qr.rfq)
        if not att.file:
            return error_response("RFQ_ATTACHMENT_MISSING", "文件不存在", request=request)
        with local_file_path(att.file) as source_path:
            return _file_translate_response(
                request, RFQ_ATT_CACHE_NS, att.id, source_path, att.file_name
            )


# ----- Quote attachment -----


class MemberQuoteAttachmentPreviewPdfView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, quote_id, file_id):
        quote = _member_visible_quote(request, quote_id)
        att = get_object_or_404(QuoteAttachment, pk=file_id, quote=quote)
        if not att.file:
            return error_response("QUOTE_ATTACHMENT_MISSING", "文件不存在", request=request)
        source_path = materialize_field_file(att.file)
        return _preview_pdf_response(
            request, source_path, att.id, att.file_name, QUOTE_ATT_CACHE_NS
        )


class MemberQuoteAttachmentTranslateView(APIView):
    permission_classes = [IsBuyerRole]
    throttle_classes = _AI_TRANSLATE_THROTTLE
    throttle_scope = _AI_TRANSLATE_SCOPE

    def post(self, request, quote_id, file_id):
        quote = _member_visible_quote(request, quote_id)
        att = get_object_or_404(QuoteAttachment, pk=file_id, quote=quote)
        if not att.file:
            return error_response("QUOTE_ATTACHMENT_MISSING", "文件不存在", request=request)
        with local_file_path(att.file) as source_path:
            return _file_translate_response(
                request, QUOTE_ATT_CACHE_NS, att.id, source_path, att.file_name
            )


class SupplierQuoteAttachmentPreviewPdfView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, quote_id, file_id):
        quote = get_object_or_404(Quote, pk=quote_id, supplier=request.user)
        att = get_object_or_404(QuoteAttachment, pk=file_id, quote=quote)
        if not att.file:
            return error_response("QUOTE_ATTACHMENT_MISSING", "文件不存在", request=request)
        source_path = materialize_field_file(att.file)
        return _preview_pdf_response(
            request, source_path, att.id, att.file_name, QUOTE_ATT_CACHE_NS
        )


class SupplierQuoteAttachmentTranslateView(APIView):
    permission_classes = [IsSupplierRole]
    throttle_classes = _AI_TRANSLATE_THROTTLE
    throttle_scope = _AI_TRANSLATE_SCOPE

    def post(self, request, quote_id, file_id):
        quote = get_object_or_404(Quote, pk=quote_id, supplier=request.user)
        att = get_object_or_404(QuoteAttachment, pk=file_id, quote=quote)
        if not att.file:
            return error_response("QUOTE_ATTACHMENT_MISSING", "文件不存在", request=request)
        with local_file_path(att.file) as source_path:
            return _file_translate_response(
                request, QUOTE_ATT_CACHE_NS, att.id, source_path, att.file_name
            )


def cleanup_rfq_attachment_cache(file_id: int) -> None:
    cleanup_preview_cache(file_id, cache_ns=RFQ_ATT_CACHE_NS)


def cleanup_quote_attachment_cache(file_id: int) -> None:
    cleanup_preview_cache(file_id, cache_ns=QUOTE_ATT_CACHE_NS)
