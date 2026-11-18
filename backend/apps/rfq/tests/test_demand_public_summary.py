"""S2：公开需求大厅不返回原始 remark，提供 public_summary。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.rfq.models import RFQ, ServiceCategory

User = get_user_model()


class DemandPublicSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email="buyer_s2_demand@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="s2-cnc"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            scope="public",
            quantity=12,
            material="AL6061",
            surface_finish="anodize",
            remark="私密备注：电话 13800001111 内部价",
            status="submitted",
            solicitation_status=RFQ.SOLICITATION_OPEN,
        )

    def test_list_and_detail_omit_remark(self):
        list_res = self.client.get("/api/public/demand-hall")
        self.assertEqual(list_res.status_code, 200, list_res.data)
        item = next(i for i in list_res.data["data"]["items"] if i["id"] == self.rfq.id)
        self.assertNotIn("remark", item)
        self.assertIn("public_summary", item)
        self.assertNotIn("13800001111", item["public_summary"])
        self.assertIn("AL6061", item["public_summary"])

        detail = self.client.get(f"/api/public/demand-hall/{self.rfq.id}")
        self.assertEqual(detail.status_code, 200, detail.data)
        data = detail.data["data"]
        self.assertNotIn("remark", data)
        self.assertIn("public_summary", data)
        self.assertNotIn("内部价", data["public_summary"])
