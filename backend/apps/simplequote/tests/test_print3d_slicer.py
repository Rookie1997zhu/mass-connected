"""Unit tests for print3d G-code parse, pricing, and upload validation."""
from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.simplequote.calculator import calc_print3d
from apps.simplequote.print3d_files import validate_print3d_upload
from apps.simplequote.slicer import SlicerError, extract_filament_usage


class FakeUpload:
    def __init__(self, name, data: bytes):
        self.name = name
        self.size = len(data)
        self._data = data
        self._pos = 0

    def read(self, n=-1):
        if n < 0:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk

    def seek(self, pos):
        self._pos = pos


class GcodeParseTests(SimpleTestCase):
    def test_extract_filament_usage_ok(self):
        import tempfile
        import os

        content = """
; filament used [mm] = 1234.5
; filament used [g] = 12.34
; filament used [cm3] = 10.0
; estimated printing time (normal mode) = 1h 30m 5s
G1 X0 Y0
"""
        with tempfile.NamedTemporaryFile("w", suffix=".gcode", delete=False, encoding="utf-8") as fh:
            fh.write(content)
            path = fh.name
        try:
            usage = extract_filament_usage(path)
            self.assertEqual(usage["filament_weight_g"], 12.34)
            self.assertEqual(usage["estimated_time_seconds"], 3600 + 1800 + 5)
        finally:
            os.remove(path)

    def test_extract_filament_usage_missing_weight_raises(self):
        import tempfile
        import os

        content = "; estimated printing time = 1h 0m 0s\n"
        with tempfile.NamedTemporaryFile("w", suffix=".gcode", delete=False, encoding="utf-8") as fh:
            fh.write(content)
            path = fh.name
        try:
            with self.assertRaises(SlicerError) as ctx:
                extract_filament_usage(path)
            self.assertEqual(ctx.exception.code, "PRINT3D_GCODE_PARSE_FAILED")
        finally:
            os.remove(path)


class Print3dPricingTests(SimpleTestCase):
    def test_legacy_mode(self):
        result = calc_print3d(
            {"material": "PLA", "model_weight_g": 10, "print_hours": 2, "quantity": 1, "post_process": "none"},
            {
                "material_price_PLA": 60,
                "loss_factor": 1.0,
                "machine_hour_rate": 1000,
                "post_none": 0,
            },
        )
        self.assertEqual(result["pricing_mode"], "legacy")
        self.assertEqual(result["unit_price"], 10 * 60 + 2 * 1000)

    def test_custom_mode_with_snapshot(self):
        snapshot = {
            "pricing_mode": "custom",
            "params": {
                "loss_factor": 1.0,
                "electricity_rate_per_kwh": 100,
                "printer_power_watts": 1000,
                "depreciation_per_hour": 1000,
                "other_costs_per_print": 0,
                "base_cost": 100,
                "gst_rate": 0,
            },
            "material": {"key": "PLA", "price_per_kg": 100000, "per_gram_price": 100},
            "printer": {"key": "prusa_mk3s", "markup_multiplier": 1.0},
            "post_processing": {"key": "none", "price": 0},
        }
        result = calc_print3d(
            {
                "model_weight_g": 1000,
                "print_hours": 1,
                "quantity": 1,
                "config_snapshot": snapshot,
            },
            snapshot["params"],
        )
        self.assertEqual(result["pricing_mode"], "custom")
        # material 1000g -> 100000 + elec 100 + dep 1000 + base 100 = 101200
        self.assertEqual(result["unit_price"], 101200)

    def test_per_gram_mode(self):
        snapshot = {
            "pricing_mode": "per_gram",
            "params": {"loss_factor": 1.0, "gst_rate": 0},
            "material": {"key": "PLA", "per_gram_price": 50},
            "printer": {"key": "prusa_mk3s", "markup_multiplier": 1.3},
            "post_processing": {"key": "sanding", "price": 100},
        }
        result = calc_print3d(
            {
                "model_weight_g": 10,
                "print_hours": 1,
                "quantity": 2,
                "config_snapshot": snapshot,
            },
            snapshot["params"],
        )
        self.assertEqual(result["pricing_mode"], "per_gram")
        self.assertEqual(result["unit_price"], 10 * 50 + 100)
        self.assertEqual(result["total"], (10 * 50 + 100) * 2)


class UploadValidationTests(SimpleTestCase):
    def test_reject_bad_ext(self):
        code, msg, ext = validate_print3d_upload(FakeUpload("a.obj", b"x"), 10_000_000)
        self.assertEqual(code, "PRINT3D_FILE_INVALID")

    def test_accept_step_magic(self):
        data = b"ISO-10303-21;\nHEADER;\n"
        code, msg, ext = validate_print3d_upload(FakeUpload("a.step", data), 10_000_000)
        self.assertIsNone(code)
        self.assertEqual(ext, ".step")


class Print3dDefaultPrinterTests(TestCase):
    """打印机不再由会员选择：选项不下发，快照固定为管理端默认打印机。"""

    def test_public_options_exclude_printers(self):
        from apps.simplequote.print3d_config import public_options_payload

        self.assertNotIn("printers", public_options_payload())

    def test_snapshot_uses_default_printer_and_ignores_member_input(self):
        from apps.simplequote.print3d_config import build_job_config_snapshot

        snap = build_job_config_snapshot({"material": "PLA", "quality": "standard"})
        self.assertEqual(snap["printer"]["key"], "prusa_mk3s")

    def test_admin_configured_default_printer_wins(self):
        from apps.simplequote.models import QuoteTable
        from apps.simplequote.print3d_config import build_job_config_snapshot

        QuoteTable.objects.create(
            quote_type="print3d",
            table_key="printers",
            rows=[
                {"key": "prusa_mk3s", "name": "Prusa", "enabled": True, "markup_multiplier": 1.3},
                {"key": "bambu_x1", "name": "Bambu", "enabled": True, "is_default": True, "markup_multiplier": 1.4},
            ],
            is_active=True,
        )
        snap = build_job_config_snapshot({"material": "PLA", "quality": "standard"})
        self.assertEqual(snap["printer"]["key"], "bambu_x1")


class Print3dJobApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="buyer_p3d@example.com",
            password="pass12345",
            role="member",
            is_active=True,
        )
        self.other = User.objects.create_user(
            email="other_p3d@example.com",
            password="pass12345",
            role="member",
            is_active=True,
        )
        self.client = APIClient()

    def test_options_requires_auth(self):
        res = self.client.get("/api/member/simple-quotes/print3d/options")
        self.assertIn(res.status_code, (401, 403))

    def test_job_detail_isolation(self):
        from apps.simplequote.models import Print3dSliceJob

        job = Print3dSliceJob.objects.create(
            buyer=self.user,
            status=Print3dSliceJob.STATUS_DONE,
            result={"filament_weight_g": 1, "print_hours": 0.5},
        )
        self.client.force_authenticate(user=self.other)
        res = self.client.get(f"/api/member/simple-quotes/print3d/slice-jobs/{job.id}")
        self.assertEqual(res.status_code, 404)
