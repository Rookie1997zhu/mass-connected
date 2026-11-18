"""S5：订阅方案/手动开通/额度优先于积分/幂等与到期。"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.points.models import PointWallet
from apps.points.services import add_points, get_rule_amount
from apps.subscription.models import (
    FEATURE_SIMPLE_QUOTE,
    FeatureEntitlement,
    PlanVersion,
    Subscription,
    UsageLedger,
)
from apps.subscription.services import activate_subscription, consume_feature, decide_meter

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class S5SubscriptionMeterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="buyer_s5@test.local",
            password="pass12345",
            role="member",
            is_active=True,
        )
        self.admin = User.objects.create_user(
            email="admin_s5@test.local",
            password="pass12345",
            role="operator",
            is_staff=True,
            is_active=True,
        )
        self.plan = PlanVersion.objects.create(
            code="draft_tools",
            name="Tools Draft",
            status=PlanVersion.STATUS_DRAFT,
            billing_period=PlanVersion.PERIOD_MONTH,
            features_json={FEATURE_SIMPLE_QUOTE: 5},
        )
        add_points(self.user, 5000, "recharge", source_type="test", description="seed")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin)

    def test_admin_grant_and_member_entitlements(self):
        res = self.admin_client.post(
            "/api/admin/subscription/grants",
            {"user_id": self.user.id, "plan_version_id": self.plan.id},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        me = self.client.get("/api/member/subscription/entitlements")
        self.assertEqual(me.status_code, 200, me.data)
        data = me.data["data"]
        self.assertIsNotNone(data["subscription"])
        self.assertEqual(data["subscription"]["status"], "active")
        codes = {e["feature_code"] for e in data["entitlements"]}
        self.assertIn(FEATURE_SIMPLE_QUOTE, codes)
        rem = next(e for e in data["entitlements"] if e["feature_code"] == FEATURE_SIMPLE_QUOTE)
        self.assertEqual(rem["remaining"], 5)

    def test_quota_preferred_over_points_no_double_charge(self):
        activate_subscription(
            user=self.user,
            plan_version=self.plan,
            source=Subscription.SOURCE_ADMIN_GRANT,
            granted_by=self.admin,
        )
        wallet_before = PointWallet.objects.get(user=self.user).balance
        spent = {"n": 0}

        def spender(user, amount, source_type="", source_id=None, description="", admin=None):
            spent["n"] += 1
            raise AssertionError("should not spend points when quota available")

        with consume_feature(
            self.user,
            FEATURE_SIMPLE_QUOTE,
            idempotency_key="s5-q-1",
            source_type="test",
            points_spender=spender,
            points_amount=1000,
        ) as meter:
            self.assertEqual(meter.mode, "subscription")
            self.assertIsNotNone(meter.ledger)

        self.assertEqual(spent["n"], 0)
        self.assertEqual(PointWallet.objects.get(user=self.user).balance, wallet_before)
        ent = FeatureEntitlement.objects.get(user=self.user, feature_code=FEATURE_SIMPLE_QUOTE)
        self.assertEqual(ent.period_used, 1)
        self.assertEqual(ent.period_reserved, 0)
        led = UsageLedger.objects.get(idempotency_key="s5-q-1")
        self.assertEqual(led.status, UsageLedger.STATUS_COMMITTED)

    def test_points_fallback_when_no_subscription(self):
        from apps.points.services import spend_points

        wallet_before = PointWallet.objects.get(user=self.user).balance
        cost = 1000
        with consume_feature(
            self.user,
            FEATURE_SIMPLE_QUOTE,
            idempotency_key="s5-p-1",
            source_type="test",
            points_spender=spend_points,
            points_amount=cost,
        ) as meter:
            self.assertEqual(meter.mode, "points")
        self.assertEqual(PointWallet.objects.get(user=self.user).balance, wallet_before - cost)

    def test_idempotent_replay_does_not_double_charge(self):
        activate_subscription(
            user=self.user,
            plan_version=self.plan,
            source=Subscription.SOURCE_ADMIN_GRANT,
            granted_by=self.admin,
        )
        for _ in range(2):
            with consume_feature(
                self.user,
                FEATURE_SIMPLE_QUOTE,
                idempotency_key="s5-idem",
                points_spender=lambda *a, **k: (_ for _ in ()).throw(AssertionError("no points")),
                points_amount=1000,
            ):
                pass
        ent = FeatureEntitlement.objects.get(user=self.user, feature_code=FEATURE_SIMPLE_QUOTE)
        self.assertEqual(ent.period_used, 1)
        self.assertEqual(UsageLedger.objects.filter(idempotency_key="s5-idem").count(), 1)

    def test_expired_subscription_falls_back_to_points(self):
        sub = activate_subscription(
            user=self.user,
            plan_version=self.plan,
            source=Subscription.SOURCE_ADMIN_GRANT,
            granted_by=self.admin,
            starts_at=timezone.now() - timedelta(days=40),
            ends_at=timezone.now() - timedelta(days=1),
        )
        sub.status = Subscription.STATUS_ACTIVE
        sub.save(update_fields=["status"])
        decision = decide_meter(self.user, FEATURE_SIMPLE_QUOTE)
        self.assertEqual(decision.mode, "points")

    def test_unpublished_plan_not_orderable(self):
        res = self.client.post(
            "/api/member/subscription/orders",
            {"plan_version_id": self.plan.id},
            format="multipart",
        )
        self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(res.data["code"], "SUBSCRIPTION_PLAN_NOT_ORDERABLE")

    def test_confirm_order_grants_once(self):
        plan = PlanVersion.objects.create(
            code="priced",
            name="Priced",
            status=PlanVersion.STATUS_PUBLISHED,
            billing_period=PlanVersion.PERIOD_MONTH,
            price_amount=10000,
            currency="KRW",
            features_json={FEATURE_SIMPLE_QUOTE: 3},
            published_at=timezone.now(),
        )
        order_res = self.client.post(
            "/api/member/subscription/orders",
            {"plan_version_id": plan.id},
            format="multipart",
        )
        self.assertEqual(order_res.status_code, 201, order_res.data)
        oid = order_res.data["data"]["id"]
        c1 = self.admin_client.post(f"/api/admin/subscription/orders/{oid}/confirm")
        self.assertEqual(c1.status_code, 200, c1.data)
        c2 = self.admin_client.post(f"/api/admin/subscription/orders/{oid}/confirm")
        self.assertEqual(c2.status_code, 200, c2.data)
        self.assertEqual(
            Subscription.objects.filter(user=self.user, status=Subscription.STATUS_ACTIVE).count(),
            1,
        )

    def test_public_plans_hide_unpriced(self):
        PlanVersion.objects.create(
            code="pub_noprice",
            name="No Price",
            status=PlanVersion.STATUS_PUBLISHED,
            features_json={FEATURE_SIMPLE_QUOTE: 1},
            published_at=timezone.now(),
        )
        anon = APIClient()
        res = anon.get("/api/public/subscription/plans")
        self.assertEqual(res.status_code, 200, res.data)
        items = res.data["data"]["items"]
        row = next(i for i in items if i["code"] == "pub_noprice")
        self.assertFalse(row["is_orderable"])
        self.assertNotIn("price_amount", row)
