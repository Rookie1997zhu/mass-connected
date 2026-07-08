"""Smoke test for dieline asset upload API."""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.simplequote.dieline_import import parse_dxf


def post_json(url, data, token=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        method="POST",
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
    print("login:", login.get("code"))

    fixture = "apps/simplequote/tests/fixtures/sample_dieline.dxf"
    parsed = parse_dxf(fixture)
    print("parse_dxf:", len(parsed["entities"]), "entities", parsed["bbox"])

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    with open(fixture, "rb") as handle:
        file_data = handle.read()
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="source_file"; filename="sample_dieline.dxf"\r\n'
        "Content-Type: application/dxf\r\n\r\n"
    ).encode() + file_data + (
        f"\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="base_length"\r\n\r\n200\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="base_width"\r\n\r\n150\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="base_height"\r\n\r\n100\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="base_thickness"\r\n\r\n1.5\r\n'
        f"--{boundary}--\r\n"
    ).encode()

    req = urllib.request.Request(
        f"{base}/admin/dieline-templates/1/assets",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        print("upload failed:", exc.read().decode())
        sys.exit(1)

    print("upload:", result.get("code"), result.get("message"))
    asset = result.get("data", {})
    entities = (asset.get("parsed_geometry") or {}).get("entities", [])
    print("asset_status:", asset.get("mapping_status"), "entities:", len(entities))


if __name__ == "__main__":
    main()
