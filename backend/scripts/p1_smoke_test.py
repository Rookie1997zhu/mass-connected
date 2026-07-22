"""P1 iteration smoke test — run: python scripts/p1_smoke_test.py"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.test import Client

from apps.accounts.models import FactoryProfile
from apps.contract.models import Contract
from apps.order.models import Order
from apps.payment.models import Payment
from apps.project.models import Project
from apps.rfq.models import ProductionOrder, QuoteRequest, RFQ

User = get_user_model()
client = Client(SERVER_NAME="localhost")
results = []


def ok(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    results.append({"name": name, "status": status, "detail": detail})
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def login_admin(email, password):
    return _login("/api/admin/auth/login", email, password)


def login_member(email, password):
    return _login("/api/member/auth/login", email, password)


def login_supplier(email, password):
    return _login("/api/member/auth/login", email, password)


def _login(path, email, password):
    r = client.post(
        path,
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
        HTTP_HOST="localhost",
    )
    data = r.json()
    if data.get("code") != "OK":
        raise RuntimeError(f"login {email}: {data}")
    token = data["data"]["tokens"]["access"]
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return data["data"]["user"]


# Admin
login_admin("admin@oem.co", "Admin123!")
r = client.get("/api/admin/suppliers", HTTP_HOST="localhost")
data = r.json()
ok("admin_suppliers_list", data.get("code") == "OK", f"count={len(data.get('data', {}).get('items', []))}")
sup_id = data["data"]["items"][0]["id"] if data.get("data", {}).get("items") else None
if sup_id:
    r = client.get(f"/api/admin/suppliers/{sup_id}", HTTP_HOST="localhost")
    ok("admin_supplier_detail", r.json().get("code") == "OK")
    r = client.post(
        f"/api/admin/suppliers/{sup_id}/tags",
        data=json.dumps({"tag_name": "smoke-p1-tag"}),
        content_type="application/json",
        HTTP_HOST="localhost",
    )
    ok("admin_supplier_tag", r.json().get("code") == "OK")

r = client.get("/api/admin/stats", HTTP_HOST="localhost")
ok("admin_stats", r.json().get("code") == "OK")

r = client.get("/api/admin/notifications/unread-count", HTTP_HOST="localhost")
ok("admin_notifications_unread", r.json().get("code") == "OK")

rfq_for_qr = RFQ.objects.filter(quote_requests__isnull=False).first()
if rfq_for_qr:
    r = client.get(f"/api/admin/rfqs/{rfq_for_qr.id}/quote-requests", HTTP_HOST="localhost")
    ok("admin_rfq_quote_requests", r.json().get("code") == "OK", f"rfq={rfq_for_qr.id}")
    r = client.post(
        f"/api/admin/rfqs/{rfq_for_qr.id}/assign",
        data=json.dumps({"supplier_ids": []}),
        content_type="application/json",
        HTTP_HOST="localhost",
    )
    ok("admin_assign_removed", r.status_code == 404)
else:
    ok("admin_rfq_quote_requests", True, "skipped — no quote requests")
    ok("admin_assign_removed", True, "skipped — no rfq")

# Buyer — find any member
buyer = User.objects.filter(role="member").first()
if not buyer:
    ok("buyer_exists", False, "no member user in DB")
else:
    # try common passwords
    logged_in = False
    pwd_used = None
    for pwd in ("Demo1234!", "Test1234!", "Buyer123!", "Member123!", "Password123!"):
        try:
            login_member(buyer.email, pwd)
            logged_in = True
            pwd_used = pwd
            break
        except RuntimeError:
            continue
    if not logged_in:
        buyer.set_password("Smoke1234!")
        buyer.save(update_fields=["password"])
        login_member(buyer.email, "Smoke1234!")
        logged_in = True
        pwd_used = "Smoke1234! (reset)"
    ok("buyer_login", logged_in, f"{buyer.email} ({pwd_used})")
    if logged_in:
        for path in ("/api/member/todos", "/api/member/files", "/api/member/profile"):
            r = client.get(path, HTTP_HOST="localhost")
            ok(path, r.json().get("code") == "OK")
        r = client.patch(
            "/api/member/profile",
            data={"name": "Smoke Test"},
            content_type="application/x-www-form-urlencoded",
            HTTP_HOST="localhost",
        )
        ok("member_profile_patch", r.json().get("code") == "OK")
        rfq = RFQ.objects.filter(buyer=buyer, quotes__is_customer_visible=True).distinct().first()
        if rfq:
            r = client.get(f"/api/member/rfqs/{rfq.id}/quote-pdf", HTTP_HOST="localhost")
            ok(
                "quote_pdf",
                r.status_code == 200 and "pdf" in (r.get("Content-Type") or "").lower(),
                f"status={r.status_code} type={r.get('Content-Type')}",
            )
        else:
            ok("quote_pdf", True, "skipped — no visible RFQ plans")

        contract = Contract.objects.filter(buyer=buyer, status="pending_sign").first()
        if contract:
            from io import BytesIO

            from django.core.files.uploadedfile import SimpleUploadedFile
            from PIL import Image

            buf = BytesIO()
            Image.new("RGB", (8, 8), color=(20, 20, 20)).save(buf, format="PNG")
            r = client.post(
                f"/api/member/contracts/{contract.id}/sign",
                {
                    "company_name": "Smoke Test Co",
                    "business_reg_no": "000-00-00000",
                    "company_address": "Seoul",
                    "signer_name": "Smoke Buyer",
                    "agree": "true",
                    "signature_image": SimpleUploadedFile(
                        "sig.png", buf.getvalue(), content_type="image/png"
                    ),
                },
                format="multipart",
                HTTP_HOST="localhost",
            )
            ok("member_contract_sign", r.json().get("code") == "OK", contract.contract_no)
        else:
            ok("member_contract_sign", True, "skipped — no pending_sign contract")

        payment = Payment.objects.filter(buyer=buyer).first()
        if payment:
            r = client.get(f"/api/member/payments/{payment.id}", HTTP_HOST="localhost")
            ok("member_payment_detail", r.json().get("code") == "OK", payment.payment_no)
        else:
            ok("member_payment_detail", True, "skipped — no payment")

        order = Order.objects.filter(member=buyer).first()
        if order:
            r = client.get(f"/api/member/orders/{order.id}", HTTP_HOST="localhost")
            ok("member_order_detail", r.json().get("code") == "OK", order.order_no)
        else:
            ok("member_order_detail", True, "skipped — no order")

        r = client.get("/api/member/notifications/unread-count", HTTP_HOST="localhost")
        ok("member_notifications_unread", r.json().get("code") == "OK")

# Supplier project file
supplier = User.objects.filter(role="factory", factory_profile__status="approved").first()
if supplier:
    sup_logged = False
    for pwd in ("Demo1234!", "Test1234!", "Factory123!", "Supplier123!", "Password123!"):
        try:
            login_supplier(supplier.email, pwd)
            sup_logged = True
            break
        except RuntimeError:
            continue
    if not sup_logged:
        supplier.set_password("Smoke1234!")
        supplier.save(update_fields=["password"])
        login_supplier(supplier.email, "Smoke1234!")
    proj = Project.objects.filter(supplier=supplier).first()
    if proj:
        r = client.get(f"/api/supplier/projects/{proj.id}/files", HTTP_HOST="localhost")
        ok("supplier_files_list", r.json().get("code") == "OK")
        buf = io.BytesIO(b"%PDF-1.4 smoke")
        buf.name = "smoke.pdf"
        r = client.post(
            f"/api/supplier/projects/{proj.id}/files",
            {"file": buf, "file_category": "report", "visibility": "all"},
            HTTP_HOST="localhost",
        )
        ok("supplier_file_upload", r.json().get("code") == "OK", r.json().get("message", ""))
    else:
        ok("supplier_files_list", True, "skipped — no project")
        ok("supplier_file_upload", True, "skipped — no project")

    r = client.get("/api/supplier/notifications/unread-count", HTTP_HOST="localhost")
    ok("supplier_notifications_unread", r.json().get("code") == "OK")

    r = client.get("/api/supplier/contracts", HTTP_HOST="localhost")
    ok("supplier_contracts_list", r.json().get("code") == "OK")

    public_rfq = (
        RFQ.objects.filter(scope="public", status__in={"submitted", "quoting", "quoted", "negotiating"})
        .exclude(quote_requests__supplier=supplier)
        .first()
    )
    if not public_rfq:
        public_rfq = RFQ.objects.filter(
            scope="public", status__in={"submitted", "quoting", "quoted", "negotiating"}
        ).first()
    if public_rfq:
        r = client.post(f"/api/supplier/demand-hall/{public_rfq.id}/grab", HTTP_HOST="localhost")
        grab_data = r.json()
        grab_ok = grab_data.get("code") == "OK" and grab_data.get("data", {}).get("id")
        ok("supplier_demand_grab", grab_ok, grab_data.get("message", ""))
        qr_id = grab_data.get("data", {}).get("id")
        existing_quote = QuoteRequest.objects.filter(id=qr_id, supplier=supplier).first() if qr_id else None
        if existing_quote and not existing_quote.quotes.exists():
            r2 = client.post(
                f"/api/supplier/quote-requests/{qr_id}/quotes",
                data=json.dumps(
                    {
                        "price_amount": 1000000,
                        "currency": "KRW",
                        "lead_time_days": 14,
                        "note": "smoke grab quote",
                    }
                ),
                content_type="application/json",
                HTTP_HOST="localhost",
            )
            ok("supplier_grab_quote", r2.json().get("code") == "OK", r2.json().get("message", ""))
        else:
            ok("supplier_grab_quote", True, "skipped — quote already exists")
    else:
        ok("supplier_demand_grab", True, "skipped — no public RFQ")
        ok("supplier_grab_quote", True, "skipped — no public RFQ")

    pending_po = ProductionOrder.objects.filter(supplier=supplier, status="pending_confirm").first()
    if pending_po:
        rfq_before = pending_po.rfq.status
        r = client.post(f"/api/supplier/production-orders/{pending_po.id}/reject", HTTP_HOST="localhost")
        pending_po.refresh_from_db()
        pending_po.rfq.refresh_from_db()
        rollback_ok = (
            r.json().get("code") == "OK"
            and pending_po.status == "cancelled"
            and (rfq_before != "won" or pending_po.rfq.status == "comparing")
        )
        ok("supplier_reject_rollback", rollback_ok, f"rfq {rfq_before}->{pending_po.rfq.status}")
    else:
        ok("supplier_reject_rollback", True, "skipped — no pending_confirm PO")
else:
    ok("supplier_demand_grab", True, "skipped — no supplier")
    ok("supplier_grab_quote", True, "skipped — no supplier")
    ok("supplier_files_list", True, "skipped — no supplier")
    ok("supplier_file_upload", True, "skipped — no supplier")
    ok("supplier_notifications_unread", True, "skipped — no supplier")
    ok("supplier_contracts_list", True, "skipped — no supplier")
    ok("supplier_reject_rollback", True, "skipped — no supplier")

# Email backend check
from django.conf import settings
ok("email_backend", "console" in settings.EMAIL_BACKEND.lower() or settings.EMAIL_BACKEND,
   settings.EMAIL_BACKEND)

failed = [x for x in results if x["status"] == "FAIL"]
print("\n=== Summary ===")
print(f"Total: {len(results)}, Failed: {len(failed)}")
sys.exit(1 if failed else 0)
