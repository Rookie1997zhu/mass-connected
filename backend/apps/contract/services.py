from django.core.files.base import ContentFile

from apps.contract.models import Contract
from core.pdf import build_quotation_pdf


def render_contract_pdf(contract):
    meta_rows = [
        ("合同标题", contract.title),
        ("买方", contract.buyer.name or contract.buyer.email),
        ("金额", f"{contract.amount:,} {contract.currency}"),
        ("生成时间", contract.created_at.strftime("%Y-%m-%d %H:%M") if contract.created_at else "-"),
    ]
    line_items = [("合同金额 / Contract Amount", contract.amount)]
    pdf_bytes = build_quotation_pdf(
        title="生产合同 / Contract",
        quote_no=contract.contract_no,
        meta_rows=meta_rows,
        line_items=line_items,
        total_label="合计 / Total",
        total_amount=contract.amount,
        currency=contract.currency,
        notes=[
            contract.terms or "双方按平台确认的报价内容履约。",
            "付款方式与交付条款以平台线下确认为准。",
            "本合同由 MASS CONNECTED 平台生成。",
        ],
    )
    contract.pdf.save(f"{contract.contract_no}.pdf", ContentFile(pdf_bytes), save=False)


def create_contract_for_order(production_order, quote):
    """详细报价确认后为生产订单生成合同。"""
    existing = Contract.objects.filter(production_order=production_order).first()
    if existing:
        return existing
    rfq = production_order.rfq
    contract = Contract(
        contract_no=Contract.generate_no(),
        rfq=rfq,
        quote=quote,
        production_order=production_order,
        buyer=production_order.buyer,
        supplier=production_order.supplier,
        title=f"生产合同 {rfq.rfq_no}",
        amount=production_order.price_amount,
        currency=production_order.currency,
        status="pending_sign",
    )
    render_contract_pdf(contract)
    contract.save()
    return contract
