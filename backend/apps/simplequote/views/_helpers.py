import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile

from apps.simplequote.calculator import build_param_map
from apps.simplequote.models import QuoteParam, QuoteTable
from core.pdf import (
    build_injection_quotation_pdf,
    build_paper_box_quotation_pdf,
    build_pcba_quotation_pdf,
    build_pcb_dev_quotation_pdf,
    build_quotation_pdf,
)


def _save_parse_upload(upload, suffix: str) -> str:
    """Persist upload under MEDIA_ROOT/tmp/parse/ for Celery worker access."""
    parse_dir = Path(settings.MEDIA_ROOT) / "tmp" / "parse"
    parse_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, dir=str(parse_dir))
    try:
        with os.fdopen(fd, "wb") as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise
    return tmp_path


TYPE_LABELS = {
    "injection": "注塑模具报价书",
    "print3d": "3D 打印报价书",
    "pcba": "PCBA 加工费报价书",
    "pcb": "PCB 开发报价书",
    "software": "软件开发报价书",
    "ic": "IC 方案报价书",
    "paper_box": "纸盒包装报价书",
}


def param_overrides(quote_type):
    overrides = {}
    for param in QuoteParam.objects.filter(quote_type=quote_type, is_active=True):
        overrides[param.param_key] = param.value
    return overrides


def table_overrides(quote_type):
    tables = {}
    for table in QuoteTable.objects.filter(quote_type=quote_type, is_active=True):
        tables[table.table_key] = table.rows or []
    return tables


def merged_pcb_params():
    """PCB 开发报价合并 shipping 域的配送简化规则与汇率参数。"""
    params = param_overrides("pcb")
    for key in ("pcb_shipping_under_1kg", "pcb_shipping_per_kg", "cny_to_krw"):
        sp = QuoteParam.objects.filter(quote_type="shipping", param_key=key, is_active=True).first()
        if sp:
            params[key] = sp.value
        else:
            defaults = build_param_map("shipping", {})
            if key in defaults:
                params[key] = defaults[key]
    return params


def render_pdf(quote):
    if quote.quote_type == "injection":
        pdf_bytes = build_injection_quotation_pdf(
            quote_no=quote.quote_no,
            product_name=quote.product_name or "-",
            inputs=quote.inputs or {},
            result=quote.result or {},
            valid_until=quote.valid_until.isoformat() if quote.valid_until else "-",
            created_at=quote.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
        return

    if quote.quote_type == "pcba":
        pdf_bytes = build_pcba_quotation_pdf(
            quote_no=quote.quote_no,
            product_name=quote.product_name or "-",
            inputs=quote.inputs or {},
            result=quote.result or {},
            valid_until=quote.valid_until.isoformat() if quote.valid_until else "-",
            created_at=quote.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
        return

    if quote.quote_type == "pcb":
        pdf_bytes = build_pcb_dev_quotation_pdf(
            quote_no=quote.quote_no,
            product_name=quote.product_name or "-",
            inputs=quote.inputs or {},
            result=quote.result or {},
            valid_until=quote.valid_until.isoformat() if quote.valid_until else "-",
            created_at=quote.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
        return

    if quote.quote_type == "paper_box":
        pdf_bytes = build_paper_box_quotation_pdf(
            quote_no=quote.quote_no,
            product_name=quote.product_name or "-",
            inputs=quote.inputs or {},
            result=quote.result or {},
            valid_until=quote.valid_until.isoformat() if quote.valid_until else "-",
            created_at=quote.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
        return

    result = quote.result or {}
    line_items = [(item["label"], item["amount"]) for item in result.get("breakdown", [])]
    meta_rows = [
        ("产品名称", quote.product_name or "-"),
        ("报价类型", TYPE_LABELS.get(quote.quote_type, quote.quote_type)),
        ("数量", result.get("quantity", 1)),
        ("有效期", quote.valid_until.isoformat() if quote.valid_until else "-"),
        ("生成时间", quote.created_at.strftime("%Y-%m-%d %H:%M")),
    ]
    pdf_bytes = build_quotation_pdf(
        title=TYPE_LABELS.get(quote.quote_type, "报价书"),
        quote_no=quote.quote_no,
        meta_rows=meta_rows,
        line_items=line_items,
        total_label="合计 / Total",
        total_amount=quote.total_amount,
        currency=quote.currency,
    )
    quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
