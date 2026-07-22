"""PCB 开发报价中的样板制造费精确查表测试。"""

import copy
import unittest

from apps.simplequote.calculator import DEFAULT_PARAMS, calc_pcb
from apps.simplequote.table_data import (
    PCB_BASE_PRICING,
    PCB_MANUFACTURING_PRICE_LIST,
    PCB_MANUFACTURING_PRICE_META,
    PCB_SERVICES,
    PCB_WEIGHTS,
)


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


def _tables():
    enabled_list = [{**row, "enabled": True} for row in PCB_MANUFACTURING_PRICE_LIST]
    estimator = {
        "version": "jlc-cn-pcb-v4-estimator-test",
        "algorithm": "staged_log_interp_v1",
        "neighbors": 4,
        "areaWeight": 1,
        "quantityWeight": 1.35,
        "aspectWeight": 0.35,
        "validationStatus": "passed",
        "validationMetrics": {
            "overall": {"hitRate20": 0.875, "maxRelativeError": 0.4, "pass": True},
        },
        "materials": {
            "fr4": {"layers": [2, 4], "maxWidthMm": 200, "maxHeightMm": 200, "maxQuantity": 200},
            "fpc": {"layers": [1, 2], "maxWidthMm": 200, "maxHeightMm": 200, "maxQuantity": 200},
            "aluminum": {"layers": [1], "maxWidthMm": 200, "maxHeightMm": 200, "maxQuantity": 200},
        },
    }
    process_model = {
        "version": "jlc-cn-pcb-v5-process-test",
        "validationStatus": "passed",
        "materials": {
            "fr4": {
                "defaults": {
                    "boardThickness": "1.6",
                    "solderColor": "绿色",
                    "surfaceFinish": "有铅喷锡",
                    "copperThickness": "1oz",
                },
                "options": {
                    "boardThickness": ["1.6", "2.0"],
                    "solderColor": ["绿色", "红色"],
                    "surfaceFinish": ["有铅喷锡", "沉金"],
                    "copperThickness": ["1oz", "2oz"],
                },
                "factors": {
                    "boardThickness": {
                        "1.6": {"method": "multiplier", "multiplier": 1},
                        "2.0": {"method": "multiplier", "multiplier": 1.1, "layers": [2]},
                    },
                    "solderColor": {
                        "绿色": {"method": "multiplier", "multiplier": 1},
                        "红色": {"method": "multiplier", "multiplier": 1.2},
                    },
                    "surfaceFinish": {
                        "有铅喷锡": {"method": "multiplier", "multiplier": 1},
                        "沉金": {"method": "additive", "additiveCny": 20},
                    },
                    "copperThickness": {
                        "1oz": {"method": "multiplier", "multiplier": 1},
                        "2oz": {"method": "multiplier", "multiplier": 1.3},
                    },
                },
            },
            "fpc": {
                "defaults": {
                    "boardThickness": "0.11",
                    "solderColor": "页面默认",
                    "surfaceFinish": "沉金",
                    "copperThickness": "1oz",
                },
                "options": {
                    "boardThickness": ["0.11", "0.12"],
                    "solderColor": ["页面默认"],
                    "surfaceFinish": ["沉金"],
                    "copperThickness": ["1oz"],
                },
                "factors": {
                    "boardThickness": {
                        "0.11": {"method": "multiplier", "multiplier": 1},
                        "0.12": {"method": "multiplier", "multiplier": 1.05},
                    },
                    "solderColor": {"页面默认": {"method": "multiplier", "multiplier": 1}},
                    "surfaceFinish": {"沉金": {"method": "multiplier", "multiplier": 1}},
                    "copperThickness": {"1oz": {"method": "multiplier", "multiplier": 1}},
                },
            },
            "aluminum": {
                "defaults": {
                    "boardThickness": "1.6",
                    "solderColor": "绿色",
                    "surfaceFinish": "无铅喷锡",
                    "copperThickness": "1oz",
                },
                "options": {
                    "boardThickness": ["1.6", "2.0"],
                    "solderColor": ["绿色", "红色"],
                    "surfaceFinish": ["无铅喷锡"],
                    "copperThickness": ["1oz"],
                },
                "factors": {
                    "boardThickness": {
                        "1.6": {"method": "multiplier", "multiplier": 1},
                        "2.0": {"method": "multiplier", "multiplier": 1.1},
                    },
                    "solderColor": {
                        "绿色": {"method": "multiplier", "multiplier": 1},
                        "红色": {"method": "multiplier", "multiplier": 1.1},
                    },
                    "surfaceFinish": {"无铅喷锡": {"method": "multiplier", "multiplier": 1}},
                    "copperThickness": {"1oz": {"method": "multiplier", "multiplier": 1}},
                },
            },
        },
    }
    return {
        "base_pricing": PCB_BASE_PRICING,
        "services": PCB_SERVICES,
        "weights": PCB_WEIGHTS,
        "manufacturing_price_list": enabled_list,
        "manufacturing_price_meta": [
            {
                **PCB_MANUFACTURING_PRICE_META[0],
                "validation_status": "passed",
                "acceptance_status": "passed",
                "enabled_materials": ["fr4", "fpc", "aluminum"],
                "estimator_enabled_materials": ["fr4", "fpc", "aluminum"],
                "estimator": estimator,
                "process_enabled_materials": ["fr4", "fpc", "aluminum"],
                "process_options": {
                    key: {"defaults": value["defaults"], "options": value["options"]}
                    for key, value in process_model["materials"].items()
                },
                "process_model": process_model,
                "version": "jlc-cn-pcb-v5-test",
                "active_price_version": "jlc-cn-pcb-v5-test",
                "fallback_version": "jlc-cn-pcb-v6-20260712",
            }
        ],
    }


