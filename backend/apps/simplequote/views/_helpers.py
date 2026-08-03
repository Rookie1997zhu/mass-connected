import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile

from apps.simplequote.calculator import build_param_map
from apps.simplequote.models import QuoteParam, QuoteTable
from core.fx_rate import FALLBACK_CNY_TO_KRW, get_cny_krw_rate
from core.pdf import (
    build_injection_quotation_pdf,
    build_paper_box_quotation_pdf,
    build_pcba_quotation_pdf,
    build_pcb_dev_quotation_pdf,
    build_quotation_pdf,
)


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _dual_from_amount(amount: float, currency: str, rate: float) -> tuple[float, float]:
    """按源币种与 CNY→KRW 汇率生成 (amount_cny, amount_krw)。"""
    if rate <= 0:
        rate = FALLBACK_CNY_TO_KRW
    if (currency or "KRW").upper() == "CNY":
        return round(amount, 2), round(amount * rate)
    return round(amount / rate, 2), round(amount)


def _attach_line_dual(item: dict, currency: str, rate: float) -> None:
    if not isinstance(item, dict):
        return
    amount = item.get("amount")
    if amount is None:
        return
    amount_cny, amount_krw = _dual_from_amount(_to_float(amount), currency, rate)
    item["amount_cny"] = amount_cny
    item["amount_krw"] = amount_krw
    if item.get("amount_min") is not None:
        min_cny, min_krw = _dual_from_amount(_to_float(item["amount_min"]), currency, rate)
        item["amount_cny_min"] = min_cny
        item["amount_krw_min"] = min_krw
    if item.get("amount_max") is not None:
        max_cny, max_krw = _dual_from_amount(_to_float(item["amount_max"]), currency, rate)
        item["amount_cny_max"] = max_cny
        item["amount_krw_max"] = max_krw


def _recalc_pcb_manufacturing_fx(result: dict, rate: float) -> None:
    """用实时汇率重算 PCB 制造费 KRW，并同步合计/明细。"""
    mfg = result.get("pcb_manufacturing")
    if not isinstance(mfg, dict) or not mfg.get("enabled"):
        return

    mfg["cny_to_krw"] = rate
    old_fee = round(_to_float(result.get("pcb_manufacturing_fee")))
    old_min = round(_to_float(result.get("pcb_manufacturing_fee_min"), old_fee))
    old_max = round(_to_float(result.get("pcb_manufacturing_fee_max"), old_fee))

    def _krw_from_cny(cny):
        if cny is None or cny == "":
            return None
        return round(_to_float(cny) * rate)

    if mfg.get("customer_quote_cny") is not None:
        mfg["customer_quote_krw"] = _krw_from_cny(mfg["customer_quote_cny"])
    if mfg.get("customer_quote_cny_min") is not None:
        mfg["customer_quote_krw_min"] = _krw_from_cny(mfg["customer_quote_cny_min"])
    if mfg.get("customer_quote_cny_max") is not None:
        mfg["customer_quote_krw_max"] = _krw_from_cny(mfg["customer_quote_cny_max"])

    if mfg.get("requires_manual_review"):
        return

    new_fee = round(_to_float(mfg.get("customer_quote_krw")))
    new_min = round(_to_float(mfg.get("customer_quote_krw_min"), new_fee))
    new_max = round(_to_float(mfg.get("customer_quote_krw_max"), new_fee))
    result["pcb_manufacturing_fee"] = new_fee
    result["pcb_manufacturing_fee_min"] = new_min
    result["pcb_manufacturing_fee_max"] = new_max

    if result.get("total") is not None:
        result["total"] = round(_to_float(result["total"]) - old_fee + new_fee)
    if result.get("total_min") is not None:
        result["total_min"] = round(_to_float(result["total_min"]) - old_min + new_min)
    if result.get("total_max") is not None:
        result["total_max"] = round(_to_float(result["total_max"]) - old_max + new_max)

    for item in result.get("breakdown") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "")
        if "样板制造" in label or "sample fabrication" in label.lower():
            item["amount"] = new_fee
            item["amount_min"] = new_min
            item["amount_max"] = new_max


def attach_live_fx(result: dict, currency: str) -> dict:
    """用 get_cny_krw_rate() 覆盖结果中的展示汇率与双币合计/明细。

    不改 QuoteParam；覆盖计算器写入的静态 rmb_to_krw / total_krw。
    """
    if not isinstance(result, dict):
        return result

    fx = get_cny_krw_rate()
    rate = _to_float(fx.get("cny_to_krw"), 0)
    if rate <= 0:
        rate = FALLBACK_CNY_TO_KRW

    currency = (currency or result.get("currency") or "KRW").upper()
    _recalc_pcb_manufacturing_fx(result, rate)

    total = _to_float(result.get("total"), 0)
    total_cny, total_krw = _dual_from_amount(total, currency, rate)

    result["rmb_to_krw"] = rate
    result["cny_to_krw"] = rate
    result["fx_as_of"] = fx.get("as_of")
    result["fx_source"] = fx.get("source")
    result["fx_stale"] = bool(fx.get("stale"))
    result["total_cny"] = total_cny
    result["total_krw"] = total_krw

    if result.get("total_min") is not None:
        min_cny, min_krw = _dual_from_amount(_to_float(result["total_min"]), currency, rate)
        result["total_cny_min"] = min_cny
        result["total_krw_min"] = min_krw
    if result.get("total_max") is not None:
        max_cny, max_krw = _dual_from_amount(_to_float(result["total_max"]), currency, rate)
        result["total_cny_max"] = max_cny
        result["total_krw_max"] = max_krw

    for key in ("breakdown", "items"):
        lines = result.get(key)
        if isinstance(lines, list):
            for item in lines:
                _attach_line_dual(item, currency, rate)

    return result


def ensure_live_fx(result: dict, currency: str) -> dict:
    """详情读取时惰性补齐：缺 fx_as_of 则按当前汇率 attach。"""
    if not isinstance(result, dict):
        return result
    if result.get("fx_as_of"):
        return result
    return attach_live_fx(dict(result), currency)


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
        fx_rate=result.get("rmb_to_krw") or result.get("cny_to_krw"),
        total_cny=result.get("total_cny"),
        total_krw=result.get("total_krw"),
    )
    quote.pdf.save(f"{quote.quote_no}.pdf", ContentFile(pdf_bytes), save=False)
