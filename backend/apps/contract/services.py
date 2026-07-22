from django.core.files.base import ContentFile
from django.utils import timezone

from apps.contract.models import Contract, ContractTemplate
from core.pdf import build_nda_pdf

DEFAULT_CONTRACT_BODY = """本保密协议（以下简称「本协议」）由 {{company_name}} 与 커넥티드（CONNECTED） 共同签订。

协议编号：{{contract_no}}
询价编号：{{rfq_no}}
生产订单：{{order_no}}
签署日期：{{date}}

第 1 条（目的）
本协议旨在规定双方在产品开发、设计及量产下单相关工作中，使用一方或客户提供的资料与信息时，应遵守的保密义务。

第 2 条（保密信息）
1. 本协议所称保密信息，指平台（MASS CONNECTED 网站）内客户填写的资料、电子邮件资料、咨询过程中形成的图纸及会议内容、会议纪要等一切协商记录，以及客户的产品、商品化计划、价格政策、合同条件、营业方法、营销计划与策略、研发活动、生产计划、开发技术或计划、技术流程、设计、发明及研究计划、营业诀窍、商业秘密、客户信息、特定软件、算法、用户手册、系统相关文档等信息中，符合以下任一项者：
1) 客户在平台填写的内容
2) 以书面提供时，明确标注为保密信息的资料
3) 以口头提供时，口头告知为「保密资料」，并在 7 日内向对方发送确认其为保密信息的书面文件
4) 虽为书面或电子信息且无保密标识，但依其性质应被合理认定为保密的信息（如专利资料等公众认为较为特殊的信息）

2. 不属于保密信息的情形：
1) 该技术等已公开，且属于一般性信息
2) 在公开前 CONNECTED 已知晓，或未使用保密信息而由 CONNECTED 独立开发或生成的信息
3) 有公开权限的第三方向 CONNECTED 公开的信息
4) CONNECTED 从未违反保密义务而从其他来源取得的信息
5) 客户虽指定为保密资料，但 CONNECTED 已通过多种方式告知其并非保密资料的信息

第 3 条（保密义务）
1. CONNECTED 未经提供保密信息的客户事先书面同意，不得将收到的保密信息用于本协议目的以外，亦不得向第三方提供、泄露或外流。
但依法负有向第三方提供保密信息的义务，或依行政机关、法院等合法程序被要求提供时，可事先通知客户，并在必要最小范围内向相关机关或第三方提供。
2. CONNECTED 仅可在实现第 1 条目的所需范围内，向相关职员披露保密信息；此时 CONNECTED 应使该等职员同样遵守前述义务。
3. 为法律、会计、咨询等正当目的，可向承担保密义务的专业人士或合作企业披露。

第 4 条（资料返还与销毁）
1. 合同期结束后，若客户要求，CONNECTED 应立即将其持有的保密信息原件、复制件及试验件等，依提供方选择返还客户或销毁。
但若发生法律纠纷或争议（如未付款），或可能产生误解，可不销毁；此时电子形式的保密信息仍应在保管 1 年后以不可恢复方式删除。
2. 若客户违反本协议保密义务，即使合同期尚未结束，亦适用前款。

第 5 条（保密义务存续）
1. CONNECTED 所负义务在本协议终止或双方业务关系结束后仍存续 1 年。（电子信息保管 1 年）
2. 若某项保密信息在期满前已不再属于秘密且已公开，接收方可免除本协议义务；但该公开不得因接收方或其职员的故意或过失违反本协议而发生。

第 6 条（损害赔偿等）
违反本协议规定并给对方造成损失的，违约方应赔偿对方损失。

第 7 条（知识产权）
1. 提供给 CONNECTED 的一切信息均归客户所有；保密信息的提供行为不得解释为向 CONNECTED 授予或转让权利，或构成任何确定性合同、实施权等。
2. CONNECTED 不得侵犯客户或第三方的知识产权等权利，亦不得违反相关法律；未经客户事先书面同意，不得向第三方提供或使用客户知识产权相关信息。
3. 仅就客户提供的资料而言；CONNECTED 向客户提供的通用产品功能、效果等，若客户未另行请求知识产权保护，则不视为知识产权。

第 8 条（合同期间）
本协议自签订日起 1 年有效。

第 9 条（一般事项）
1. 本协议的解释与适用依大韩民国法律。
2. 与本协议相关的争议或问题，以客户所在地管辖地方法院为一审专属合意管辖法院。

—— 签署栏 ——
客户：{{company_name}}
事业者登记号：{{business_reg_no}}
客户地址：{{company_address}}
客户姓名：{{signer_name}}

供方：커넥티드（CONNECTED）
事业者登记号：652-18-02371
地址：首尔特别市 衿川区 数码路10街 37，16层 1607号（加山洞，Ask Tower）
代表：홍승범
"""

NDA_TEMPLATE_VERSION = "nda-v1"


