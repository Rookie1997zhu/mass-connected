"""Activate mapped dieline asset for template 0201."""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.simplequote.models import DielineTemplateAsset


def post_json(url, data, token=None, method="POST"):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        method=method,
        headers={"Content-Type": "application/json"},
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def main():
    base = "http://127.0.0.1:8000/api"
    login = post_json(f"{base}/admin/auth/login", {"email": "admin@oem.co", "password": "Admin123!"})
    token = login["data"]["tokens"]["access"]

    asset = DielineTemplateAsset.objects.get(id=1)
    mapping = asset.mapping_schema or {}
    mapping["entity_roles"] = {"dxf_00001": "cut", "dxf_00002": "crease"}
    save = post_json(
        f"{base}/admin/dieline-templates/1/assets/1",
        {"mapping_schema": mapping, "base_dimensions": asset.base_dimensions},
        token,
        "PATCH",
    )
    print("save:", save.get("code"), save.get("data", {}).get("mapping_status"))

    activate = post_json(f"{base}/admin/dieline-templates/1/assets/1/activate", {}, token)
    print("activate:", activate.get("code"), activate.get("message"))

    catalog = json.loads(urllib.request.urlopen(f"{base}/packaging/fefco-catalog").read())
    template = next(item for item in catalog["data"]["templates"] if item["code"] == "0201")
    print("catalog:", template.get("parametric_asset_status"), bool(template.get("active_parametric_asset")))


if __name__ == "__main__":
    main()
