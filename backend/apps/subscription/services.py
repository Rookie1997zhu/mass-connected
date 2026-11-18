"""订阅权益判定与额度账本（预留 / 结算 / 释放）。"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.subscription.models import (
    FEATURE_SIMPLE_QUOTE,
    KNOWN_FEATURE_CODES,
    FeatureEntitlement,
    PlanVersion,
    Subscription,
    SubscriptionOrder,
    UsageLedger,
)
from core.exceptions import AppAPIException


@dataclass
class MeterDecision:
    """一次受限动作的扣费决策。"""

    mode: str  # "subscription" | "points" | "free"
    entitlement: FeatureEntitlement | None = None
    subscription: Subscription | None = None
    ledger: UsageLedger | None = None


def _period_delta(billing_period: str) -> timedelta:
    if billing_period == PlanVersion.PERIOD_YEAR:
        return timedelta(days=365)
    if billing_period == PlanVersion.PERIOD_NONE:
        return timedelta(days=36500)  # effectively open-ended
    return timedelta(days=30)


def _maybe_expire_subscription(sub: Subscription, now=None) -> Subscription:
    now = now or timezone.now()
    if sub.status == Subscription.STATUS_ACTIVE and sub.ends_at and sub.ends_at <= now:
        sub.status = Subscription.STATUS_EXPIRED
        sub.save(update_fields=["status", "updated_at"])
    return sub


def get_active_subscription(user, now=None):
    now = now or timezone.now()
    qs = (
        Subscription.objects.filter(user=user, status=Subscription.STATUS_ACTIVE)
        .select_related("plan_version")
        .order_by("-ends_at", "-id")
    )
    for sub in qs:
        _maybe_expire_subscription(sub, now=now)
        if sub.is_currently_active(now=now):
            return sub
    return None


def sync_entitlements_from_plan(subscription: Subscription) -> list[FeatureEntitlement]:
    """按方案 features_json 同步权益快照（创建/开通时调用）。"""
    features = subscription.plan_version.features_json or {}
    out = []
    for code, limit in features.items():
        try:
            limit_i = int(limit)
        except (TypeError, ValueError):
            continue
        if limit_i <= 0:
            continue
        ent, _ = FeatureEntitlement.objects.update_or_create(
            subscription=subscription,
            feature_code=str(code),
            defaults={
                "user": subscription.user,
                "period_limit": limit_i,
                "period_reset_at": subscription.ends_at,
            },
        )
        out.append(ent)
    return out


@transaction.atomic
def activate_subscription(
    *,
    user,
    plan_version: PlanVersion,
    source: str,
    granted_by=None,
    note: str = "",
    starts_at=None,
    ends_at=None,
) -> Subscription:
    now = timezone.now()
    starts_at = starts_at or now
    if ends_at is None:
        ends_at = starts_at + _period_delta(plan_version.billing_period)

    # 同一用户新开通时，将既有 active 标为 cancelled（不删历史）
    Subscription.objects.filter(user=user, status=Subscription.STATUS_ACTIVE).update(
        status=Subscription.STATUS_CANCELLED,
        updated_at=now,
    )

    sub = Subscription.objects.create(
        user=user,
        plan_version=plan_version,
        status=Subscription.STATUS_ACTIVE,
        source=source,
        starts_at=starts_at,
        ends_at=ends_at,
        granted_by=granted_by,
        note=note or "",
    )
    sync_entitlements_from_plan(sub)
    return sub


def decide_meter(user, feature_code: str, quantity: int = 1) -> MeterDecision:
    """只读判定：优先订阅额度，否则交给积分路径。"""
    if quantity <= 0:
        return MeterDecision(mode="free")
    sub = get_active_subscription(user)
    if not sub:
        return MeterDecision(mode="points")
    ent = (
        FeatureEntitlement.objects.filter(
            user=user, subscription=sub, feature_code=feature_code
        )
        .order_by("id")
        .first()
    )
    if not ent or ent.period_limit <= 0:
        return MeterDecision(mode="points", subscription=sub)
    if ent.remaining < quantity:
        return MeterDecision(mode="points", subscription=sub, entitlement=ent)
    return MeterDecision(mode="subscription", subscription=sub, entitlement=ent)


@transaction.atomic
def reserve_quota(
    user,
    feature_code: str,
    *,
    idempotency_key: str,
    quantity: int = 1,
    source_type: str = "",
    source_id=None,
) -> UsageLedger:
    if not idempotency_key:
        raise AppAPIException("缺少幂等键", code="SUBSCRIPTION_IDEMPOTENCY_REQUIRED")
    existing = UsageLedger.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    decision = decide_meter(user, feature_code, quantity=quantity)
    if decision.mode != "subscription" or not decision.entitlement:
        raise AppAPIException("当前无可用订阅额度", code="SUBSCRIPTION_QUOTA_EXCEEDED")

    ent = FeatureEntitlement.objects.select_for_update().get(pk=decision.entitlement.pk)
    if ent.remaining < quantity:
        raise AppAPIException("订阅额度不足", code="SUBSCRIPTION_QUOTA_EXCEEDED")
    ent.period_reserved = int(ent.period_reserved or 0) + quantity
    ent.save(update_fields=["period_reserved", "updated_at"])

    return UsageLedger.objects.create(
        ledger_no=UsageLedger.generate_no(),
        user=user,
        subscription=decision.subscription,
        feature_code=feature_code,
        action=UsageLedger.ACTION_RESERVE,
        quantity=quantity,
        status=UsageLedger.STATUS_RESERVED,
        idempotency_key=idempotency_key,
        source_type=source_type or "",
        source_id=source_id,
    )


@transaction.atomic
def commit_quota(ledger: UsageLedger) -> UsageLedger:
    ledger = UsageLedger.objects.select_for_update().get(pk=ledger.pk)
    if ledger.status == UsageLedger.STATUS_COMMITTED:
        return ledger
    if ledger.status == UsageLedger.STATUS_RELEASED:
        raise AppAPIException("额度已释放，无法结算", code="SUBSCRIPTION_LEDGER_INVALID")
    ent = (
        FeatureEntitlement.objects.select_for_update()
        .filter(
            user=ledger.user,
            subscription_id=ledger.subscription_id,
            feature_code=ledger.feature_code,
        )
        .first()
    )
    if ent:
        reserved = max(0, int(ent.period_reserved or 0) - int(ledger.quantity))
        ent.period_reserved = reserved
        ent.period_used = int(ent.period_used or 0) + int(ledger.quantity)
        ent.save(update_fields=["period_reserved", "period_used", "updated_at"])
    ledger.status = UsageLedger.STATUS_COMMITTED
    ledger.action = UsageLedger.ACTION_COMMIT
    ledger.save(update_fields=["status", "action", "updated_at"])
    return ledger


@transaction.atomic
def release_quota(ledger: UsageLedger) -> UsageLedger:
    ledger = UsageLedger.objects.select_for_update().get(pk=ledger.pk)
    if ledger.status == UsageLedger.STATUS_RELEASED:
        return ledger
    if ledger.status == UsageLedger.STATUS_COMMITTED:
        # 已结算不回滚 used（业务失败应在 commit 前 release）
        return ledger
    ent = (
        FeatureEntitlement.objects.select_for_update()
        .filter(
            user=ledger.user,
            subscription_id=ledger.subscription_id,
            feature_code=ledger.feature_code,
        )
        .first()
    )
    if ent:
        ent.period_reserved = max(0, int(ent.period_reserved or 0) - int(ledger.quantity))
        ent.save(update_fields=["period_reserved", "updated_at"])
    ledger.status = UsageLedger.STATUS_RELEASED
    ledger.action = UsageLedger.ACTION_RELEASE
    ledger.save(update_fields=["status", "action", "updated_at"])
    return ledger


@contextmanager
def consume_feature(
    user,
    feature_code: str,
    *,
    idempotency_key: str,
    quantity: int = 1,
    source_type: str = "",
    points_spender=None,
    points_amount: int = 0,
    points_description: str = "",
):
    """
    统一扣费入口：订阅额度优先，否则走 points_spender；同一次不会双扣。
    yield MeterDecision（含 ledger 若走订阅）。
    成功后才 commit 额度或扣积分；失败 release，不扣点。
    """
    if not idempotency_key:
        raise AppAPIException("缺少幂等键", code="SUBSCRIPTION_IDEMPOTENCY_REQUIRED")

    existing = UsageLedger.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        yield MeterDecision(
            mode="subscription" if existing.subscription_id else "points",
            subscription=existing.subscription,
            ledger=existing,
        )
        return

    decision = decide_meter(user, feature_code, quantity=quantity)
    if decision.mode == "subscription":
        ledger = reserve_quota(
            user,
            feature_code,
            idempotency_key=idempotency_key,
            quantity=quantity,
            source_type=source_type,
        )
        decision.ledger = ledger
        try:
            yield decision
        except Exception:
            release_quota(ledger)
            raise
        commit_quota(ledger)
        return

    # points / free：先扣点（与历史 simple_quote 语义一致），成功后写 ledger 幂等回执
    if decision.mode == "points" and points_amount > 0:
        if points_spender is None:
            raise AppAPIException("积分扣费未配置", code="POINT_SPENDER_MISSING")
        points_spender(
            user,
            points_amount,
            source_type=source_type or feature_code,
            description=points_description or feature_code,
        )
    try:
        yield decision
    except Exception:
        raise
    UsageLedger.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "ledger_no": UsageLedger.generate_no(),
            "user": user,
            "subscription": None,
            "feature_code": feature_code,
            "action": UsageLedger.ACTION_COMMIT,
            "quantity": quantity,
            "status": UsageLedger.STATUS_COMMITTED,
            "source_type": source_type or feature_code,
        },
    )


@transaction.atomic
def confirm_subscription_order(order: SubscriptionOrder, admin_user) -> SubscriptionOrder:
    order = SubscriptionOrder.objects.select_for_update().get(pk=order.pk)
    if order.status == SubscriptionOrder.STATUS_CONFIRMED and order.subscription_id:
        return order
    if order.status == SubscriptionOrder.STATUS_CANCELLED:
        raise AppAPIException("开通单已取消", code="SUBSCRIPTION_ORDER_CANCELLED")
    sub = activate_subscription(
        user=order.user,
        plan_version=order.plan_version,
        source=Subscription.SOURCE_ORDER,
        granted_by=admin_user,
        note=f"order:{order.order_no}",
    )
    order.status = SubscriptionOrder.STATUS_CONFIRMED
    order.subscription = sub
    order.confirmed_by = admin_user
    order.confirmed_at = timezone.now()
    order.save(
        update_fields=[
            "status",
            "subscription",
            "confirmed_by",
            "confirmed_at",
            "updated_at",
        ]
    )
    return order


def entitlements_summary(user) -> dict:
    sub = get_active_subscription(user)
    ents = []
    if sub:
        for e in FeatureEntitlement.objects.filter(subscription=sub).order_by("feature_code"):
            ents.append(
                {
                    "feature_code": e.feature_code,
                    "period_limit": e.period_limit,
                    "period_used": e.period_used,
                    "period_reserved": e.period_reserved,
                    "remaining": e.remaining,
                    "period_reset_at": e.period_reset_at.isoformat() if e.period_reset_at else None,
                }
            )
    return {
        "subscription": (
            {
                "id": sub.id,
                "status": sub.status,
                "source": sub.source,
                "starts_at": sub.starts_at.isoformat() if sub.starts_at else None,
                "ends_at": sub.ends_at.isoformat() if sub.ends_at else None,
                "plan": {
                    "id": sub.plan_version_id,
                    "code": sub.plan_version.code,
                    "name": sub.plan_version.name,
                    "billing_period": sub.plan_version.billing_period,
                },
            }
            if sub
            else None
        ),
        "entitlements": ents,
        "known_features": list(KNOWN_FEATURE_CODES),
    }
