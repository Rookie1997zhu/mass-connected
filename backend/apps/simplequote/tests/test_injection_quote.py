"""注塑自动报价：单价公式与运输费估算单元测试。"""

import unittest

from apps.simplequote.calculator import DEFAULT_PARAMS, calc_injection


def _params():
    return dict(DEFAULT_PARAMS["injection"])


def _part(material="ABS", color="transparent", weight_g=0.8, quantity=1000):
    return {
        "material": material,
        "color": color,
        "weight_g": weight_g,
        "cavity": 1,
        "slider_count": 0,
        "quantity": quantity,
    }


class InjectionUnitPriceTests(unittest.TestCase):
    def test_abs_transparent_under_1g(self):
        result = calc_injection({"parts": [_part(weight_g=0.8)]}, _params())
        part = result["parts"][0]
        self.assertEqual(part["material_cost"], 0)
        self.assertAlmostEqual(part["unit_price"], 0.1903, places=3)
        self.assertAlmostEqual(result["production_fee"], part["after_color"], places=4)

    def test_pc_transparent_5_8g(self):
        result = calc_injection(
            {"parts": [_part(material="PC", weight_g=5.8)]},
            _params(),
        )
        part = result["parts"][0]
        self.assertAlmostEqual(part["material_cost"], 0.2088, places=4)
        self.assertAlmostEqual(part["unit_price"], 0.5286, places=3)

    def test_shipping_with_bbox_air_tier(self):
        result = calc_injection(
            {
                "parts": [_part(weight_g=600, quantity=1)],
                "bbox_mm": [200, 200, 100],
                "shipping_mode": "air",
            },
            _params(),
        )
        self.assertIsNotNone(result["shipping_fee"])
        self.assertIsNotNone(result["shipping"])
        self.assertEqual(result["shipping"]["mode"], "air")
        self.assertGreater(result["shipping"]["fee_krw"], 0)
        self.assertGreater(result["total"], result["mold_fee"] + result["product_total"])

    def test_shipping_weight_only(self):
        result = calc_injection(
            {"parts": [_part(weight_g=500, quantity=2)]},
            _params(),
        )
        self.assertIsNotNone(result["shipping_fee"])

    def test_no_weight_skips_shipping(self):
        result = calc_injection({"parts": [_part(weight_g=0)]}, _params())
        self.assertIsNone(result["shipping_fee"])
        self.assertIsNone(result["shipping"])


if __name__ == "__main__":
    unittest.main()
