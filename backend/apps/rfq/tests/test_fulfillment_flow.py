"""RFQ 履约最小集成：会员发布需求 -> 供应商抢单 -> 供应商报价 -> 会员可见报价。"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile
from apps.rfq.models import Quote, QuoteRequest, RFQ, ServiceCategory

User = get_user_model()

RFQ_LIST_URL = "/api/member/rfqs"


class RfqFulfillmentFlowTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_fulfill@test.local", password="pass12345", role="member", is_active=True
        )
        self.supplier = User.objects.create_user(
            email="supplier_fulfill@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="Fulfillment Factory", status="approved"
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="fulfillment-flow-cnc"
        )

    def test_buyer_publish_supplier_grab_quote_and_buyer_sees_quote(self):
        buyer_client = APIClient()
        buyer_client.force_authenticate(user=self.buyer)
        supplier_client = APIClient()
        supplier_client.force_authenticate(user=self.supplier)

        # 1. 会员发布公开需求（进入需求大厅）
        create_res = buyer_client.post(
            RFQ_LIST_URL,
            {"service_category": self.category.id, "scope": "public", "quantity": 100},
            format="json",
        )
        self.assertEqual(create_res.status_code, 201, create_res.data)
        self.assertEqual(create_res.data["code"], "OK")
        rfq_id = create_res.data["data"]["id"]
        rfq = RFQ.objects.get(pk=rfq_id)
        self.assertEqual(rfq.status, "submitted")

        # 2. 供应商在需求大厅抢单
        grab_res = supplier_client.post(f"/api/supplier/demand-hall/{rfq_id}/grab")
        self.assertEqual(grab_res.status_code, 201, grab_res.data)
        self.assertEqual(grab_res.data["code"], "OK")
        qr = QuoteRequest.objects.get(rfq=rfq, supplier=self.supplier)
        self.assertEqual(qr.status, "viewed")
        rfq.refresh_from_db()
        self.assertEqual(rfq.status, "quoting")

        # 再次抢单幂等，不重复创建
        regrab_res = supplier_client.post(f"/api/supplier/demand-hall/{rfq_id}/grab")
        self.assertEqual(regrab_res.status_code, 200)
        self.assertEqual(QuoteRequest.objects.filter(rfq=rfq, supplier=self.supplier).count(), 1)

        # 3. 供应商提交报价
        quote_res = supplier_client.post(
            f"/api/supplier/quote-requests/{qr.id}/quotes",
            {"price_amount": 5000, "currency": "CNY", "lead_time_days": 10},
            format="multipart",
        )
        self.assertEqual(quote_res.status_code, 201, quote_res.data)
        self.assertEqual(quote_res.data["code"], "OK")
        quote_id = quote_res.data["data"]["id"]
        quote = Quote.objects.get(pk=quote_id)
        self.assertTrue(quote.is_customer_visible)
        self.assertEqual(quote.status, "sent")
        qr.refresh_from_db()
        self.assertEqual(qr.status, "quoted")
        rfq.refresh_from_db()
        self.assertEqual(rfq.status, "comparing")

        # 4. 会员可见该报价
        member_view_res = buyer_client.get(f"{RFQ_LIST_URL}/{rfq_id}/quotes/{quote_id}")
        self.assertEqual(member_view_res.status_code, 200, member_view_res.data)
        self.assertEqual(member_view_res.data["code"], "OK")
        self.assertEqual(member_view_res.data["data"]["price_amount"], 5000)

        rfq_detail_res = buyer_client.get(f"{RFQ_LIST_URL}/{rfq_id}")
        self.assertEqual(rfq_detail_res.status_code, 200)
        plans_in_detail = rfq_detail_res.data["data"].get("plans") or []
        self.assertTrue(any(p["id"] == quote_id for p in plans_in_detail))

    def test_grab_fails_for_internal_scope_rfq(self):
        supplier_client = APIClient()
        supplier_client.force_authenticate(user=self.supplier)
        rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            scope="internal",
            status="submitted",
            quantity=10,
        )
        res = supplier_client.post(f"/api/supplier/demand-hall/{rfq.id}/grab")
        self.assertEqual(res.status_code, 404)
