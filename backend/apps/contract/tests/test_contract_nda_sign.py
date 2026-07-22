from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile
from apps.contract.services import create_contract_for_order, ensure_default_contract_template
from apps.rfq.models import ProductionOrder, Quote, RFQ, ServiceCategory

User = get_user_model()


def _tiny_png():
    buf = BytesIO()
    Image.new("RGB", (8, 8), color=(20, 20, 20)).save(buf, format="PNG")
    return buf.getvalue()


class ContractNdaSignApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email="buyer_nda@example.com", password="pass12345", role="member", is_active=True
        )
        self.supplier = User.objects.create_user(
            email="supplier_nda@example.com",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="NDA Factory", status="approved"
        )
        category = ServiceCategory.objects.create(name="Mold", slug="mold-nda-test")
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=category,
            quantity=10,
            status="won",
        )
        self.quote = Quote.objects.create(
            rfq=self.rfq,
            supplier=self.supplier,
            price_amount=5000,
            currency="KRW",
            lead_time_days=10,
            status="accepted",
        )
        self.order = ProductionOrder.objects.create(
            rfq=self.rfq,
            quote=self.quote,
            buyer=self.buyer,
            supplier=self.supplier,
            price_amount=5500,
            supplier_amount=5000,
            customer_amount=5500,
            currency="KRW",
            status="confirmed",
        )
        ensure_default_contract_template()
        self.contract = create_contract_for_order(self.order, self.quote)
        self.client.force_authenticate(self.buyer)

    def test_create_contract_uses_nda_template(self):
        self.assertEqual(self.contract.status, "pending_sign")
        self.assertEqual(self.contract.template_version, "nda-v1")
        self.assertIn("保密协议", self.contract.title)
        self.assertIn("保密信息", self.contract.rendered_body)
        self.assertFalse(bool(self.contract.pdf))

    def test_sign_requires_signature_image(self):
        res = self.client.post(
            f"/api/member/contracts/{self.contract.id}/sign",
            {
                "company_name": "Acme Co",
                "business_reg_no": "123",
                "company_address": "Seoul",
                "signer_name": "Kim",
                "agree": True,
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "CONTRACT_SIGNATURE_REQUIRED")

    def test_sign_requires_agree(self):
        image = SimpleUploadedFile("sig.png", _tiny_png(), content_type="image/png")
        res = self.client.post(
            f"/api/member/contracts/{self.contract.id}/sign",
            {
                "company_name": "Acme Co",
                "business_reg_no": "123",
                "company_address": "Seoul",
                "signer_name": "Kim",
                "agree": False,
                "signature_image": image,
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "CONTRACT_AGREE_REQUIRED")

    def test_sign_success_with_signature(self):
        image = SimpleUploadedFile("sig.png", _tiny_png(), content_type="image/png")
        res = self.client.post(
            f"/api/member/contracts/{self.contract.id}/sign",
            {
                "company_name": "Acme Co",
                "business_reg_no": "123-45-67890",
                "company_address": "Seoul Digital Road",
                "signer_name": "Kim Buyer",
                "agree": True,
                "signature_image": image,
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["code"], "OK")
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "signed")
        self.assertTrue(self.contract.signature_image)
        self.assertTrue(self.contract.pdf)
        self.assertEqual(self.contract.company_name, "Acme Co")
        self.assertIn("Acme Co", self.contract.rendered_body)
        self.assertIsNotNone(self.contract.agree_at)
        self.assertIsNotNone(self.contract.signed_at)
