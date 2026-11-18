"""F01：公开企业目录仅展示 approved 且 is_public=true。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile

User = get_user_model()


class PublicPartnerIsPublicGateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.visible_user = User.objects.create_user(
            email="visible_f01@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
            is_verified=True,
        )
        self.hidden_user = User.objects.create_user(
            email="hidden_f01@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
            is_verified=True,
        )
        self.pending_user = User.objects.create_user(
            email="pending_f01@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
            is_verified=True,
        )
        self.visible = FactoryProfile.objects.create(
            user=self.visible_user,
            company_name="Visible Co",
            status="approved",
            is_public=True,
        )
        FactoryProfile.objects.create(
            user=self.hidden_user,
            company_name="Hidden Co",
            status="approved",
            is_public=False,
        )
        FactoryProfile.objects.create(
            user=self.pending_user,
            company_name="Pending Co",
            status="pending",
            is_public=True,
        )

    def test_list_only_approved_and_public(self):
        res = self.client.get("/api/public/partners")
        self.assertEqual(res.status_code, 200, res.data)
        items = res.data["data"]["items"]
        names = [item["company_name"] for item in items]
        self.assertIn("Visible Co", names)
        self.assertNotIn("Hidden Co", names)
        self.assertNotIn("Pending Co", names)
        for item in items:
            self.assertNotIn("contact_phone", item)
            self.assertNotIn("admin_note", item)
            self.assertNotIn("business_license", item)
