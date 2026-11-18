"""S2：公开企业详情与网站附件下载门禁。"""

import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile, SupplierAttachment

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PublicPartnerDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.visible_user = User.objects.create_user(
            email="visible_s2@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
            is_verified=True,
        )
        self.hidden_user = User.objects.create_user(
            email="hidden_s2@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
            is_verified=True,
        )
        self.visible = FactoryProfile.objects.create(
            user=self.visible_user,
            company_name="Visible Detail Co",
            region="Shenzhen",
            intro="CNC specialist",
            status="approved",
            is_public=True,
            contact_phone="13800000000",
            admin_note="internal only",
        )
        self.hidden = FactoryProfile.objects.create(
            user=self.hidden_user,
            company_name="Hidden Detail Co",
            status="approved",
            is_public=False,
        )
        self.public_att = SupplierAttachment.objects.create(
            profile=self.visible,
            file=SimpleUploadedFile("case.pdf", b"%PDF-1.4 public", content_type="application/pdf"),
            file_name="case.pdf",
            category="case",
            is_public=True,
        )
        self.private_att = SupplierAttachment.objects.create(
            profile=self.visible,
            file=SimpleUploadedFile("qual.pdf", b"%PDF-1.4 private", content_type="application/pdf"),
            file_name="qual.pdf",
            category="qualification",
            is_public=False,
        )

    def test_detail_visible_and_hides_sensitive_fields(self):
        res = self.client.get(f"/api/public/partners/{self.visible.id}")
        self.assertEqual(res.status_code, 200, res.data)
        data = res.data["data"]
        self.assertEqual(data["company_name"], "Visible Detail Co")
        self.assertNotIn("contact_phone", data)
        self.assertNotIn("admin_note", data)
        self.assertNotIn("business_license", data)
        self.assertNotIn("payment_terms", data)
        att_ids = [a["id"] for a in data["public_attachments"]]
        self.assertIn(self.public_att.id, att_ids)
        self.assertNotIn(self.private_att.id, att_ids)
        self.assertIn(
            f"/api/public/partner-attachments/{self.public_att.id}/download",
            data["public_attachments"][0]["file_url"],
        )

    def test_hidden_and_pending_detail_404(self):
        res = self.client.get(f"/api/public/partners/{self.hidden.id}")
        self.assertEqual(res.status_code, 404)

    def test_list_supports_q_and_pagination(self):
        res = self.client.get("/api/public/partners", {"q": "Visible", "page_size": 10})
        self.assertEqual(res.status_code, 200, res.data)
        names = [item["company_name"] for item in res.data["data"]["items"]]
        self.assertIn("Visible Detail Co", names)
        self.assertIn("pagination", res.data["data"])

    def test_public_attachment_download_gate(self):
        ok = self.client.get(f"/api/public/partner-attachments/{self.public_att.id}/download")
        self.assertEqual(ok.status_code, 200)
        denied = self.client.get(f"/api/public/partner-attachments/{self.private_att.id}/download")
        self.assertEqual(denied.status_code, 404)
