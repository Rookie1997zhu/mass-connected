from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile
from apps.contract.models import Contract
from apps.payment.models import Payment
from apps.project.models import Project
from apps.rfq.models import ProductionOrder, Quote, RFQ, ServiceCategory

User = get_user_model()


class PaymentConfirmApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email="buyer_pay@example.com", password="pass12345", role="member", is_active=True
        )
        self.supplier = User.objects.create_user(
            email="supplier_pay@example.com",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="Demo Factory", status="approved"
        )
        self.other_supplier = User.objects.create_user(
            email="other_supplier_pay@example.com",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.other_supplier, company_name="Other Factory", status="approved"
        )
        self.admin = User.objects.create_user(
            email="admin_pay@example.com",
            password="pass12345",
            role="operator",
            is_active=True,
            is_staff=True,
        )
        category = ServiceCategory.objects.create(name="Injection", slug="injection-test-pay")
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=category,
            quantity=1,
            status="won",
        )
        self.quote = Quote.objects.create(
            rfq=self.rfq,
            supplier=self.supplier,
            price_amount=1000,
            currency="CNY",
            lead_time_days=7,
            status="accepted",
        )
        self.order = ProductionOrder.objects.create(
            rfq=self.rfq,
            quote=self.quote,
            buyer=self.buyer,
            supplier=self.supplier,
            price_amount=1100,
            supplier_amount=1000,
            customer_amount=1100,
            currency="CNY",
            status="confirmed",
        )
        self.contract = Contract.objects.create(
            rfq=self.rfq,
            quote=self.quote,
            production_order=self.order,
            buyer=self.buyer,
            supplier=self.supplier,
            title="Test Contract",
            amount=1100,
            currency="CNY",
            status="pending_sign",
            contract_no=Contract.generate_no(),
        )
        self.payment = Payment.objects.create(
            payment_no=Payment.generate_no(),
            contract=self.contract,
            buyer=self.buyer,
            amount=1100,
            currency="CNY",
            status="unpaid",
        )

    def _attach_proof(self, payment):
        payment.proof = SimpleUploadedFile("proof.jpg", b"fake-image", content_type="image/jpeg")
        payment.status = "pending_confirm"
        payment.save(update_fields=["proof", "status", "updated_at"])

    def test_supplier_cannot_confirm_without_proof(self):
        self.client.force_authenticate(user=self.supplier)
        res = self.client.post(f"/api/supplier/payments/{self.payment.id}/confirm")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "PAYMENT_PROOF_REQUIRED")

    def test_other_supplier_cannot_confirm(self):
        self._attach_proof(self.payment)
        self.client.force_authenticate(user=self.other_supplier)
        res = self.client.post(f"/api/supplier/payments/{self.payment.id}/confirm")
        self.assertEqual(res.status_code, 404)

    def test_supplier_confirm_creates_project_once(self):
        self._attach_proof(self.payment)
        self.client.force_authenticate(user=self.supplier)
        res = self.client.post(f"/api/supplier/payments/{self.payment.id}/confirm")
        self.assertEqual(res.status_code, 200)
        self.payment.refresh_from_db()
        self.contract.refresh_from_db()
        self.assertEqual(self.payment.status, "confirmed")
        self.assertEqual(self.contract.status, "signed")
        self.assertEqual(Project.objects.filter(production_order=self.order).count(), 1)
        self.assertTrue(res.data["data"].get("proof_url"))

        res2 = self.client.post(f"/api/supplier/payments/{self.payment.id}/confirm")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(Project.objects.filter(production_order=self.order).count(), 1)

    def test_admin_confirm_without_proof_still_works(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(f"/api/admin/payments/{self.payment.id}/confirm")
        self.assertEqual(res.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "confirmed")
        self.assertEqual(Project.objects.filter(production_order=self.order).count(), 1)

    def test_buyer_payment_serializer_includes_proof_meta(self):
        self._attach_proof(self.payment)
        self.client.force_authenticate(user=self.buyer)
        res = self.client.get(f"/api/member/payments/{self.payment.id}")
        self.assertEqual(res.status_code, 200)
        data = res.data["data"]
        self.assertTrue(data.get("proof_url"))
        self.assertEqual(data.get("proof_file_ext"), "jpg")
        self.assertTrue(data.get("proof_is_previewable"))
