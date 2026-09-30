import os
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.blog.models import BlogPost
from apps.content.models import Download
from apps.inquiry.models import Inquiry
from apps.ops.services import STORAGE_CACHE_KEY, _probe_workers
from apps.order.models import Order
from apps.rfq.models import RFQ, ServiceCategory
from apps.blog.tests.client import SecureClient

User = get_user_model()


class OpsApiTests(TestCase):
    def setUp(self):
        self.client = SecureClient()
        self.admin = User.objects.create_user(
            email="ops_admin@test.local",
            password="pass12345",
            role="super_admin",
            is_active=True,
            is_verified=True,
        )
        self.operator = User.objects.create_user(
            email="ops_operator@test.local",
            password="pass12345",
            role="operator",
            is_active=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            email="ops_member@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        cache.delete(STORAGE_CACHE_KEY)

    def tearDown(self):
        cache.delete(STORAGE_CACHE_KEY)

    def test_anonymous_runtime_is_unauthorized(self):
        response = self.client.get("/api/admin/ops/runtime")
        self.assertEqual(response.status_code, 401)

    def test_operator_cannot_read_ops(self):
        self.client.force_authenticate(user=self.operator)
        runtime = self.client.get("/api/admin/ops/runtime")
        storage = self.client.get("/api/admin/ops/storage")
        behavior = self.client.get("/api/admin/ops/behavior")
        self.assertEqual(runtime.status_code, 403)
        self.assertEqual(storage.status_code, 403)
        self.assertEqual(behavior.status_code, 403)

    @patch("apps.ops.views.collect_runtime")
    def test_super_admin_runtime_has_live_cards_without_missing_services(self, collect_runtime):
        collect_runtime.return_value = {
            "cpu": {"percent": 3.5, "load_1m": 0.2},
            "memory": {"used_bytes": 10, "total_bytes": 20},
            "disk": {"used_bytes": 5, "total_bytes": 50, "path": "/app/media"},
            "services": [
                {"key": "mysql", "status": "ok", "latency_ms": 2},
                {"key": "redis", "status": "ok", "latency_ms": 1},
                {"key": "chat_ws", "status": "ok", "latency_ms": 4},
                {"key": "slicer", "status": "ok", "latency_ms": 20},
                {"key": "heavy", "status": "error", "latency_ms": None},
                {"key": "translate", "status": "ok", "latency_ms": 20},
                {"key": "oss", "status": "disabled", "latency_ms": None},
            ],
            "history": [],
        }
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/ops/runtime")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        keys = {item["key"] for item in data["services"]}
        self.assertEqual(
            keys, {"mysql", "redis", "chat_ws", "slicer", "heavy", "translate", "oss"}
        )
        self.assertEqual(data["history"], [])
        self.assertEqual(data["services"][-1]["status"], "disabled")

    def test_behavior_days_must_be_7_or_30(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/ops/behavior", {"days": 9})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "OPS_QUERY_INVALID")
        self.assertIn("days", response.data["errors"])

    def test_behavior_uses_existing_tables_and_skips_blog_daily(self):
        category = ServiceCategory.objects.create(name="纸盒", slug="ops-box")
        RFQ.objects.create(buyer=self.member, service_category=category)
        Order.objects.create(
            member=self.member,
            total_amount=1000,
            shipping_name="收件人",
            shipping_phone="010",
            shipping_address="首尔",
        )
        Inquiry.objects.create(name="访客", email="guest@test.local", message="想做纸盒")
        BlogPost.objects.create(title="笔记", view_count=12, language="zh", status="published")
        BlogPost.objects.create(title="另一篇", view_count=3, language="zh", status="draft")
        self.member.last_login = timezone.now()
        self.member.save(update_fields=["last_login"])
        old = User.objects.create_user(
            email="ops_old@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        User.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=40))

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/ops/behavior", {"days": 7})
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(len(data["daily"]), 7)
        self.assertNotIn("blog_views", data["daily"][0])
        self.assertEqual(data["totals"]["blog_views"], 15)
        self.assertEqual(data["totals"]["new_members"], 1)
        self.assertEqual(data["totals"]["rfqs"], 1)
        self.assertEqual(data["totals"]["orders"], 1)
        self.assertEqual(data["totals"]["inquiries"], 1)
        self.assertEqual(data["totals"]["members_logged_in"], 1)
        today = timezone.localdate().isoformat()
        today_row = next(row for row in data["daily"] if row["date"] == today)
        self.assertEqual(today_row["rfqs"], 1)

    def test_storage_lists_old_unreferenced_files_and_caches(self):
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media, USE_OSS=False):
                Download.objects.create(
                    title={"zh": "说明书"},
                    file=ContentFile(b"pdf", name="keep.pdf"),
                )
                old_path = Path(media) / "orphan-old.txt"
                old_path.write_text("old", encoding="utf-8")
                old_ts = time.time() - 48 * 3600
                os.utime(old_path, (old_ts, old_ts))
                new_path = Path(media) / "orphan-new.txt"
                new_path.write_text("new", encoding="utf-8")

                self.client.force_authenticate(user=self.admin)
                cold = self.client.get("/api/admin/ops/storage")
                self.assertEqual(cold.status_code, 200, cold.data)
                self.assertFalse(cold.data["data"]["cached"])
                self.assertIsNone(cold.data["data"]["counted_at"])

                recounted = self.client.get("/api/admin/ops/storage", {"recount": "1"})
                self.assertEqual(recounted.status_code, 200, recounted.data)
                payload = recounted.data["data"]
                self.assertTrue(payload["cached"])
                self.assertIsNotNone(payload["counted_at"])
                self.assertEqual(payload["oss"]["status"], "disabled")
                self.assertGreaterEqual(payload["local"]["file_count"], 2)
                keys = [item["key"] for item in payload["orphans"]["items"]]
                self.assertIn("orphan-old.txt", keys)
                self.assertNotIn("orphan-new.txt", keys)
                self.assertFalse(any(key.endswith("keep.pdf") for key in keys))

                cached = self.client.get("/api/admin/ops/storage")
                self.assertEqual(cached.data["data"]["counted_at"], payload["counted_at"])


class OpsWorkerProbeTests(TestCase):
    @patch("apps.ops.services._inspect_worker_queues", return_value=({"celery", "translate"}, 18))
    def test_worker_status_follows_queue_name(self, _inspect):
        services = {item["key"]: item for item in _probe_workers()}
        self.assertEqual(services["slicer"]["status"], "ok")
        self.assertEqual(services["translate"]["status"], "ok")
        self.assertEqual(services["heavy"]["status"], "error")
        self.assertEqual(services["slicer"]["latency_ms"], 18)
        self.assertIsNone(services["heavy"]["latency_ms"])
