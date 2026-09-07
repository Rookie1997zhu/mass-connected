"""刀版积分买断与下载 API 测试。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.points.models import PointTransaction, PointWallet
from apps.points.services import add_points
from apps.simplequote.models import DielineCategory, DielineTemplatePurchase
from apps.simplequote.tests.test_packaging import create_mapped_template

User = get_user_model()

PURCHASE_URL = "/api/member/dieline-purchases"
DOWNLOAD_URL = "/api/member/dieline-templates/{code}/download"


class DielinePurchaseApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="dieline_buyer@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        self.user.email_verified_at = timezone.now()
        self.user.save(update_fields=["email_verified_at"])
        self.client.force_authenticate(user=self.user)
        self.category, _ = DielineCategory.objects.get_or_create(
            code="0200",
            defaults={"name_i18n": {"zh": "开槽箱"}, "sort_order": 20},
        )
        self.template = create_mapped_template(
            "0201",
            self.category,
            points_cost=100,
            purchase_enabled=True,
            preview_enabled=True,
            geometry_mode="formula",
            engine_key="slotted_rsc",
        )
        add_points(self.user, 500, "recharge", source_type="test", description="test topup")

    def _post(self, url, data):
        return self.client.post(url, data, format="json", secure=True)

    def _get(self, url, data=None):
        return self.client.get(url, data or {}, secure=True)

    def test_purchase_spends_points_and_creates_record(self):
        res = self._post(PURCHASE_URL, {"template_code": "0201"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["code"], "OK")
        self.assertFalse(res.data["data"]["already_unlocked"])
        self.assertEqual(res.data["data"]["points_spent"], 100)

        purchase = DielineTemplatePurchase.objects.get(user=self.user, template=self.template)
        self.assertEqual(purchase.points_spent, 100)
        self.assertTrue(purchase.transaction_no)

        wallet = PointWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 400)
        tx = PointTransaction.objects.filter(
            user=self.user, type="spend", source_type="dieline_purchase", source_id=purchase.id
        ).first()
        self.assertIsNotNone(tx)

    def test_purchase_idempotent(self):
        self._post(PURCHASE_URL, {"template_code": "0201"})
        balance_before = PointWallet.objects.get(user=self.user).balance
        res = self._post(PURCHASE_URL, {"template_code": "0201"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["data"]["already_unlocked"])
        self.assertEqual(PointWallet.objects.get(user=self.user).balance, balance_before)
        self.assertEqual(
            DielineTemplatePurchase.objects.filter(user=self.user, template=self.template).count(),
            1,
        )

    def test_purchase_insufficient_points(self):
        PointWallet.objects.filter(user=self.user).update(balance=10)
        res = self._post(PURCHASE_URL, {"template_code": "0201"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "POINT_INSUFFICIENT")
        self.assertFalse(
            DielineTemplatePurchase.objects.filter(user=self.user, template=self.template).exists()
        )

    def test_free_template_no_spend_tx(self):
        free = create_mapped_template(
            "0210",
            self.category,
            points_cost=0,
            purchase_enabled=True,
            preview_enabled=True,
            geometry_mode="formula",
            engine_key="folding_shipping",
        )
        balance_before = PointWallet.objects.get(user=self.user).balance
        res = self._post(PURCHASE_URL, {"template_code": "0210"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["points_spent"], 0)
        self.assertEqual(PointWallet.objects.get(user=self.user).balance, balance_before)
        self.assertFalse(
            PointTransaction.objects.filter(
                user=self.user, source_type="dieline_purchase", source_id=res.data["data"]["id"]
            ).exists()
        )
        self.assertTrue(
            DielineTemplatePurchase.objects.filter(user=self.user, template=free).exists()
        )

    def test_download_requires_purchase(self):
        res = self._get(
            DOWNLOAD_URL.format(code="0201"),
            {
                "format": "dxf",
                "length_mm": 200,
                "width_mm": 150,
                "height_mm": 100,
                "thickness_mm": 3,
                "dimension_type": "manufacturing",
            },
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["code"], "DIELINE_NOT_PURCHASED")

    def test_download_dxf_after_purchase(self):
        self._post(PURCHASE_URL, {"template_code": "0201"})
        res = self._get(
            DOWNLOAD_URL.format(code="0201"),
            {
                "format": "dxf",
                "length_mm": 200,
                "width_mm": 150,
                "height_mm": 100,
                "thickness_mm": 3,
                "dimension_type": "manufacturing",
            },
        )
        self.assertEqual(res.status_code, 200)
        body = res.content.decode("utf-8", errors="ignore")
        self.assertIn("SECTION", body)
        self.assertIn("CUT", body.upper())

    def test_download_ai_after_purchase(self):
        self._post(PURCHASE_URL, {"template_code": "0201"})
        res = self._get(
            DOWNLOAD_URL.format(code="0201"),
            {
                "format": "ai",
                "length_mm": 200,
                "width_mm": 150,
                "height_mm": 100,
                "thickness_mm": 3,
                "dimension_type": "manufacturing",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.startswith(b"%PDF"))
        self.assertIn("attachment", res.get("Content-Disposition", ""))
        self.assertIn(".ai", res.get("Content-Disposition", ""))

    def test_paper_box_quote_retired(self):
        res = self._post(
            "/api/member/simple-quotes",
            {"quote_type": "paper_box", "inputs": {"box_code": "0201", "length_mm": 200}},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "SIMPLE_QUOTE_TYPE_RETIRED")


class DielineEngineExportTests(TestCase):
    def test_0201_blank_matches_formula(self):
        from apps.simplequote.dieline_engines import build_segments_by_engine
        from apps.simplequote.dieline_export import effective_bbox
        from apps.simplequote.packaging import unfold_size_0201

        geo = unfold_size_0201(200, 150, 100, 3, "manufacturing", 30, {})
        segments = build_segments_by_engine(
            "slotted_rsc",
            {
                "manufacturing": {
                    "length": geo["manufacturing_length_mm"],
                    "width": geo["manufacturing_width_mm"],
                    "height": geo["manufacturing_height_mm"],
                },
                "thickness_mm": geo["thickness_mm"],
                "glue_tab_mm": geo["glue_tab_mm"],
            },
        )
        min_x, min_y, max_x, max_y = effective_bbox(segments, exclude_kinds=("bleed",))
        self.assertAlmostEqual(max_x - min_x, geo["blank_width_mm"], places=1)
        self.assertAlmostEqual(max_y - min_y, geo["blank_height_mm"], places=1)
