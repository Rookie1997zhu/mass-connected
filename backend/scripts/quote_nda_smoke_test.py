"""Quote / shipping / NDA smoke test — run: python scripts/quote_nda_smoke_test.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.test import Client

from apps.points.services import add_points

User = get_user_model()
client = Client(SERVER_NAME="localhost")
results = []


def ok(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    results.append({"name": name, "status": status, "detail": detail})
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def login_member(email, password):
    r = client.post(
        "/api/member/auth/login",
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


def login_admin():
    r = client.post(
        "/api/admin/auth/login",
        data=json.dumps({"email": "admin@oem.co", "password": "Admin123!"}),
        content_type="application/json",
        HTTP_HOST="localhost",
    )
    data = r.json()
    if data.get("code") != "OK":
        raise RuntimeError(f"admin login: {data}")
    token = data["data"]["tokens"]["access"]
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"


# Admin quote tables
login_admin()
r = client.get("/api/admin/quote-tables?quote_type=pcba", HTTP_HOST="localhost")
data = r.json()
tables = data.get("data", {}).get("items", [])
ok("admin_quote_tables_pcba", data.get("code") == "OK" and len(tables) >= 1, f"count={len(tables)}")

# Buyer login
buyer = User.objects.filter(role="member").first()
if not buyer:
    ok("buyer_exists", False, "no member user")
    sys.exit(1)

logged_in = False
for pwd in ("Demo1234!", "Test1234!", "Buyer123!", "Member123!", "Password123!", "Smoke1234!"):
    try:
        login_member(buyer.email, pwd)
        logged_in = True
        break
    except RuntimeError:
        continue
if not logged_in:
    buyer.set_password("Smoke1234!")
    buyer.save(update_fields=["password"])
    login_member(buyer.email, "Smoke1234!")
ok("buyer_login", True, buyer.email)

add_points(buyer, 5000, "adjust", description="smoke test grant")

# Shipping air
r = client.post(
    "/api/member/simple-quotes/shipping-estimate",
    data=json.dumps(
        {"mode": "air", "weight_kg": 0.6, "length_cm": 20, "width_cm": 20, "height_cm": 10}
    ),
    content_type="application/json",
    HTTP_HOST="localhost",
)
air = r.json()
fee = air.get("data", {}).get("fee_krw")
ok("shipping_air", air.get("code") == "OK" and fee == 21000, f"fee_krw={fee}")

# Shipping LCL（文档示例含提货 + C/O → 731,818 KRW）
r = client.post(
    "/api/member/simple-quotes/shipping-estimate",
    data=json.dumps(
        {
            "mode": "lcl",
            "cbm": 3,
            "weight_kg": 250,
            "service_days": 4,
            "has_battery": False,
            "has_pickup": True,
            "has_co": True,
        }
    ),
    content_type="application/json",
    HTTP_HOST="localhost",
)
lcl = r.json()
lcl_fee = lcl.get("data", {}).get("fee_krw")
ok(
    "shipping_lcl",
    lcl.get("code") == "OK" and lcl_fee and abs(lcl_fee - 731818) <= 5000,
    f"fee_krw={lcl_fee} (expect ~731818)",
)

# PCBA quote
r = client.post(
    "/api/member/simple-quotes",
    data=json.dumps(
        {
            "quote_type": "pcba",
            "product_name": "Smoke PCBA",
            "inputs": {
                "pcb_quantity": 10,
                "array_count": 1,
                "components": [
                    {"package": "0402", "tech": "smt", "qty": 20},
                    {"package": "CAP-2PIN", "tech": "dip", "qty": 5},
                ],
            },
        }
    ),
    content_type="application/json",
    HTTP_HOST="localhost",
)
pcba = r.json()
pcba_data = pcba.get("data", {})
pcba_total = pcba_data.get("result", {}).get("total_krw") or pcba_data.get("total_amount")
ok(
    "quote_pcba",
    pcba.get("code") == "OK" and pcba_total and pcba_total > 0,
    f"total_krw={pcba_total}",
)

# PCB dev quote
r = client.post(
    "/api/member/simple-quotes",
    data=json.dumps(
        {
            "quote_type": "pcb",
            "product_name": "Smoke PCB Dev",
            "inputs": {
                "base_item_no": 1,
                "weight_keys": ["mass_production", "pcb_fr4"],
                "service_nos": [1],
                "shipping_weight_kg": 0.8,
                "ad_consent": True,
            },
        }
    ),
    content_type="application/json",
    HTTP_HOST="localhost",
)
pcb = r.json()
pcb_data = pcb.get("data", {})
pcb_total = pcb_data.get("total_amount") or pcb_data.get("result", {}).get("total")
ok("quote_pcb", pcb.get("code") == "OK" and pcb_total and pcb_total > 0, f"total={pcb_total}")

# NDA template
r = client.get("/api/member/nda/template", HTTP_HOST="localhost")
nda_tpl = r.json()
ok(
    "nda_template",
    nda_tpl.get("code") == "OK" and nda_tpl.get("data", {}).get("template", {}).get("id"),
    nda_tpl.get("message", ""),
)

# NDA sign
r = client.post(
    "/api/member/nda/sign",
    data=json.dumps({"company_name": "Smoke Test Co., Ltd.", "agree": True}),
    content_type="application/json",
    HTTP_HOST="localhost",
)
nda_sign = r.json()
ok(
    "nda_sign",
    nda_sign.get("code") == "OK" and nda_sign.get("data", {}).get("status") == "signed",
    nda_sign.get("message", ""),
)

# NDA list
r = client.get("/api/member/nda", HTTP_HOST="localhost")
nda_list = r.json()
items = nda_list.get("data", {}).get("items", nda_list.get("data", []))
if isinstance(items, dict):
    items = items.get("items", [])
count = len(items) if isinstance(items, list) else 0
ok("nda_list", nda_list.get("code") == "OK" and count >= 1, f"count={count}")

failed = [x for x in results if x["status"] == "FAIL"]
print("\n=== Summary ===")
print(f"Total: {len(results)}, Failed: {len(failed)}")
sys.exit(1 if failed else 0)
