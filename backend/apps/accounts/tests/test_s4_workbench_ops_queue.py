"""S4：工作台 action_items（还价/项目待办）与 AdminOpsQueue 聚合。"""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import FactoryProfile
from apps.chat.models import Conversation
from apps.payment.models import Payment
from apps.project.models import Project, ProjectIssue, ProjectTodo
from apps.rfq.models import (
    ProductionOrder,
    Quote,
    QuoteCounterOffer,
    QuoteRequest,
    RFQ,
    ServiceCategory,
)

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class S4WorkbenchActionItemsTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_s4@test.local",
            password="pass12345",
            role="member",
            is_active=True,
        )
        self.supplier = User.objects.create_user(
            email="supplier_s4@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="S4 Factory", status="approved"
        )
        self.category = ServiceCategory.objects.create(
            name={"zh": "CNC", "en": "CNC"}, slug="s4-wb"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            quantity=10,
            company="Buyer Co",
            status="comparing",
        )
        self.qr = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.supplier, status="assigned", created_by=self.supplier
        )
        self.quote = Quote.objects.create(
            rfq=self.rfq,
            quote_request=self.qr,
            supplier=self.supplier,
            price_amount=5000,
            currency="KRW",
            lead_time_days=14,
            status="sent",
            is_customer_visible=True,
        )
        self.counter = QuoteCounterOffer.objects.create(
            quote=self.quote,
            rfq=self.rfq,
            created_by=self.buyer,
            target_total_amount=4500,
            currency="KRW",
            status=QuoteCounterOffer.STATUS_PENDING,
        )
        self.project = Project.objects.create(
            project_no=Project.generate_no(),
            title="S4 Project",
            rfq=self.rfq,
            buyer=self.buyer,
            supplier=self.supplier,
            status="in_progress",
        )
        self.buyer_todo = ProjectTodo.objects.create(
            project=self.project,
            title="Buyer confirm sample",
            assignee_type="customer",
            is_done=False,
        )
        self.supplier_todo = ProjectTodo.objects.create(
            project=self.project,
            title="Supplier ship sample",
            assignee_type="supplier",
            is_done=False,
        )
        self.buyer_client = APIClient()
        self.buyer_client.force_authenticate(user=self.buyer)
        self.supplier_client = APIClient()
        self.supplier_client.force_authenticate(user=self.supplier)

    def test_buyer_workbench_includes_counter_and_todo(self):
        res = self.buyer_client.get("/api/member/workbench")
        self.assertEqual(res.status_code, 200, res.data)
        items = res.data["data"]["action_items"]
        kinds = {row["kind"] for row in items}
        self.assertIn("counter_offer_pending", kinds)
        self.assertIn("project_todo", kinds)
        counter_row = next(r for r in items if r["kind"] == "counter_offer_pending")
        self.assertEqual(counter_row["id"], self.counter.id)
        self.assertEqual(counter_row["cta"], "withdraw")
        self.assertIn("?tab=quotes", counter_row["href"])
        todo_row = next(r for r in items if r["kind"] == "project_todo")
        self.assertEqual(todo_row["id"], self.buyer_todo.id)
        self.assertEqual(todo_row["cta"], "toggle_todo")

    def test_supplier_dashboard_includes_counter_and_todo(self):
        res = self.supplier_client.get("/api/supplier/dashboard")
        self.assertEqual(res.status_code, 200, res.data)
        items = res.data["data"]["action_items"]
        kinds = {row["kind"] for row in items}
        self.assertIn("counter_offer_pending", kinds)
        self.assertIn("project_todo", kinds)
        self.assertIn("quote_request", kinds)
        counter_row = next(r for r in items if r["kind"] == "counter_offer_pending")
        self.assertEqual(counter_row["cta"], "respond_counter")
        todo_row = next(r for r in items if r["kind"] == "project_todo")
        self.assertEqual(todo_row["id"], self.supplier_todo.id)

    def test_supplier_project_todo_create_and_toggle(self):
        create_res = self.supplier_client.post(
            f"/api/supplier/projects/{self.project.id}/todos",
            {"title": "Prepare BOM"},
            format="json",
        )
        self.assertEqual(create_res.status_code, 201, create_res.data)
        todo_id = create_res.data["data"]["id"]
        self.assertEqual(create_res.data["data"]["assignee_type"], "supplier")
        self.assertFalse(create_res.data["data"]["is_done"])

        toggle_res = self.supplier_client.post(
            f"/api/supplier/projects/{self.project.id}/todos/{todo_id}/toggle"
        )
        self.assertEqual(toggle_res.status_code, 200, toggle_res.data)
        self.assertTrue(toggle_res.data["data"]["is_done"])

        # 供应商不能 toggle 客户待办
        deny = self.supplier_client.post(
            f"/api/supplier/projects/{self.project.id}/todos/{self.buyer_todo.id}/toggle"
        )
        self.assertEqual(deny.status_code, 404)


