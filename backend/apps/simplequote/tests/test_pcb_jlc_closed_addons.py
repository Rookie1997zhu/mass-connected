"""jlc_pcb_quote 已闭合加价校准：阻焊色 / 无铅喷锡 / 确认稿。"""

import copy
import csv
import unittest
from pathlib import Path

from apps.simplequote.calculator import DEFAULT_PARAMS, calc_pcb
from apps.simplequote.calculator.pcb_jlc_closed_addons import (
    confirm_file_fee_cny,
    lead_free_hasl_fee_cny,
    solder_color_delta_cny,
    surface_finish_delta_cny,
)
from apps.simplequote.table_data import (
    PCB_BASE_PRICING,
    PCB_MANUFACTURING_PRICE_LIST,
    PCB_MANUFACTURING_PRICE_META,
    PCB_SERVICES,
    PCB_WEIGHTS,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
ADDONS_PATH = REPO_ROOT / "exports" / "jlc_pcb_quote" / "price_list" / "addons.csv"


def _params():
    params = dict(DEFAULT_PARAMS["pcb"])
    params.update(
        {
            "pcb_shipping_under_1kg": 24000,
            "pcb_shipping_per_kg": 11600,
            "cny_to_krw": 232.4,
            "pcb_manufacturing_margin_rate": 0.10,
        }
    )
    return params


def _tables_with_process_enabled():
    """启用 fr4 工艺调整，便于校准项自动报价。"""
    meta = copy.deepcopy(PCB_MANUFACTURING_PRICE_META[0])
    meta["validation_status"] = "passed"
    meta["acceptance_status"] = "passed"
    meta["enabled_materials"] = ["fr4", "fpc", "aluminum"]
    meta["estimator_enabled_materials"] = ["fr4", "fpc", "aluminum"]
    meta["process_enabled_materials"] = ["fr4", "fpc", "aluminum"]
    meta["process_model"] = {
        **(meta.get("process_model") or {}),
        "validationStatus": "passed",
    }
    return {
        "base_pricing": PCB_BASE_PRICING,
        "services": PCB_SERVICES,
        "weights": PCB_WEIGHTS,
        "manufacturing_price_list": [{**row, "enabled": True} for row in PCB_MANUFACTURING_PRICE_LIST],
        "manufacturing_price_meta": [meta],
    }


def _base_inputs():
    return {
        "base_item_no": 1,
        "weight_keys": [],
        "service_nos": [],
        "ad_consent": False,
        "shipping_weight_kg": 1,
        "include_pcb_manufacturing": True,
        "mfg_material": "fr4",
        "mfg_layers": 2,
        "mfg_width_mm": 100,
        "mfg_height_mm": 100,
        "mfg_quantity": 5,
        "mfg_board_thickness": "1.6",
        "mfg_solder_color": "绿色",
        "mfg_surface_finish": "有铅喷锡",
        "mfg_copper_thickness": "1oz",
        "mfg_solder_mask_coverage": "过孔盖油",
        "mfg_panel_design_count": "1",
        "mfg_confirm_production_file": "none",
    }


class ClosedAddonFormulaTests(unittest.TestCase):
    def test_solder_color_anchor_deltas(self):
        self.assertEqual(solder_color_delta_cny("绿色"), 0)
        self.assertEqual(solder_color_delta_cny("哑黑色"), 0)
        for color in ("红色", "黄色", "蓝色", "白色", "嘉立创紫"):
            self.assertEqual(solder_color_delta_cny(color), 30)

    def test_confirm_file_fees(self):
        self.assertEqual(confirm_file_fee_cny("none"), 0)
        self.assertEqual(confirm_file_fee_cny("twice"), 3)
        self.assertEqual(confirm_file_fee_cny("multi"), 10)
        self.assertEqual(confirm_file_fee_cny("confirm_twice_3"), 3)
        self.assertEqual(confirm_file_fee_cny("confirm_multi_10"), 10)

    def test_lead_free_hasl_matches_addons_csv(self):
        if not ADDONS_PATH.exists():
            self.skipTest("addons.csv missing")
        with ADDONS_PATH.open(encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        hasl_rows = [r for r in rows if r.get("factor", "").startswith("adornPut")]
        self.assertGreaterEqual(len(hasl_rows), 3)
        for row in hasl_rows:
            if "无铅喷锡" not in (row.get("factor_value") or ""):
                continue
            if row["factor"] == "adornPut" and row["factor_value"] == "无铅喷锡":
                fee = lead_free_hasl_fee_cny(100, 100, 5)
                self.assertAlmostEqual(fee, float(row["adornputmoney"]), delta=0.01)
            if row["factor"] == "adornPut_area":
                length = int(float(row["pcbLength"]))
                width = int(float(row["pcbWidth"]))
                qty = int(float(row["pcbNumber"]))
                fee = lead_free_hasl_fee_cny(length * 10, width * 10, qty)
                self.assertAlmostEqual(fee, float(row["adornputmoney"]), delta=0.02)

    def test_surface_finish_free_and_hasl(self):
        self.assertEqual(surface_finish_delta_cny("OSP", 100, 100, 5), 0)
        self.assertEqual(surface_finish_delta_cny("有铅喷锡", 100, 100, 5), 0)
        self.assertAlmostEqual(surface_finish_delta_cny("无铅喷锡", 100, 100, 5), 31.5, delta=0.01)


class ClosedAddonIntegrationTests(unittest.TestCase):
    def test_solder_color_red_adds_30_on_exact_lookup(self):
        tables = _tables_with_process_enabled()
        result = calc_pcb(
            {**_base_inputs(), "mfg_solder_color": "红色"},
            _params(),
            tables,
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        fields = [a["field"] for a in mfg.get("process_adjustments") or []]
        self.assertIn("solder_color", fields)
        color_adj = next(a for a in mfg["process_adjustments"] if a["field"] == "solder_color")
        self.assertAlmostEqual(color_adj["amount_cny"], 30, delta=0.01)

    def test_lead_free_hasl_area_formula_on_exact_lookup(self):
        tables = _tables_with_process_enabled()
        result = calc_pcb(
            {**_base_inputs(), "mfg_surface_finish": "无铅喷锡"},
            _params(),
            tables,
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        finish_adj = next(a for a in mfg["process_adjustments"] if a["field"] == "surface_finish")
        self.assertEqual(finish_adj["method"], "lead_free_hasl_area")
        self.assertAlmostEqual(finish_adj["amount_cny"], 31.5, delta=0.01)

    def test_confirm_file_twice_adds_3(self):
        tables = _tables_with_process_enabled()
        baseline = calc_pcb(_base_inputs(), _params(), tables)
        with_confirm = calc_pcb(
            {**_base_inputs(), "mfg_confirm_production_file": "twice"},
            _params(),
            tables,
        )
        base_mfg = baseline["pcb_manufacturing"]
        conf_mfg = with_confirm["pcb_manufacturing"]
        self.assertFalse(conf_mfg["requires_manual_review"])
        self.assertAlmostEqual(
            conf_mfg["jlc_estimate_cny"] - base_mfg["jlc_estimate_cny"],
            3.0,
            delta=0.01,
        )
        fields = [a["field"] for a in conf_mfg.get("process_adjustments") or []]
        self.assertIn("confirm_production_file", fields)

    def test_confirm_file_multi_adds_10(self):
        tables = _tables_with_process_enabled()
        baseline = calc_pcb(_base_inputs(), _params(), tables)
        with_confirm = calc_pcb(
            {**_base_inputs(), "mfg_confirm_production_file": "multi"},
            _params(),
            tables,
        )
        self.assertAlmostEqual(
            with_confirm["pcb_manufacturing"]["jlc_estimate_cny"]
            - baseline["pcb_manufacturing"]["jlc_estimate_cny"],
            10.0,
            delta=0.01,
        )

    def test_price_list_not_replaced(self):
        """校准不得改动价目主表行数。"""
        self.assertGreater(len(PCB_MANUFACTURING_PRICE_LIST), 100)


if __name__ == "__main__":
    unittest.main()
