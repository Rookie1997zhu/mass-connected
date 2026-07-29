from django.db.models import Count
from django.http import FileResponse
from django.utils import timezone

from apps.notification.services import notify
from apps.rfq.models import Quote, QuoteAttachment, QuoteRequest, RFQ
from apps.rfq.serializers import MAX_QUOTE_ATTACHMENTS
from core.file_validation import validate_upload_file
from core.responses import error_response

ALLOWED_ATTACHMENT_EXTENSIONS = {
    "pdf", "step", "stp", "igs", "iges", "dwg", "dxf", "x_t", "x_b",
    "sldprt", "stl", "3mf", "zip", "rar", "7z",
    "jpg", "jpeg", "png", "gif", "webp", "xlsx", "xls", "docx", "doc", "csv", "txt",
}
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024
OPEN_RFQ_STATUSES = {"submitted", "quoting", "quoted", "negotiating"}


def open_demand_hall_queryset():
    return (
        RFQ.objects.filter(scope="public", status__in=OPEN_RFQ_STATUSES)
        .select_related("service_category")
        .annotate(quotes_count=Count("quotes", distinct=True))
        .order_by("-created_at")
    )


def get_lang(request):
    return request.query_params.get("lang") or request.headers.get("Accept-Language", "ko")[:2]


def maybe_mark_quote_request_expired(qr):
    """读取时对超过 deadline 的 assigned/viewed 报价请求标记为 expired。"""
    today = timezone.now().date()
    if qr.deadline and qr.deadline < today and qr.status in {"assigned", "viewed"}:
        qr.status = "expired"
        qr.save(update_fields=["status", "updated_at"])
    return qr


def next_plan_label(rfq):
    """为自动开放的供应商报价分配方案标签 Plan A/B/C…"""
    used = set(
        Quote.objects.filter(rfq=rfq)
        .exclude(plan_label="")
        .values_list("plan_label", flat=True)
    )
    for letter in "ABCDEF":
        candidate = f"Plan {letter}"
        if candidate not in used and letter not in used:
            return candidate
    return ""


def publish_supplier_quote_to_buyer(quote, rfq, *, notify_buyer=True):
    """供应商报价提交后立即对买家可见，并推进 RFQ 至比价状态。"""
    was_visible = bool(quote.is_customer_visible)
    update_fields = []
    if not quote.is_customer_visible:
        quote.is_customer_visible = True
        update_fields.append("is_customer_visible")
    if not (quote.plan_label or "").strip():
        quote.plan_label = next_plan_label(rfq)
        update_fields.append("plan_label")
    if update_fields:
        quote.save(update_fields=[*update_fields, "updated_at"])

    if rfq.status in {
        "submitted",
        "pending_review",
        "assigned",
        "quoting",
        "quoted",
    }:
        rfq.status = "comparing"
        rfq.save(update_fields=["status", "updated_at"])

    if notify_buyer and not was_visible:
        notify(
            rfq.buyer,
            "quote",
            "报价方案已就绪",
            f"询价 {rfq.rfq_no} 有新的报价方案可供对比确认。",
            related_type="rfq",
            related_id=rfq.id,
            send_email=True,
        )
    return quote


def _quote_upload_files(request):
    files = list(request.FILES.getlist("attachments"))
    if not files and request.FILES.get("file"):
        files = [request.FILES.get("file")]
    return [f for f in files if f]


def _validate_quote_attachment_files(files, existing_count=0, request=None):
    if existing_count + len(files) > MAX_QUOTE_ATTACHMENTS:
        return error_response(
            "QUOTE_ATTACHMENT_LIMIT",
            f"每份报价最多上传 {MAX_QUOTE_ATTACHMENTS} 个附件",
            request=request,
        )
    for file_obj in files:
        code, msg = validate_upload_file(file_obj)
        if code:
            return error_response(code, msg, request=request)
    return None


def _save_quote_attachments(quote, files, uploader):
    created = []
    for file_obj in files:
        code, ext = validate_upload_file(file_obj)
        if code:
            continue
        att = QuoteAttachment.objects.create(
            quote=quote,
            file=file_obj,
            file_name=file_obj.name,
            file_type=ext or "",
            size=file_obj.size or 0,
            uploader=uploader,
        )
        created.append(att)
    return created


def _quote_is_locked(quote):
    return quote.status == "accepted" or quote.rfq.status == "won"


def _download_quote_attachment(attachment):
    if not attachment.file:
        return error_response("QUOTE_ATTACHMENT_MISSING", "文件不存在")
    return FileResponse(
        attachment.file.open("rb"),
        as_attachment=False,
        filename=attachment.file_name,
    )