@override_settings(SECURE_SSL_REDIRECT=False)
class S4AdminOpsQueueTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin_s4@test.local",
            password="pass12345",
            role="operator",
            is_active=True,
            is_staff=True,
        )
        self.buyer = User.objects.create_user(
            email="buyer_ops@test.local",
            password="pass12345",
            role="member",
            is_active=True,
        )
        self.supplier = User.objects.create_user(
            email="supplier_ops@test.local",
            password="pass12345",
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        FactoryProfile.objects.create(
            user=self.supplier, company_name="Ops Factory", status="approved"
        )
        self.category = ServiceCategory.objects.create(
            name={"zh": "Mold", "en": "Mold"}, slug="s4-ops"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            quantity=5,
            status="won",
        )
        self.qr = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.supplier, status="quoted", created_by=self.supplier
        )
        self.quote = Quote.objects.create(
            rfq=self.rfq,
            quote_request=self.qr,
            supplier=self.supplier,
            price_amount=2000,
            currency="KRW",
            status="accepted",
        )
        self.order = ProductionOrder.objects.create(
            rfq=self.rfq,
            quote=self.quote,
            buyer=self.buyer,
            supplier=self.supplier,
            price_amount=2000,
            supplier_amount=2000,
            customer_amount=2000,
            currency="KRW",
            status="pending_confirm",
        )
        from apps.contract.models import Contract

        self.contract = Contract.objects.create(
            rfq=self.rfq,
            quote=self.quote,
            production_order=self.order,
            buyer=self.buyer,
            supplier=self.supplier,
            title="Ops Contract",
            amount=2000,
            currency="KRW",
            status="signed",
            contract_no=Contract.generate_no(),
        )
        self.payment = Payment.objects.create(
            payment_no=Payment.generate_no(),
            contract=self.contract,
            buyer=self.buyer,
            amount=2000,
            currency="KRW",
            status="pending_confirm",
        )
        self.project = Project.objects.create(
            project_no=Project.generate_no(),
            title="Ops Project",
            rfq=self.rfq,
            buyer=self.buyer,
            supplier=self.supplier,
            status="in_progress",
        )
        self.issue = ProjectIssue.objects.create(
            project=self.project,
            title="Delay risk",
            severity="high",
            status="open",
        )
        self.conversation = Conversation.objects.create(
            quote_request=self.qr,
            buyer=self.buyer,
            supplier=self.supplier,
            dispute_status=Conversation.DISPUTE_OPEN,
            disputed_at=timezone.now(),
            dispute_reason="Quality concern",
        )
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin)

    def test_ops_queue_aggregates_exceptions(self):
        res = self.admin_client.get("/api/admin/ops-queue")
        self.assertEqual(res.status_code, 200, res.data)
        data = res.data["data"]
        counts = data["counts"]
        self.assertGreaterEqual(counts["disputes_open"], 1)
        self.assertGreaterEqual(counts["payments_pending_confirm"], 1)
        self.assertGreaterEqual(counts["orders_pending_confirm"], 1)
        self.assertGreaterEqual(counts["project_issues_open"], 1)
        self.assertTrue(any(d["id"] == self.conversation.id for d in data["disputes"]))
        self.assertTrue(any(p["id"] == self.payment.id for p in data["payments"]))
        self.assertTrue(any(o["id"] == self.order.id for o in data["orders"]))
        self.assertTrue(any(i["id"] == self.issue.id for i in data["project_issues"]))

    def test_admin_stats_includes_exception_counts(self):
        res = self.admin_client.get("/api/admin/stats")
        self.assertEqual(res.status_code, 200, res.data)
        data = res.data["data"]
        self.assertIn("disputes_open", data)
        self.assertIn("orders_pending_confirm", data)
        self.assertIn("project_issues_open", data)
        self.assertGreaterEqual(data["disputes_open"], 1)
        self.assertGreaterEqual(data["orders_pending_confirm"], 1)
        self.assertGreaterEqual(data["project_issues_open"], 1)

    def test_ops_queue_requires_admin(self):
        member = APIClient()
        member.force_authenticate(user=self.buyer)
        res = member.get("/api/admin/ops-queue")
        self.assertIn(res.status_code, {401, 403})
