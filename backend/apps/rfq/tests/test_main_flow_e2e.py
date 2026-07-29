"""主流程端到端集成：发布需求 -> 抢单 -> 报价 -> 采纳 -> 接单 -> 签约 -> 付款 -> 确认 -> 项目启动。"""
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile
from apps.contract.models import Contract
from apps.contract.services import ensure_default_contract_template
from apps.payment.models import Payment
from apps.project.models import Project
from apps.rfq.models import ProductionOrder, Quote, QuoteRequest, RFQ, ServiceCategory

User = get_user_model()

RFQ_LIST_URL = "/api/member/rfqs"


def _tiny_png():
    buf = BytesIO()
    Image.new("RGB", (8, 8), color=(20, 20, 20)).save(buf, format="PNG")
    return buf.getvalue()


class MainFlowE2ETests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_e2e@test.local", password="pass12345", role="member", is_active=True
        )
        self.supplier = User.objects.create_user(
            email="supplier_e2e@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="E2E Factory", status="approved"
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC"}, slug="main-flow-e2e-cnc"
        )
        ensure_default_contract_template()

        self.buyer_client = APIClient()
        self.buyer_client.force_authenticate(user=self.buyer)
        self.supplier_client = APIClient()
        self.supplier_client.force_authenticate(user=self.supplier)

    def test_full_order_lifecycle(self):
        # 1. 会员发布公开需求
        create_res = self.buyer_client.post(
            RFQ_LIST_URL,
            {"service_category": self.category.id, "scope": "public", "quantity": 100},
            format="json",
        )
        self.assertEqual(create_res.status_code, 201, create_res.data)
        rfq_id = create_res.data["data"]["id"]

        # 2. 供应商在需求大厅抢单
        grab_res = self.supplier_client.post(f"/api/supplier/demand-hall/{rfq_id}/grab")
        self.assertEqual(grab_res.status_code, 201, grab_res.data)
        qr = QuoteRequest.objects.get(rfq_id=rfq_id, supplier=self.supplier)

        # 3. 供应商提交报价
        quote_res = self.supplier_client.post(
            f"/api/supplier/quote-requests/{qr.id}/quotes",
            {"price_amount": 5000, "currency": "CNY", "lead_time_days": 10},
            format="multipart",
        )
        self.assertEqual(quote_res.status_code, 201, quote_res.data)
        quote_id = quote_res.data["data"]["id"]

        # 4. 会员采纳报价 -> 生成生产订单、合同、付款单
        accept_res = self.buyer_client.post(
            f"{RFQ_LIST_URL}/{rfq_id}/quotes/{quote_id}/accept"
        )
        self.assertEqual(accept_res.status_code, 200, accept_res.data)
        self.assertEqual(accept_res.data["code"], "OK")

        order = ProductionOrder.objects.get(quote_id=quote_id)
        self.assertEqual(order.status, "pending_confirm")
        contract = Contract.objects.get(production_order=order)
        self.assertEqual(contract.status, "pending_sign")
        payment = Payment.objects.get(contract=contract)
        self.assertEqual(payment.status, "unpaid")

        quote = Quote.objects.get(pk=quote_id)
        self.assertEqual(quote.status, "accepted")

        # 5. 供应商确认接单
        confirm_res = self.supplier_client.post(
            f"/api/supplier/production-orders/{order.id}/confirm"
        )
        self.assertEqual(confirm_res.status_code, 200, confirm_res.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")

        # 6. 买家签署合同（含签名图片）
        signature = SimpleUploadedFile("sig.png", _tiny_png(), content_type="image/png")
        sign_res = self.buyer_client.post(
            f"/api/member/contracts/{contract.id}/sign",
            {
                "company_name": "E2E Buyer Co",
                "business_reg_no": "123-45-67890",
                "company_address": "Seoul Digital Road",
                "signer_name": "Kim Buyer",
                "agree": True,
                "signature_image": signature,
            },
            format="multipart",
        )
        self.assertEqual(sign_res.status_code, 200, sign_res.data)
        contract.refresh_from_db()
        self.assertEqual(contract.status, "signed")
        self.assertTrue(contract.signature_image)

        # 7. 买家上传付款凭证
        proof = SimpleUploadedFile("proof.png", _tiny_png(), content_type="image/png")
        proof_res = self.buyer_client.post(
            f"/api/member/payments/{payment.id}/proof",
            {"proof": proof},
            format="multipart",
        )
        self.assertEqual(proof_res.status_code, 200, proof_res.data)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending_confirm")

        # 8. 供应商确认收款
        pay_confirm_res = self.supplier_client.post(
            f"/api/supplier/payments/{payment.id}/confirm"
        )
        self.assertEqual(pay_confirm_res.status_code, 200, pay_confirm_res.data)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "confirmed")

        # 9. 项目已启动且阶段完成初始化
        project = Project.objects.get(production_order=order)
        self.assertEqual(project.stages.count(), 5)
        self.assertTrue(project.stages.filter(status="in_progress").exists())
        first_stage = project.stages.order_by("sort_order").first()
        self.assertEqual(first_stage.status, "in_progress")
