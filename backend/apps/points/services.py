from django.db import transaction

from apps.points.models import PointRule, PointTransaction, PointWallet
from core.exceptions import AppAPIException

DEFAULT_RULES = {
    "REGISTER_BONUS": 10000,
    "SIMPLE_QUOTE": 1000,
    "PDF_QUOTE": 1000,
}


def ensure_wallet(user):
    wallet, _ = PointWallet.objects.get_or_create(user=user)
    return wallet


def get_rule_amount(rule_code):
    rule = PointRule.objects.filter(rule_code=rule_code, enabled=True).first()
    if rule:
        return rule.point_amount
    return DEFAULT_RULES.get(rule_code, 0)


@transaction.atomic
def add_points(user, amount, ttype, source_type="", source_id=None, description="", admin=None):
    """增加积分（earn/recharge/refund/adjust 正向）。"""
    wallet = PointWallet.objects.select_for_update().get_or_create(user=user)[0]
    before = wallet.balance
    wallet.balance = before + amount
    if ttype == "recharge":
        wallet.total_recharged += amount
    if ttype in {"earn", "adjust", "refund", "recharge"} and amount > 0:
        wallet.total_earned += amount
    wallet.save()
    return PointTransaction.objects.create(
        transaction_no=PointTransaction.generate_no(),
        user=user,
        type=ttype,
        amount=amount,
        balance_before=before,
        balance_after=wallet.balance,
        source_type=source_type,
        source_id=source_id,
        description=description,
        admin=admin,
    )


@transaction.atomic
def spend_points(user, amount, source_type="", source_id=None, description="", admin=None):
    """扣减积分，余额不足抛业务异常。"""
    wallet = PointWallet.objects.select_for_update().get_or_create(user=user)[0]
    if amount <= 0:
        return None
    if wallet.balance < amount:
        raise AppAPIException(
            "积分余额不足，请充值后再使用该功能",
            code="POINT_INSUFFICIENT",
        )
    before = wallet.balance
    wallet.balance = before - amount
    wallet.total_spent += amount
    wallet.save()
    return PointTransaction.objects.create(
        transaction_no=PointTransaction.generate_no(),
        user=user,
        type="spend",
        amount=-amount,
        balance_before=before,
        balance_after=wallet.balance,
        source_type=source_type,
        source_id=source_id,
        description=description,
        admin=admin,
    )


def grant_register_bonus(user):
    amount = get_rule_amount("REGISTER_BONUS")
    if amount <= 0:
        ensure_wallet(user)
        return None
    return add_points(
        user,
        amount,
        "earn",
        source_type="register_bonus",
        description="注册奖励积分",
    )
