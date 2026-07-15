"""付款确认：管理员与关联卖家共用同一事务流程。"""

from django.db import transaction
from django.utils import timezone

from apps.notification.services import notify
from apps.payment.models import Payment
from apps.project.services import create_project_from_production_order


class PaymentConfirmError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


@transaction.atomic
def confirm_payment(payment_id, *, actor, require_proof=False):
    """
    确认付款：置 confirmed → 合同 signed → 幂等创建项目 → 通知买卖双方。
    并发时用行锁；项目创建依赖 production_order 一对一幂等。
    """
    payment = (
        Payment.objects.select_for_update()
        .select_related(
            "contract",
            "contract__production_order",
            "contract__supplier",
            "buyer",
        )
        .filter(pk=payment_id)
        .first()
    )
    if not payment:
        raise PaymentConfirmError("PAYMENT_NOT_FOUND", "付款单不存在")

    if payment.status == "confirmed":
        project = None
        contract = payment.contract
        if contract and contract.production_order_id:
            project = getattr(contract.production_order, "project", None)
        return payment, project, True

    if payment.status == "cancelled":
        raise PaymentConfirmError("PAYMENT_CANCELLED", "该付款已取消")

    if require_proof and (payment.status != "pending_confirm" or not payment.proof):
        raise PaymentConfirmError(
            "PAYMENT_PROOF_REQUIRED",
            "请等待买家上传付款凭证后再确认",
        )

    payment.status = "confirmed"
    payment.confirmed_by = actor
    payment.confirmed_at = timezone.now()
    payment.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])

    contract = payment.contract
    project = None
    if contract:
        if contract.status != "signed":
            contract.status = "signed"
            contract.signed_at = timezone.now()
            contract.save(update_fields=["status", "signed_at", "updated_at"])
        if contract.production_order_id:
            project = create_project_from_production_order(contract.production_order)

    notify(
        payment.buyer,
        "payment",
        "付款已确认",
        f"付款单 {payment.payment_no} 已确认，项目将进入生产阶段。",
        send_email=True,
    )
    if contract and contract.supplier_id:
        notify(
            contract.supplier,
            "payment",
            "客户付款已确认",
            f"付款单 {payment.payment_no} 已确认，合同 {contract.contract_no} 进入履约阶段。",
            related_type="payment",
            related_id=payment.id,
            send_email=True,
        )

    return payment, project, False
