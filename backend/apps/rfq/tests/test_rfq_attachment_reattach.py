"""S2：买方 RFQ 附件补传；终态拒绝。"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
import tempfile

from apps.rfq.models import RFQ, ServiceCategory

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RfqAttachmentReattachTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_s2_att@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="s2-att-cnc"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            scope="public",
            quantity=1,
            status="submitted",
            solicitation_status=RFQ.SOLICITATION_OPEN,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

    def test_reattach_allowed(self):
        f = SimpleUploadedFile("draw.pdf", b"%PDF-1.4", content_type="application/pdf")
        res = self.client.post(
            f"/api/member/rfqs/{self.rfq.id}/attachments",
            {"file": f},
            format="multipart",
        )
        self.assertEqual(res.status_code, 201, res.data)

    def test_reattach_blocked_when_won(self):
        self.rfq.status = "won"
        self.rfq.save(update_fields=["status"])
        f = SimpleUploadedFile("draw2.pdf", b"%PDF-1.4", content_type="application/pdf")
        res = self.client.post(
            f"/api/member/rfqs/{self.rfq.id}/attachments",
            {"file": f},
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "RFQ_STATUS_LOCKED")
