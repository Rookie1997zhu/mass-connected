"""F04：同一买方 idempotency_key 重放不重复创建 RFQ。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.rfq.models import RFQ, ServiceCategory

User = get_user_model()


class RfqCreateIdempotencyTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_f04@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="f04-cnc"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)
        self.payload = {
            "service_category": self.category.id,
            "scope": "public",
            "quantity": 3,
            "material": "AL6061",
            "idempotency_key": "f04-key-001",
        }

    def test_replay_returns_same_rfq(self):
        first = self.client.post("/api/member/rfqs", self.payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        rfq_id = first.data["data"]["id"]

        second = self.client.post("/api/member/rfqs", self.payload, format="json")
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data["data"]["id"], rfq_id)
        self.assertEqual(RFQ.objects.filter(buyer=self.buyer).count(), 1)

    def test_header_idempotency_key(self):
        first = self.client.post(
            "/api/member/rfqs",
            {**self.payload, "idempotency_key": ""},
            format="json",
            HTTP_IDEMPOTENCY_KEY="hdr-f04-1",
        )
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(
            "/api/member/rfqs",
            {**self.payload, "idempotency_key": ""},
            format="json",
            HTTP_IDEMPOTENCY_KEY="hdr-f04-1",
        )
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data["data"]["id"], first.data["data"]["id"])
