"""F02：买家接受报价响应不得泄漏供货侧原始金额。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile
from apps.contract.services import ensure_default_contract_template
from apps.rfq.models import Quote, QuoteRequest, RFQ, ServiceCategory
from apps.rfq.serializers.base import apply_markup

User = get_user_model()


class QuoteAcceptCustomerDtoTests(TestCase):
    def setUp(self):
        ensure_default_contract_template()
        self.buyer = User.objects.create_user(
            email="buyer_f02@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        self.supplier = User.objects.create_user(
            email="supplier_f02@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
            is_verified=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="F02 Factory", status="approved", is_public=True
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="f02-cnc"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            scope="public",
            quantity=10,
            status="quoting",
            markup_percent=20,
        )
        self.qr = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.supplier, status="quoted"
        )
        self.quote = Quote.objects.create(
            rfq=self.rfq,
            quote_request=self.qr,
            supplier=self.supplier,
            price_amount=1000,
            unit_price=100,
            mold_fee=50,
            sample_fee=20,
            currency="CNY",
            lead_time_days=7,
            status="sent",
            is_customer_visible=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

    def test_accept_returns_marked_up_customer_amounts_only(self):
        response = self.client.post(
            f"/api/member/rfqs/{self.rfq.id}/quotes/{self.quote.id}/accept"
        )
        self.assertEqual(response.status_code, 200, response.data)
        quote_data = response.data["data"]["quote"]
        self.assertEqual(quote_data["price_amount"], apply_markup(1000, 20))
        self.assertEqual(quote_data["unit_price"], apply_markup(100, 20))
        self.assertEqual(quote_data["mold_fee"], apply_markup(50, 20))
        self.assertEqual(quote_data["sample_fee"], apply_markup(20, 20))
        self.assertNotIn("is_customer_visible", quote_data)
        self.assertNotIn("supplier", quote_data)
        order = response.data["data"]["production_order"]
        self.assertIsNone(order.get("supplier_amount"))
        self.assertEqual(order.get("customer_amount"), apply_markup(1000, 20))
