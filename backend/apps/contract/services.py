from django.core.files.base import ContentFile
from django.utils import timezone

from apps.contract.models import Contract, ContractTemplate
from core.pdf import build_quotation_pdf

DEFAULT_CONTRACT_BODY = """本合同由 MASS CONNECTED 平台根据已确认报价自动生成。

合同编号：{{contract_no}}
询价编号：{{rfq_no}}
生产订单：{{order_no}}
买方：{{buyer_name}}
供应商：{{supplier_name}}
合同金额：{{amount}} {{currency}}
交期（天）：{{lead_time_days}}
付款条件：{{payment_terms}}
签署日期：{{date}}

双方按平台确认的报价方案与本合同条款履约。
付款方式与交付条款以平台确认为准。
"""


def ensure_default_contract_template():
    template = ContractTemplate.objects.filter(is_active=True).order_by("-effective_date", "-id").first()
    if template:
        return template
    return ContractTemplate.objects.create(
        version="v1-default",
        title="生产合同",
        body=DEFAULT_CONTRACT_BODY,
        is_active=True,
        effective_date=timezone.now().date(),
    )


def _supplier_display_name(user):
    if not user:
        return "平台"
    profile = getattr(user, "factory_profile", None)
    if profile and profile.company_name:
        return profile.company_name
    return user.name or user.email


def render_template_body(template_body, context):
    text = template_body or DEFAULT_CONTRACT_BODY
    for key, value in context.items():
        text = text.replace(f"{{{{{key}}}}}", str(value if value is not None else ""))
    return text


def render_contract_pdf(contract):
    notes = []
    if contract.rendered_body:
        notes = [line.strip() for line in contract.rendered_body.splitlines() if line.strip()]
    if not notes:
        notes = [
            contract.terms or "双方按平台确认的报价内容履约。",
            "付款方式与交付条款以平台线下确认为准。",
            "本合同由 MASS CONNECTED 平台生成。",
        ]
    meta_rows = [
        ("合同标题", contract.title),
        ("买方", contract.buyer.name or contract.buyer.email),
        ("供应商", _supplier_display_name(contract.supplier)),
        ("金额", f"{contract.amount:,} {contract.currency}"),
        ("模板版本", contract.template_version or "-"),
        ("生成时间", contract.created_at.strftime("%Y-%m-%d %H:%M") if contract.created_at else "-"),
    ]
    line_items = [("合同金额 / Contract Amount", contract.amount)]
    pdf_bytes = build_quotation_pdf(
        title=contract.title or "生产合同 / Contract",
        quote_no=contract.contract_no,
        meta_rows=meta_rows,
        line_items=line_items,
        total_label="合计 / Total",
        total_amount=contract.amount,
        currency=contract.currency,
        notes=notes[:20],
    )
    contract.pdf.save(f"{contract.contract_no}.pdf", ContentFile(pdf_bytes), save=False)


def create_contract_for_order(production_order, quote):
    """详细报价确认后为生产订单生成合同（金额使用客户价）。"""
    existing = Contract.objects.filter(production_order=production_order).first()
    if existing:
        return existing

    rfq = production_order.rfq
    template = ensure_default_contract_template()
    customer_amount = production_order.display_customer_amount()
    supplier_name = _supplier_display_name(production_order.supplier)
    buyer_name = production_order.buyer.name or production_order.buyer.email
    context = {
        "contract_no": Contract.generate_no(),
        "rfq_no": rfq.rfq_no if rfq else "",
        "order_no": production_order.order_no,
        "buyer_name": buyer_name,
        "supplier_name": supplier_name,
        "amount": f"{customer_amount:,}",
        "currency": production_order.currency,
        "lead_time_days": production_order.lead_time_days,
        "payment_terms": quote.payment_terms or "按平台确认",
        "date": timezone.now().strftime("%Y-%m-%d"),
    }
    rendered = render_template_body(template.body, context)
    contract = Contract(
        contract_no=context["contract_no"],
        rfq=rfq,
        quote=quote,
        production_order=production_order,
        template=template,
        template_version=template.version,
        rendered_body=rendered,
        buyer=production_order.buyer,
        supplier=production_order.supplier,
        title=template.title or f"生产合同 {rfq.rfq_no if rfq else production_order.order_no}",
        amount=customer_amount,
        currency=production_order.currency,
        terms=rendered,
        status="pending_sign",
    )
    render_contract_pdf(contract)
    contract.save()
    return contract
