"""F03：首份报价进入 comparing 后公开征集仍可被第二家供应商参与。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile
from apps.rfq.models import Quote, QuoteRequest, RFQ, ServiceCategory

User = get_user_model()


class SolicitationContinuesAfterFirstQuoteTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_f03@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        self.s1 = User.objects.create_user(
            email="s1_f03@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
            is_verified=True,
        )
        self.s2 = User.objects.create_user(
            email="s2_f03@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
            is_verified=True,
        )
        FactoryProfile.objects.create(user=self.s1, company_name="S1", status="approved", is_public=True)
        FactoryProfile.objects.create(user=self.s2, company_name="S2", status="approved", is_public=True)
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="f03-cnc"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            scope="public",
            quantity=5,
            status="submitted",
            solicitation_status=RFQ.SOLICITATION_OPEN,
        )
        self.buyer_client = APIClient()
        self.buyer_client.force_authenticate(user=self.buyer)
        self.s1_client = APIClient()
        self.s1_client.force_authenticate(user=self.s1)
        self.s2_client = APIClient()
        self.s2_client.force_authenticate(user=self.s2)

    def test_second_supplier_can_grab_after_first_quote(self):
        grab1 = self.s1_client.post(f"/api/supplier/demand-hall/{self.rfq.id}/grab")
        self.assertEqual(grab1.status_code, 201, grab1.data)
        qr1 = QuoteRequest.objects.get(rfq=self.rfq, supplier=self.s1)

        quote_res = self.s1_client.post(
            f"/api/supplier/quote-requests/{qr1.id}/quotes",
            {"price_amount": 2000, "currency": "CNY", "lead_time_days": 5},
            format="multipart",
        )
        self.assertEqual(quote_res.status_code, 201, quote_res.data)
        self.rfq.refresh_from_db()
        self.assertEqual(self.rfq.status, "comparing")
        self.assertEqual(self.rfq.solicitation_status, RFQ.SOLICITATION_OPEN)

        hall = self.s2_client.get("/api/public/demand-hall")
        self.assertEqual(hall.status_code, 200)
        ids = [item["id"] for item in hall.data["data"]["items"]]
        self.assertIn(self.rfq.id, ids)

        grab2 = self.s2_client.post(f"/api/supplier/demand-hall/{self.rfq.id}/grab")
        self.assertEqual(grab2.status_code, 201, grab2.data)
        self.assertTrue(
            QuoteRequest.objects.filter(rfq=self.rfq, supplier=self.s2).exists()
        )

    def test_closed_solicitation_rejects_new_grab(self):
        self.rfq.solicitation_status = RFQ.SOLICITATION_CLOSED
        self.rfq.save(update_fields=["solicitation_status"])
        grab = self.s1_client.post(f"/api/supplier/demand-hall/{self.rfq.id}/grab")
        self.assertEqual(grab.status_code, 404)