def ensure_default_contract_template():
    """确保激活的合同模板为保密协议全文；旧生产合同模板停用。"""
    template = ContractTemplate.objects.filter(version=NDA_TEMPLATE_VERSION).first()
    if template:
        if not template.is_active or template.body != DEFAULT_CONTRACT_BODY:
            template.title = "保密协议"
            template.body = DEFAULT_CONTRACT_BODY
            template.is_active = True
            template.effective_date = timezone.now().date()
            template.save(
                update_fields=["title", "body", "is_active", "effective_date", "updated_at"]
            )
        ContractTemplate.objects.exclude(pk=template.pk).filter(is_active=True).update(
            is_active=False
        )
        return template

    ContractTemplate.objects.filter(is_active=True).update(is_active=False)
    return ContractTemplate.objects.create(
        version=NDA_TEMPLATE_VERSION,
        title="保密协议",
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


def _buyer_company_name(user):
    if not user:
        return ""
    profile = getattr(user, "factory_profile", None)
    if profile and profile.company_name:
        return profile.company_name
    return ""


def render_template_body(template_body, context):
    text = template_body or DEFAULT_CONTRACT_BODY
    for key, value in context.items():
        text = text.replace(f"{{{{{key}}}}}", str(value if value is not None else ""))
    return text


def build_contract_context(contract, *, overrides=None):
    overrides = overrides or {}
    rfq = contract.rfq
    production_order = contract.production_order
    return {
        "contract_no": contract.contract_no,
        "rfq_no": rfq.rfq_no if rfq else "",
        "order_no": production_order.order_no if production_order else "",
        "buyer_name": contract.buyer.name or contract.buyer.email if contract.buyer_id else "",
        "supplier_name": _supplier_display_name(contract.supplier),
        "company_name": overrides.get("company_name", contract.company_name)
        or "（客户公司名称）",
        "business_reg_no": overrides.get("business_reg_no", contract.business_reg_no)
        or "（事业者登记号）",
        "company_address": overrides.get("company_address", contract.company_address)
        or "（客户地址）",
        "signer_name": overrides.get("signer_name", contract.signer_name) or "（客户姓名）",
        "amount": f"{contract.amount:,}",
        "currency": contract.currency,
        "lead_time_days": getattr(production_order, "lead_time_days", "") or "",
        "payment_terms": "",
        "date": (
            contract.signed_at.strftime("%Y-%m-%d")
            if contract.signed_at
            else timezone.now().strftime("%Y-%m-%d")
        ),
    }


def render_contract_pdf(contract, *, signature_path=None):
    """生成含落款信息的保密协议 PDF；签署后可附带签名图。"""
    body = contract.rendered_body
    if not body:
        template_body = contract.template.body if contract.template_id else DEFAULT_CONTRACT_BODY
        body = render_template_body(template_body, build_contract_context(contract))
    signed_at = (
        contract.signed_at.strftime("%Y-%m-%d %H:%M")
        if contract.signed_at
        else timezone.now().strftime("%Y-%m-%d %H:%M")
    )
    pdf_bytes = build_nda_pdf(
        title=contract.title or "保密协议",
        version=contract.template_version or NDA_TEMPLATE_VERSION,
        company_name=contract.company_name or "（客户公司名称）",
        body=body,
        signed_at=signed_at,
        business_reg_no=contract.business_reg_no,
        company_address=contract.company_address,
        signer_name=contract.signer_name,
        signature_image_path=signature_path,
    )
    contract.pdf.save(f"{contract.contract_no}.pdf", ContentFile(pdf_bytes), save=False)


def create_contract_for_order(production_order, quote):
    """详细报价确认后为生产订单生成保密协议（金额仍写入供付款单使用）。"""
    existing = Contract.objects.filter(production_order=production_order).first()
    if existing:
        return existing

    rfq = production_order.rfq
    template = ensure_default_contract_template()
    customer_amount = production_order.display_customer_amount()
    company_name = _buyer_company_name(production_order.buyer)
    contract_no = Contract.generate_no()
    context = {
        "contract_no": contract_no,
        "rfq_no": rfq.rfq_no if rfq else "",
        "order_no": production_order.order_no,
        "buyer_name": production_order.buyer.name or production_order.buyer.email,
        "supplier_name": _supplier_display_name(production_order.supplier),
        "company_name": company_name or "（客户公司名称）",
        "business_reg_no": "（事业者登记号）",
        "company_address": "（客户地址）",
        "signer_name": "（客户姓名）",
        "amount": f"{customer_amount:,}",
        "currency": production_order.currency,
        "lead_time_days": production_order.lead_time_days,
        "payment_terms": quote.payment_terms or "按平台确认",
        "date": timezone.now().strftime("%Y-%m-%d"),
    }
    rendered = render_template_body(template.body, context)
    contract = Contract(
        contract_no=contract_no,
        rfq=rfq,
        quote=quote,
        production_order=production_order,
        template=template,
        template_version=template.version,
        rendered_body=rendered,
        buyer=production_order.buyer,
        supplier=production_order.supplier,
        title=template.title or "保密协议",
        amount=customer_amount,
        currency=production_order.currency,
        terms=rendered,
        company_name=company_name,
        status="pending_sign",
    )
    # 待签署阶段不强制生成 PDF；签署后再归档含签名版本
    contract.save()
    return contract