def _base_inputs():
    return {
        "base_item_no": 2,
        "weight_keys": ["mass_production", "pcb_fr4", "qty_2", "size_100"],
        "service_nos": [],
        "ad_consent": False,
        "shipping_weight_kg": 1,
    }


def _manufacturing_row(material_key, layers, width_mm, height_mm, quantity):
    return next(
        row
        for row in PCB_MANUFACTURING_PRICE_LIST
        if row["material_key"] == material_key
        and row["layers"] == layers
        and row["width_mm"] == width_mm
        and row["height_mm"] == height_mm
        and row["quantity"] == quantity
    )


class PcbManufacturingQuoteTests(unittest.TestCase):
    def test_switch_off_keeps_existing_pcb_total(self):
        inputs = _base_inputs()
        result = calc_pcb(inputs, _params(), _tables())
        with_disabled = calc_pcb({**inputs, "include_pcb_manufacturing": False}, _params(), _tables())
        self.assertEqual(result["total"], with_disabled["total"])
        self.assertEqual(with_disabled["pcb_manufacturing"]["enabled"], False)

    def test_fr4_exact_lookup_adds_converted_manufacturing_fee(self):
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertFalse(manufacturing["requires_manual_review"])
        expected_cny = round(row["jlc_price_cny"] * 1.1, 2)
        self.assertEqual(manufacturing["jlc_estimate_cny"], row["jlc_price_cny"])
        self.assertEqual(manufacturing["pricing_mode"], "exact_lookup")
        self.assertFalse(manufacturing["is_estimated"])
        self.assertEqual(manufacturing["customer_quote_cny"], expected_cny)
        self.assertEqual(manufacturing["customer_quote_krw"], round(expected_cny * 232.4))
        self.assertEqual(result["pcb_manufacturing_fee"], manufacturing["customer_quote_krw"])
        self.assertIn("PCB 样板制造费 / PCB sample fabrication", [row["label"] for row in result["breakdown"]])

    def test_fpc_exact_lookup_adds_fee(self):
        row = _manufacturing_row("fpc", 2, 100, 150, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fpc",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 150,
                "mfg_quantity": 20,
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertFalse(manufacturing["requires_manual_review"])
        self.assertEqual(manufacturing["jlc_estimate_cny"], row["jlc_price_cny"])
        self.assertEqual(manufacturing["customer_quote_cny"], round(row["jlc_price_cny"] * 1.1, 2))

    def test_fpc_one_layer_expanded_spec_adds_fee(self):
        row = _manufacturing_row("fpc", 1, 50, 50, 5)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fpc",
                "mfg_layers": 1,
                "mfg_width_mm": 50,
                "mfg_height_mm": 50,
                "mfg_quantity": 5,
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertFalse(manufacturing["requires_manual_review"])
        self.assertEqual(manufacturing["jlc_estimate_cny"], row["jlc_price_cny"])
        self.assertEqual(manufacturing["customer_quote_cny"], round(row["jlc_price_cny"] * 1.1, 2))

    def test_aluminum_exact_lookup_adds_fee(self):
        row = _manufacturing_row("aluminum", 1, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "aluminum",
                "mfg_layers": 1,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertFalse(manufacturing["requires_manual_review"])
        self.assertEqual(manufacturing["jlc_estimate_cny"], row["jlc_price_cny"])
        self.assertEqual(manufacturing["customer_quote_cny"], round(row["jlc_price_cny"] * 1.1, 2))

    def test_unknown_or_unmatched_spec_requires_manual_review_without_fee(self):
        baseline = calc_pcb(_base_inputs(), _params(), _tables())
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "copper",
                "mfg_layers": 1,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 5,
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertTrue(manufacturing["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertEqual(result["total"], baseline["total"])
        self.assertIn("该板材不在当前自动报价范围内", manufacturing["manual_review_reasons"])

    def test_pending_validation_requires_manual_review(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            {
                **_tables(),
                "manufacturing_price_meta": [
                    {
                        **PCB_MANUFACTURING_PRICE_META[0],
                        "validation_status": "pending_live_resample",
                    }
                ],
            },
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertTrue(manufacturing["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertIn("尚未通过 live 验证", manufacturing["manual_review_reasons"][0])

    def test_material_not_enabled_by_validation_requires_manual_review(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "aluminum",
                "mfg_layers": 1,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            {
                **_tables(),
                "manufacturing_price_meta": [
                    {
                        **PCB_MANUFACTURING_PRICE_META[0],
                        "validation_status": "passed",
                        "enabled_materials": ["fr4", "fpc"],
                    }
                ],
            },
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertTrue(manufacturing["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertIn("该材料当前未启用自动报价", manufacturing["manual_review_reasons"])

    def test_supported_material_unmatched_spec_uses_verified_estimate(self):
        for material, layers in (("fr4", 2), ("fpc", 1), ("aluminum", 1)):
            with self.subTest(material=material):
                result = calc_pcb(
                    {
                        **_base_inputs(),
                        "include_pcb_manufacturing": True,
                        "mfg_material": material,
                        "mfg_layers": layers,
                        "mfg_width_mm": 90,
                        "mfg_height_mm": 90,
                        "mfg_quantity": 10,
                    },
                    _params(),
                    _tables(),
                )
                manufacturing = result["pcb_manufacturing"]
                self.assertFalse(manufacturing["requires_manual_review"])
                self.assertEqual(manufacturing["pricing_mode"], "verified_estimate")
                self.assertTrue(manufacturing["is_estimated"])
                self.assertGreater(manufacturing["confidence"], 0)
                self.assertGreater(result["pcb_manufacturing_fee"], 0)

    def test_estimator_outside_jlc_supported_bounds_requires_manual_review(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 250,
                "mfg_height_mm": 100,
                "mfg_quantity": 10,
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertTrue(manufacturing["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertIn("超出 JLC 已确认支持范围", " ".join(manufacturing["manual_review_reasons"]))

    def test_estimator_disabled_material_requires_manual_review(self):
        tables = _tables()
        tables["manufacturing_price_meta"][0]["estimator_enabled_materials"] = ["fr4", "fpc"]
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "aluminum",
                "mfg_layers": 1,
                "mfg_width_mm": 90,
                "mfg_height_mm": 90,
                "mfg_quantity": 10,
            },
            _params(),
            tables,
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertTrue(manufacturing["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertIn("估算报价尚未通过验证", " ".join(manufacturing["manual_review_reasons"]))

    def test_standard_process_defaults_keep_v4_exact_price(self):
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertEqual(manufacturing["jlc_estimate_cny"], row["jlc_price_cny"])
        self.assertEqual(manufacturing["selected_process"]["board_thickness"], "1.6")
        self.assertFalse(manufacturing["process_adjusted"])
        self.assertEqual(manufacturing["pricing_mode"], "exact_lookup")

    def test_verified_process_adjustments_apply_after_exact_lookup(self):
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_board_thickness": "2.0",
                "mfg_solder_color": "红色",
                "mfg_surface_finish": "沉金",
                "mfg_copper_thickness": "2oz",
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        expected = round((((row["jlc_price_cny"] * 1.1) * 1.2) + 20) * 1.3, 2)
        self.assertFalse(manufacturing["requires_manual_review"])
        self.assertEqual(manufacturing["jlc_estimate_cny"], expected)
        self.assertTrue(manufacturing["process_adjusted"])
        self.assertTrue(manufacturing["is_estimated"])
        self.assertEqual(manufacturing["base_pricing_mode"], "exact_lookup")
        self.assertEqual(len(manufacturing["process_adjustments"]), 4)

    def test_unverified_process_value_requires_manual_review(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_solder_color": "荧光粉",
            },
            _params(),
            _tables(),
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertTrue(manufacturing["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertIn("solder_color", " ".join(manufacturing["manual_review_reasons"]))

    def test_disabled_material_process_model_requires_manual_review(self):
        tables = _tables()
        tables["manufacturing_price_meta"][0]["process_enabled_materials"] = ["fr4", "fpc"]
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "aluminum",
                "mfg_layers": 1,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_solder_color": "红色",
            },
            _params(),
            tables,
        )
        manufacturing = result["pcb_manufacturing"]
        self.assertTrue(manufacturing["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertIn("工艺调整尚未通过", " ".join(manufacturing["manual_review_reasons"]))


def _tables_v6():
    """v6 扩展 fixture：新增 solderMaskCoverage / panelDesignCount / OSP / interactions / risk_zones。"""
    tables = copy.deepcopy(_tables())
    meta = tables["manufacturing_price_meta"][0]
    process_model = meta["process_model"]

    fr4 = process_model["materials"]["fr4"]
    fr4["defaults"].update({
        "solderMaskCoverage": "过孔盖油",
        "panelDesignCount": "1",
    })
    # 扩展 surface_finish 选项：加入 OSP
    fr4["options"]["surfaceFinish"] = fr4["options"]["surfaceFinish"] + ["OSP"]
    fr4["options"].update({
        "solderMaskCoverage": ["过孔盖油", "非过孔盖油"],
        "panelDesignCount": ["1", "2"],
    })
    fr4["factors"]["surfaceFinish"]["OSP"] = {"method": "multiplier", "multiplier": 0.95}
    fr4["factors"]["solderMaskCoverage"] = {
        "过孔盖油": {"method": "multiplier", "multiplier": 1},
        "非过孔盖油": {"method": "multiplier", "multiplier": 1.15},
    }
    fr4["factors"]["panelDesignCount"] = {
        "1": {"method": "multiplier", "multiplier": 1},
        "2": {"method": "multiplier", "multiplier": 1.05},
    }

    # 交互修正：沉金 + 2oz 同时选中时额外 ×1.05
    process_model["interactions"] = {
        "fr4": [
            {
                "id": "sink_gold_2oz",
                "fields": {"surfaceFinish": "沉金", "copperThickness": "2oz"},
                "method": "multiplier",
                "multiplier": 1.05,
            }
        ]
    }

    # 同步更新 process_options（含 options 用于 _resolve_pcb_process_spec）
    meta["process_options"] = {
        key: {"defaults": mat["defaults"], "options": mat["options"]}
        for key, mat in process_model["materials"].items()
    }

    # 风险分区：4层 FR4 且面积 ≥ 10000 mm²（100×100）触发 manual_review
    meta["risk_zones"] = [
        {
            "id": "fr4_4layer_large_area",
            "material_key": "fr4",
            "layers": [4],
            "min_area_mm2": 10000,
            "action": "manual_review",
        }
    ]

    return tables


class PcbManufacturingQuoteV6Tests(unittest.TestCase):
    """V6 新字段：solderMaskCoverage / panelDesignCount / OSP / interactions / risk_zones / smt_required。"""

    def test_solder_mask_coverage_non_default_applies_process_adjustment(self):
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_solder_mask_coverage": "非过孔盖油",
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertTrue(mfg["process_adjusted"])
        expected = round(row["jlc_price_cny"] * 1.15, 2)
        self.assertEqual(mfg["jlc_estimate_cny"], expected)
        fields = [a["field"] for a in mfg["process_adjustments"]]
        self.assertIn("solder_mask_coverage", fields)

    def test_panel_design_count_non_default_applies_process_adjustment(self):
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_panel_design_count": "2",
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertTrue(mfg["process_adjusted"])
        expected = round(row["jlc_price_cny"] * 1.05, 2)
        self.assertEqual(mfg["jlc_estimate_cny"], expected)
        fields = [a["field"] for a in mfg["process_adjustments"]]
        self.assertIn("panel_design_count", fields)

    def test_osp_surface_finish_applies_process_adjustment(self):
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_surface_finish": "OSP",
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertTrue(mfg["process_adjusted"])
        expected = round(row["jlc_price_cny"] * 0.95, 2)
        self.assertEqual(mfg["jlc_estimate_cny"], expected)

    def test_interaction_correction_applies_on_sink_gold_2oz(self):
        """沉金 + 2oz 组合额外叠加 ×1.05 交互修正。"""
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_surface_finish": "沉金",
                "mfg_copper_thickness": "2oz",
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        # boardThickness=1.6(×1), solderColor=绿色(×1), surfaceFinish=沉金(+20),
        # copperThickness=2oz(×1.3), solderMaskCoverage=过孔盖油(×1), panelDesignCount=1(×1)
        # interaction sink_gold_2oz: ×1.05
        expected = round(((row["jlc_price_cny"] + 20) * 1.3) * 1.05, 2)
        self.assertEqual(mfg["jlc_estimate_cny"], expected)
        interaction_fields = [a["field"] for a in mfg["process_adjustments"]]
        self.assertTrue(any("interaction:" in f for f in interaction_fields))

    def test_invalid_solder_mask_coverage_requires_manual_review(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_solder_mask_coverage": "荧光橙",
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertTrue(mfg["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertIn("solder_mask_coverage", " ".join(mfg["manual_review_reasons"]))

    def test_risk_zone_triggers_manual_review_with_zero_fee(self):
        """4层 FR4 面积≥10000mm² 命中风险分区 → manual_review，制造费为 0。"""
        baseline = calc_pcb(_base_inputs(), _params(), _tables_v6())
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 4,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertTrue(mfg["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertEqual(result["total"], baseline["total"])
        self.assertIn("fr4_4layer_large_area", " ".join(mfg["manual_review_reasons"]))
        self.assertEqual(mfg["risk_zone"], "fr4_4layer_large_area")
        self.assertEqual(mfg["risk_status"], "manual_review")

    def test_smt_required_true_does_not_change_manufacturing_fee(self):
        """smt_required=True 时制造费不变，smt_price_included=False。"""
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        base_result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables_v6(),
        )
        smt_result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_smt_required": True,
            },
            _params(),
            _tables_v6(),
        )
        self.assertEqual(base_result["pcb_manufacturing_fee"], smt_result["pcb_manufacturing_fee"])
        self.assertTrue(smt_result["pcb_manufacturing"]["smt_required"])
        self.assertFalse(smt_result["pcb_manufacturing"]["smt_price_included"])

    def test_smt_required_false_behaves_same_as_default(self):
        """smt_required 缺省与 False 行为一致，smt_price_included 均为 False。"""
        result_default = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables_v6(),
        )
        result_false = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_smt_required": False,
            },
            _params(),
            _tables_v6(),
        )
        self.assertEqual(result_default["total"], result_false["total"])
        self.assertFalse(result_default["pcb_manufacturing"]["smt_required"])
        self.assertFalse(result_false["pcb_manufacturing"]["smt_required"])
        self.assertFalse(result_default["pcb_manufacturing"]["smt_price_included"])
        self.assertFalse(result_false["pcb_manufacturing"]["smt_price_included"])

    def test_legacy_request_without_new_fields_uses_defaults(self):
        """缺省 v6 新字段时，自动使用 process_options defaults，is_standard_process=True。"""
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertTrue(mfg["is_standard_process"])
        self.assertFalse(mfg["process_adjusted"])
        self.assertEqual(mfg["selected_process"].get("solder_mask_coverage"), "过孔盖油")
        self.assertEqual(mfg["selected_process"].get("panel_design_count"), "1")

    def test_standard_process_price_unchanged_without_new_v6_fields(self):
        """使用 v6 fixture 但不提供新字段时，价格与 v5 基准一致。"""
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertEqual(mfg["jlc_estimate_cny"], row["jlc_price_cny"])
        self.assertEqual(mfg["pricing_mode"], "exact_lookup")


def _tables_v7():
    """v7 fixture：scaleSegments + process_enabled_zones 局部放行，材料整体未启用。"""
    tables = copy.deepcopy(_tables_v6())
    meta = tables["manufacturing_price_meta"][0]
    meta["version"] = "jlc-cn-pcb-v7-test"
    meta["process_enabled_materials"] = ["aluminum"]
    meta["process_enabled_zones"] = [
        {
            "id": "fr4_surfaceFinish_OSP",
            "material_key": "fr4",
            "process_fields": {"surfaceFinish": ["OSP"]},
            "action": "auto_quote",
        },
        {
            "id": "fpc_boardThickness_0.20",
            "material_key": "fpc",
            "process_fields": {"boardThickness": ["0.20"]},
            "action": "auto_quote",
        },
    ]
    fr4 = meta["process_model"]["materials"]["fr4"]
    fr4["options"]["boardThickness"] = ["1.0", "1.6", "2.0"]
    fr4["factors"]["boardThickness"]["1.0"] = {
        "method": "multiplier",
        "multiplier": 0.95,
        "scaleSegments": {
            "small": {"method": "multiplier", "multiplier": 0.92},
            "mid": {"method": "multiplier", "multiplier": 0.95},
            "large": {"method": "multiplier", "multiplier": 0.98},
        },
    }
    fr4["factors"]["surfaceFinish"]["OSP"] = {
        "method": "multiplier",
        "multiplier": 0.95,
        "scaleSegments": {
            "small": {"method": "multiplier", "multiplier": 0.9},
            "mid": {"method": "multiplier", "multiplier": 0.95},
            "large": {"method": "multiplier", "multiplier": 0.97},
        },
    }
    fpc = meta["process_model"]["materials"]["fpc"]
    fpc["options"]["boardThickness"] = ["0.11", "0.12", "0.20"]
    fpc["factors"]["boardThickness"]["0.20"] = {
        "method": "multiplier",
        "multiplier": 1.08,
        "scaleSegments": {
            "small": {"method": "multiplier", "multiplier": 1.12},
            "mid": {"method": "multiplier", "multiplier": 1.08},
            "large": {"method": "multiplier", "multiplier": 1.05},
        },
    }
    meta["process_options"] = {
        key: {"defaults": mat["defaults"], "options": mat["options"]}
        for key, mat in meta["process_model"]["materials"].items()
    }
    meta["process_model"]["validationStatus"] = "partial_pass"
    meta["acceptance_status"] = "passed"
    meta["active_price_version"] = "jlc-cn-pcb-v7-test"
    meta["fallback_version"] = "jlc-cn-pcb-v6-20260712"
    meta["risk_zones"] = [
        {
            "id": "fr4_2l_large_high_qty",
            "material_key": "fr4",
            "layers": [2],
            "min_area_mm2": 14000,
            "min_quantity": 75,
            "action": "manual_review",
        },
        {
            "id": "aluminum_small_low_qty",
            "material_key": "aluminum",
            "layers": [1],
            "max_area_mm2": 7000,
            "max_quantity": 20,
            "action": "manual_review",
        },
    ]
    meta["estimator_guards"] = {"maxNeighborDistance": 0.85, "minLocalNeighbors": 2}
    return tables


def _tables_v9():
    tables = copy.deepcopy(_tables())
    rows = []
    for material_key, layers, floor in (("fr4", 2, 0), ("aluminum", 1, 120)):
        for width_mm, height_mm, quantity, price in (
            (80, 80, 10, floor + 80),
            (80, 80, 20, floor + 125),
            (100, 100, 10, floor + 110),
            (100, 100, 20, floor + 175),
        ):
            rows.append(
                {
                    "material_key": material_key,
                    "material_label": material_key,
                    "layers": layers,
                    "width_mm": width_mm,
                    "height_mm": height_mm,
                    "quantity": quantity,
                    "jlc_price_cny": price,
                    "enabled": True,
                }
            )
    tables["manufacturing_price_list"] = rows
    meta = tables["manufacturing_price_meta"][0]
    meta["acceptance_status"] = "passed"
    meta["risk_zones"] = []
    meta["estimator_enabled_materials"] = ["fr4", "aluminum"]
    meta["estimator"] = {
        "version": "jlc-cn-pcb-v9-material-estimator-test",
        "validationStatus": "passed",
        "neighbors": 6,
        "materials": {
            "fr4": {
                "modelType": "fr4_segmented",
                "layers": [2],
                "minWidthMm": 80,
                "maxWidthMm": 100,
                "minHeightMm": 80,
                "maxHeightMm": 100,
                "minQuantity": 10,
                "maxQuantity": 20,
                "guards": {
                    "maxNeighborDistance": 0.7,
                    "minLocalNeighbors": 2,
                    "areaWeight": 1,
                    "quantityWeight": 0.8,
                },
            },
            "aluminum": {
                "modelType": "aluminum_floor_area_quantity",
                "layers": [1],
                "minWidthMm": 80,
                "maxWidthMm": 100,
                "minHeightMm": 80,
                "maxHeightMm": 100,
                "minQuantity": 10,
                "maxQuantity": 20,
                "floorPriceCny": 120,
                "guards": {
                    "maxNeighborDistance": 0.65,
                    "minLocalNeighbors": 3,
                    "areaWeight": 1.15,
                    "quantityWeight": 0.95,
                    "areaExponent": 0.92,
                    "quantityExponent": 0.72,
                },
            },
        },
    }
    return tables


def _tables_v10():
    tables = copy.deepcopy(_tables())
    rows = []
    for layers, layer_base in ((1, 80), (2, 120)):
        for quantity, quantity_base in ((10, 20), (15, 28), (30, 45), (50, 62), (100, 90), (150, 118)):
            for width_mm, height_mm, area_add in ((70, 70, 15), (90, 90, 35), (110, 110, 60)):
                rows.append(
                    {
                        "material_key": "fpc",
                        "material_label": "FPC软板",
                        "layers": layers,
                        "width_mm": width_mm,
                        "height_mm": height_mm,
                        "quantity": quantity,
                        "jlc_price_cny": layer_base + quantity_base + area_add,
                        "enabled": True,
                    }
                )
    tables["manufacturing_price_list"] = rows
    meta = tables["manufacturing_price_meta"][0]
    meta["acceptance_status"] = "passed"
    meta["risk_zones"] = []
    meta["estimator_enabled_materials"] = ["fpc"]
    band = {
        "floorPriceCny": 80,
        "areaExponent": 0.85,
        "quantityExponent": 0.65,
        "maxNeighborDistance": 0.8,
        "minLocalNeighbors": 2,
        "neighbors": 6,
        "maxPredictionMultiplier": 2.5,
        "minPredictionMultiplier": 0.5,
        "maxLocalResidualRatio": 0.5,
    }
    meta["estimator"] = {
        "version": "jlc-cn-pcb-v10-material-estimator-test",
        "validationStatus": "passed",
        "neighbors": 6,
        "materials": {
            "fpc": {
                "modelType": "fpc_layered_floor_area_quantity",
                "layers": [1, 2],
                "minWidthMm": 70,
                "maxWidthMm": 110,
                "minHeightMm": 70,
                "maxHeightMm": 110,
                "minQuantity": 10,
                "maxQuantity": 150,
                "guards": {
                    "maxNeighborDistance": 0.8,
                    "minLocalNeighbors": 2,
                    "areaWeight": 1,
                    "quantityWeight": 0.7,
                },
                "layerQuantityBands": {
                    str(layers): {
                        quantity_band: {
                            **band,
                            "floorPriceCny": band["floorPriceCny"] + (40 if layers == 2 else 0),
                        }
                        for quantity_band in ("low", "medium", "high")
                    }
                    for layers in (1, 2)
                },
            }
        },
    }
    return tables


class PcbManufacturingQuoteV7Tests(unittest.TestCase):
    """V7：分段工艺系数、分区级放行、未覆盖组合降级、SMT 不改价。"""

    def test_fr4_enabled_zone_osp_auto_quotes_with_scale_segment(self):
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_surface_finish": "OSP",
            },
            _params(),
            _tables_v7(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertTrue(mfg["process_adjusted"])
        # 100x100=10000 → mid band ×0.95
        self.assertEqual(mfg["jlc_estimate_cny"], round(row["jlc_price_cny"] * 0.95, 2))
        self.assertEqual(mfg["process_adjustments"][0]["area_band"], "mid")

    def test_fr4_small_area_uses_small_scale_segment(self):
        row = _manufacturing_row("fr4", 2, 50, 50, 5)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 50,
                "mfg_height_mm": 50,
                "mfg_quantity": 5,
                "mfg_surface_finish": "OSP",
            },
            _params(),
            _tables_v7(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertEqual(mfg["jlc_estimate_cny"], round(row["jlc_price_cny"] * 0.9, 2))
        self.assertEqual(mfg["process_adjustments"][0]["area_band"], "small")

    def test_fpc_board_thickness_0_20_zone_auto_quotes(self):
        row = _manufacturing_row("fpc", 2, 100, 150, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fpc",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 150,
                "mfg_quantity": 20,
                "mfg_board_thickness": "0.20",
            },
            _params(),
            _tables_v7(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        # 15000 → mid ×1.08
        self.assertEqual(mfg["jlc_estimate_cny"], round(row["jlc_price_cny"] * 1.08, 2))

    def test_fr4_uncovered_process_combo_requires_manual_review(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_solder_color": "红色",
            },
            _params(),
            _tables_v7(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertTrue(mfg["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertIn("工艺调整尚未通过", " ".join(mfg["manual_review_reasons"]))

    def test_fr4_zone_plus_extra_uncovered_field_requires_manual_review(self):
        """OSP 分区不能连带放行未门禁的红色。"""
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_surface_finish": "OSP",
                "mfg_solder_color": "红色",
            },
            _params(),
            _tables_v7(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertTrue(mfg["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)

    def test_aluminum_fully_enabled_process_still_works(self):
        row = _manufacturing_row("aluminum", 1, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "aluminum",
                "mfg_layers": 1,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_solder_color": "红色",
            },
            _params(),
            _tables_v7(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertEqual(mfg["jlc_estimate_cny"], round(row["jlc_price_cny"] * 1.1, 2))

    def test_smt_required_does_not_change_v7_fee(self):
        base = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_surface_finish": "OSP",
            },
            _params(),
            _tables_v7(),
        )
        with_smt = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_surface_finish": "OSP",
                "mfg_smt_required": True,
            },
            _params(),
            _tables_v7(),
        )
        self.assertEqual(base["pcb_manufacturing_fee"], with_smt["pcb_manufacturing_fee"])
        self.assertFalse(with_smt["pcb_manufacturing"]["smt_price_included"])

    def test_v6_rollback_meta_still_quotes_standard_process(self):
        """回滚到仅含 v6 meta 时，标准工艺仍可报价。"""
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables_v6(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertEqual(mfg["jlc_estimate_cny"], row["jlc_price_cny"])


class PcbManufacturingQuoteV8Tests(unittest.TestCase):
    """V8：验收门禁、边界风险区、缺失 acceptance_status 兼容。"""

    def test_acceptance_failed_blocks_estimator_keeps_exact(self):
        tables = _tables()
        tables["manufacturing_price_meta"][0]["acceptance_status"] = "failed"
        exact = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            tables,
        )
        self.assertFalse(exact["pcb_manufacturing"]["requires_manual_review"])
        self.assertEqual(exact["pcb_manufacturing"]["pricing_mode"], "exact_lookup")

        estimated = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 90,
                "mfg_height_mm": 90,
                "mfg_quantity": 10,
            },
            _params(),
            tables,
        )
        self.assertTrue(estimated["pcb_manufacturing"]["requires_manual_review"])
        self.assertEqual(estimated["pcb_manufacturing_fee"], 0)
        self.assertIn("独立验收未通过", " ".join(estimated["pcb_manufacturing"]["manual_review_reasons"]))

    def test_acceptance_failed_blocks_nonstandard_process(self):
        tables = _tables_v7()
        tables["manufacturing_price_meta"][0]["acceptance_status"] = "failed"
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
                "mfg_surface_finish": "OSP",
            },
            _params(),
            tables,
        )
        self.assertTrue(result["pcb_manufacturing"]["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)

    def test_missing_acceptance_status_keeps_legacy_estimate(self):
        tables = _tables()
        tables["manufacturing_price_meta"][0].pop("acceptance_status", None)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 90,
                "mfg_height_mm": 90,
                "mfg_quantity": 10,
            },
            _params(),
            tables,
        )
        self.assertFalse(result["pcb_manufacturing"]["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing"]["pricing_mode"], "verified_estimate")

    def test_boundary_risk_zone_fr4_large_high_qty(self):
        tables = _tables_v7()
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 150,
                "mfg_quantity": 100,
            },
            _params(),
            tables,
        )
        mfg = result["pcb_manufacturing"]
        self.assertTrue(mfg["requires_manual_review"])
        self.assertEqual(mfg["risk_zone"], "fr4_2l_large_high_qty")
        self.assertEqual(result["pcb_manufacturing_fee"], 0)

    def test_boundary_risk_zone_aluminum_small_low_qty(self):
        tables = _tables_v7()
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "aluminum",
                "mfg_layers": 1,
                "mfg_width_mm": 50,
                "mfg_height_mm": 50,
                "mfg_quantity": 5,
            },
            _params(),
            tables,
        )
        mfg = result["pcb_manufacturing"]
        self.assertTrue(mfg["requires_manual_review"])
        self.assertEqual(mfg["risk_zone"], "aluminum_small_low_qty")
        self.assertEqual(result["pcb_manufacturing_fee"], 0)

    def test_acceptance_status_exposed_on_result(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables(),
        )
        self.assertEqual(result["pcb_manufacturing"]["acceptance_status"], "passed")
        self.assertEqual(result["pcb_manufacturing"]["fallback_version"], "jlc-cn-pcb-v6-20260712")


class PcbManufacturingQuoteV9Tests(unittest.TestCase):
    def test_fr4_segmented_estimator(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 90,
                "mfg_height_mm": 90,
                "mfg_quantity": 15,
            },
            _params(),
            _tables_v9(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertEqual(mfg["pricing_mode"], "verified_estimate")
        self.assertEqual(mfg["estimator_model_type"], "fr4_segmented")
        self.assertGreaterEqual(mfg["estimator_local_coverage"], 2)

    def test_aluminum_floor_area_quantity_estimator(self):
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "aluminum",
                "mfg_layers": 1,
                "mfg_width_mm": 90,
                "mfg_height_mm": 90,
                "mfg_quantity": 15,
            },
            _params(),
            _tables_v9(),
        )
        mfg = result["pcb_manufacturing"]
        self.assertFalse(mfg["requires_manual_review"])
        self.assertEqual(mfg["estimator_model_type"], "aluminum_floor_area_quantity")
        self.assertGreaterEqual(mfg["jlc_estimate_cny"], 120)

    def test_v9_low_coverage_returns_manual_review(self):
        tables = _tables_v9()
        tables["manufacturing_price_meta"][0]["estimator"]["materials"]["aluminum"]["guards"][
            "minLocalNeighbors"
        ] = 8
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "aluminum",
                "mfg_layers": 1,
                "mfg_width_mm": 90,
                "mfg_height_mm": 90,
                "mfg_quantity": 15,
            },
            _params(),
            tables,
        )
        self.assertTrue(result["pcb_manufacturing"]["requires_manual_review"])


class PcbManufacturingQuoteV10Tests(unittest.TestCase):
    def _quote(self, *, layers=1, width=85, height=85, quantity=40, tables=None):
        return calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fpc",
                "mfg_layers": layers,
                "mfg_width_mm": width,
                "mfg_height_mm": height,
                "mfg_quantity": quantity,
            },
            _params(),
            tables or _tables_v10(),
        )["pcb_manufacturing"]

    def test_fpc_layered_floor_area_quantity_estimator(self):
        one_layer = self._quote(layers=1)
        two_layer = self._quote(layers=2)
        self.assertFalse(one_layer["requires_manual_review"])
        self.assertFalse(two_layer["requires_manual_review"])
        self.assertEqual(
            one_layer["estimator_model_type"],
            "fpc_layered_floor_area_quantity",
        )
        self.assertGreater(two_layer["jlc_estimate_cny"], one_layer["jlc_estimate_cny"])

    def test_fpc_model_is_monotonic_by_area_and_quantity(self):
        small = self._quote(width=80, height=80, quantity=40)
        large = self._quote(width=100, height=100, quantity=40)
        low_quantity = self._quote(width=90, height=90, quantity=35)
        high_quantity = self._quote(width=90, height=90, quantity=65)
        self.assertGreater(large["jlc_estimate_cny"], small["jlc_estimate_cny"])
        self.assertGreater(high_quantity["jlc_estimate_cny"], low_quantity["jlc_estimate_cny"])

    def test_fpc_low_coverage_returns_manual_review(self):
        tables = _tables_v10()
        bands = tables["manufacturing_price_meta"][0]["estimator"]["materials"]["fpc"][
            "layerQuantityBands"
        ]
        bands["1"]["medium"]["minLocalNeighbors"] = 20
        result = self._quote(tables=tables)
        self.assertTrue(result["requires_manual_review"])


def _tables_v11_fr4():
    tables = copy.deepcopy(_tables())
    rows = []
    for layers, layer_base in ((2, 100), (4, 180)):
        for quantity, quantity_base in ((5, 10), (10, 18), (20, 30), (50, 55), (100, 85)):
            for width_mm, height_mm, area_add in ((70, 70, 12), (90, 90, 28), (110, 110, 55)):
                rows.append(
                    {
                        "material_key": "fr4",
                        "material_label": "FR-4",
                        "layers": layers,
                        "width_mm": width_mm,
                        "height_mm": height_mm,
                        "quantity": quantity,
                        "jlc_price_cny": layer_base + quantity_base + area_add,
                        "enabled": True,
                    }
                )
    tables["manufacturing_price_list"] = rows
    meta = tables["manufacturing_price_meta"][0]
    meta["acceptance_status"] = "passed"
    meta["quote_range_rate"] = 0.20
    meta["risk_zones"] = []
    meta["estimator_enabled_materials"] = ["fr4"]
    band = {
        "floorPriceCny": 90,
        "areaExponent": 0.85,
        "quantityExponent": 0.65,
        "maxNeighborDistance": 0.8,
        "minLocalNeighbors": 2,
        "neighbors": 6,
        "maxPredictionMultiplier": 2.5,
        "minPredictionMultiplier": 0.5,
        "maxLocalResidualRatio": 0.5,
    }
    meta["estimator"] = {
        "version": "jlc-cn-pcb-v11-material-estimator-test",
        "validationStatus": "passed",
        "neighbors": 6,
        "materials": {
            "fr4": {
                "modelType": "fr4_layered_floor_area_quantity",
                "layers": [2, 4],
                "minWidthMm": 70,
                "maxWidthMm": 110,
                "minHeightMm": 70,
                "maxHeightMm": 110,
                "minQuantity": 5,
                "maxQuantity": 100,
                "guards": {
                    "maxNeighborDistance": 0.8,
                    "minLocalNeighbors": 2,
                    "areaWeight": 1,
                    "quantityWeight": 0.7,
                },
                "layerQuantityBands": {
                    str(layers): {
                        quantity_band: {
                            **band,
                            "floorPriceCny": band["floorPriceCny"] + (80 if layers == 4 else 0),
                        }
                        for quantity_band in ("low", "medium", "high")
                    }
                    for layers in (2, 4)
                },
            }
        },
    }
    return tables


class PcbManufacturingQuoteV11Tests(unittest.TestCase):
    def test_auto_quote_exposes_plus_minus_20_percent_range(self):
        row = _manufacturing_row("fr4", 2, 100, 100, 20)
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 100,
                "mfg_height_mm": 100,
                "mfg_quantity": 20,
            },
            _params(),
            _tables(),
        )
        mfg = result["pcb_manufacturing"]
        mid_cny = round(row["jlc_price_cny"] * 1.1, 2)
        mid_krw = round(mid_cny * 232.4)
        self.assertEqual(mfg["pricing_display_mode"], "range")
        self.assertEqual(mfg["quote_range_rate"], 0.20)
        self.assertEqual(mfg["customer_quote_cny"], mid_cny)
        self.assertEqual(mfg["customer_quote_cny_min"], round(mid_cny * 0.8, 2))
        self.assertEqual(mfg["customer_quote_cny_max"], round(mid_cny * 1.2, 2))
        self.assertEqual(mfg["customer_quote_krw_min"], round(mid_krw * 0.8))
        self.assertEqual(mfg["customer_quote_krw_max"], round(mid_krw * 1.2))
        self.assertEqual(result["pcb_manufacturing_fee"], mid_krw)
        self.assertEqual(result["pcb_manufacturing_fee_min"], round(mid_krw * 0.8))
        self.assertEqual(result["pcb_manufacturing_fee_max"], round(mid_krw * 1.2))
        fixed = result["total"] - mid_krw
        self.assertEqual(result["total_min"], fixed + result["pcb_manufacturing_fee_min"])
        self.assertEqual(result["total_max"], fixed + result["pcb_manufacturing_fee_max"])
        self.assertLessEqual(result["total_min"], result["total"])
        self.assertLessEqual(result["total"], result["total_max"])

    def test_manual_review_has_no_price_range(self):
        tables = _tables()
        tables["manufacturing_price_meta"][0]["acceptance_status"] = "failed"
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 90,
                "mfg_height_mm": 90,
                "mfg_quantity": 10,
            },
            _params(),
            tables,
        )
        mfg = result["pcb_manufacturing"]
        self.assertTrue(mfg["requires_manual_review"])
        self.assertEqual(mfg["pricing_display_mode"], "manual")
        self.assertIsNone(mfg["customer_quote_cny_min"])
        self.assertEqual(result["pcb_manufacturing_fee"], 0)
        self.assertEqual(result["total_min"], result["total"])
        self.assertEqual(result["total_max"], result["total"])

    def test_fr4_layered_floor_area_quantity_estimator(self):
        two_layer = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 85,
                "mfg_height_mm": 85,
                "mfg_quantity": 25,
            },
            _params(),
            _tables_v11_fr4(),
        )["pcb_manufacturing"]
        four_layer = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 4,
                "mfg_width_mm": 85,
                "mfg_height_mm": 85,
                "mfg_quantity": 25,
            },
            _params(),
            _tables_v11_fr4(),
        )["pcb_manufacturing"]
        self.assertFalse(two_layer["requires_manual_review"])
        self.assertTrue(two_layer["is_estimated"])
        self.assertEqual(two_layer["estimator_model_type"], "fr4_layered_floor_area_quantity")
        self.assertEqual(two_layer["pricing_display_mode"], "range")
        self.assertGreater(four_layer["jlc_estimate_cny"], two_layer["jlc_estimate_cny"])

    def test_honesty_risk_zone_forces_manual_review(self):
        tables = _tables_v11_fr4()
        tables["manufacturing_price_meta"][0]["risk_zones"] = [
            {
                "id": "v11_honesty_fr4_L2_medium_medium_test",
                "material_key": "fr4",
                "layers": [2],
                "min_area_mm2": 6000,
                "max_area_mm2": 16000,
                "min_quantity": 20,
                "max_quantity": 75,
                "action": "manual_review",
                "reason": "v11_quote_range_honesty_guard",
            }
        ]
        result = calc_pcb(
            {
                **_base_inputs(),
                "include_pcb_manufacturing": True,
                "mfg_material": "fr4",
                "mfg_layers": 2,
                "mfg_width_mm": 85,
                "mfg_height_mm": 85,
                "mfg_quantity": 25,
            },
            _params(),
            tables,
        )
        self.assertTrue(result["pcb_manufacturing"]["requires_manual_review"])
        self.assertEqual(result["pcb_manufacturing"]["pricing_display_mode"], "manual")
        self.assertEqual(result["pcb_manufacturing_fee"], 0)


if __name__ == "__main__":
    unittest.main()
