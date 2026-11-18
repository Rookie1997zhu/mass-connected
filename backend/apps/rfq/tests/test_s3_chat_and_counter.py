"""S3：报价前沟通、会话门禁、接受幂等、结构化还价。"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile
from apps.contract.services import ensure_default_contract_template
from apps.rfq.models import ProductionOrder, Quote, QuoteRequest, RFQ, ServiceCategory

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class S3PreQuoteParticipantsTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_s3@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            name="Buyer S3",
        )
        self.s1 = User.objects.create_user(
            email="s1_s3@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        self.s2 = User.objects.create_user(
            email="s2_s3@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(user=self.s1, company_name="Alpha Co", status="approved")
        FactoryProfile.objects.create(user=self.s2, company_name="Beta Co", status="approved")
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="s3-participants"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            scope="public",
            quantity=10,
            company="Buyer Corp",
            status="submitted",
            solicitation_status=RFQ.SOLICITATION_OPEN,
        )
        self.qr1 = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.s1, status="pending", created_by=self.s1
        )
        self.qr2 = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.s2, status="pending", created_by=self.s2
        )
        self.buyer_client = APIClient()
        self.buyer_client.force_authenticate(user=self.buyer)
        self.s1_client = APIClient()
        self.s1_client.force_authenticate(user=self.s1)

    def test_participants_before_quote_no_price_fields(self):
        res = self.buyer_client.get(f"/api/member/rfqs/{self.rfq.id}")
        self.assertEqual(res.status_code, 200, res.data)
        parts = res.data["data"]["participants"]
        self.assertEqual(len(parts), 2)
        ids = {p["quote_request_id"] for p in parts}
        self.assertEqual(ids, {self.qr1.id, self.qr2.id})
        for p in parts:
            self.assertIn("supplier_company_name", p)
            self.assertIn("has_visible_quote", p)
            self.assertFalse(p["has_visible_quote"])
            self.assertNotIn("price_amount", p)
            self.assertNotIn("unit_price", p)
            blob = str(p)
            self.assertNotIn("price", blob.lower())

    def test_peer_display_name_hides_buyer_email(self):
        open_res = self.s1_client.post(
            "/api/supplier/chat/conversations",
            {"quote_request_id": self.qr1.id},
            format="json",
        )
        self.assertEqual(open_res.status_code, 201, open_res.data)
        name = open_res.data["data"]["peer_display_name"]
        self.assertNotIn("@", name)
        self.assertNotIn(self.buyer.email, name)
        self.assertIn("Buyer", name)

    def test_readonly_after_cancelled_qr(self):
        open_res = self.buyer_client.post(
            "/api/member/chat/conversations",
            {"quote_request_id": self.qr1.id},
            format="json",
        )
        self.assertEqual(open_res.status_code, 201, open_res.data)
        conv_id = open_res.data["data"]["id"]
        send_ok = self.buyer_client.post(
            f"/api/member/chat/conversations/{conv_id}/messages",
            {"body": "澄清交期"},
            format="json",
        )
        self.assertEqual(send_ok.status_code, 201, send_ok.data)
        self.qr1.status = "cancelled"
        self.qr1.save(update_fields=["status", "updated_at"])
        send_block = self.buyer_client.post(
            f"/api/member/chat/conversations/{conv_id}/messages",
            {"body": "还能发吗"},
            format="json",
        )
        self.assertEqual(send_block.status_code, 403)
        self.assertEqual(send_block.data["code"], "CHAT_THREAD_READONLY")
        hist = self.buyer_client.get(f"/api/member/chat/conversations/{conv_id}/messages")
        self.assertEqual(hist.status_code, 200)
        self.assertGreaterEqual(len(hist.data["data"]["items"]), 1)

    def test_chat_attachment_upload(self):
        open_res = self.buyer_client.post(
            "/api/member/chat/conversations",
            {"quote_request_id": self.qr1.id},
            format="json",
        )
        conv_id = open_res.data["data"]["id"]
        f = SimpleUploadedFile("note.txt", b"hello chat", content_type="text/plain")
        up = self.buyer_client.post(
            f"/api/member/chat/conversations/{conv_id}/attachments",
            {"file": f, "body": ""},
            format="multipart",
        )
        self.assertEqual(up.status_code, 201, up.data)
        msg = up.data["data"]
        self.assertTrue(msg["attachments"])
        att_id = msg["attachments"][0]["id"]
        dl = self.buyer_client.get(
            f"/api/member/chat/conversations/{conv_id}/attachments/{att_id}/download"
        )
        self.assertEqual(dl.status_code, 200)


@override_settings(SECURE_SSL_REDIRECT=False)
class S3AcceptIdempotencyTests(TestCase):
    def setUp(self):
        ensure_default_contract_template()
        self.buyer = User.objects.create_user(
            email="buyer_s3_accept@test.local",
            password="pass12345",
            role="member",
            is_active=True,
        )
        self.supplier = User.objects.create_user(
            email="sup_s3_accept@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="Accept Factory", status="approved"
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="s3-accept"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            scope="public",
            quantity=5,
            status="quoted",
            solicitation_status=RFQ.SOLICITATION_CLOSED,
            markup_percent=10,
        )
        self.qr = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.supplier, status="quoted", created_by=self.supplier
        )
        self.quote = Quote.objects.create(
            rfq=self.rfq,
            quote_request=self.qr,
            supplier=self.supplier,
            price_amount=10000,
            currency="KRW",
            lead_time_days=7,
            status="sent",
            is_customer_visible=True,
            plan_label="A",
            revision_version=2,
        )

    def test_idempotent_accept_replay(self):
        client = APIClient()
        client.force_authenticate(user=self.buyer)
        headers = {"HTTP_IDEMPOTENCY_KEY": "s3-accept-key-1"}
        r1 = client.post(
            f"/api/member/rfqs/{self.rfq.id}/quotes/{self.quote.id}/accept",
            **headers,
        )
        self.assertEqual(r1.status_code, 200, r1.data)
        r2 = client.post(
            f"/api/member/rfqs/{self.rfq.id}/quotes/{self.quote.id}/accept",
            **headers,
        )
        self.assertEqual(r2.status_code, 200, r2.data)
        self.assertEqual(ProductionOrder.objects.filter(rfq=self.rfq).count(), 1)
        self.assertEqual(
            r1.data["data"]["production_order"]["id"],
            r2.data["data"]["production_order"]["id"],
        )


@override_settings(SECURE_SSL_REDIRECT=False)
class S3CounterOfferTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_s3_co@test.local",
            password="pass12345",
            role="member",
            is_active=True,
        )
        self.supplier = User.objects.create_user(
            email="sup_s3_co@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="CO Factory", status="approved"
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="s3-co"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            scope="public",
            quantity=20,
            status="quoted",
            solicitation_status=RFQ.SOLICITATION_CLOSED,
            markup_percent=10,
        )
        self.qr = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.supplier, status="quoted", created_by=self.supplier
        )
        self.quote = Quote.objects.create(
            rfq=self.rfq,
            quote_request=self.qr,
            supplier=self.supplier,
            price_amount=20000,
            currency="KRW",
            lead_time_days=14,
            status="sent",
            is_customer_visible=True,
            plan_label="B",
        )
        self.buyer_client = APIClient()
        self.buyer_client.force_authenticate(user=self.buyer)
        self.sup_client = APIClient()
        self.sup_client.force_authenticate(user=self.supplier)

    def test_counter_offer_accept_does_not_change_quote_price(self):
        create = self.buyer_client.post(
            f"/api/member/rfqs/{self.rfq.id}/quotes/{self.quote.id}/counter-offers",
            {
                "target_total_amount": 18000,
                "quantity": 20,
                "lead_time_days": 10,
                "note": "希望优惠",
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        co_id = create.data["data"]["id"]
        self.assertNotIn("price_amount", create.data["data"])
        acc = self.sup_client.post(f"/api/supplier/counter-offers/{co_id}/accept")
        self.assertEqual(acc.status_code, 200, acc.data)
        self.assertEqual(acc.data["data"]["status"], "accepted")
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.price_amount, 20000)
        self.assertEqual(self.quote.status, "sent")
