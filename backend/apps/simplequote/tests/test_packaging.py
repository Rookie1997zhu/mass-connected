"""packaging 模块单元测试。"""

from django.test import SimpleTestCase

from apps.simplequote.fefco_catalog import build_fefco_catalog
from apps.simplequote.packaging import (
    PaperBoxGeometryError,
    size_triple_from_manufacturing,
    unfold_by_code,
    unfold_size_0201,
)


class UnfoldSize0201Tests(SimpleTestCase):
    def test_standard_case_200x150x100(self):
        result = unfold_size_0201(200, 150, 100, thickness_mm=1.5, dimension_type="internal")
        self.assertEqual(result["blank_width_mm"], 733.0)  # mfg 202+152 → 2*(202+152)+25
        self.assertEqual(result["blank_height_mm"], 256.0)  # mfg H 104 + W 152
        self.assertAlmostEqual(result["unfold_area_m2"], 0.187648, places=5)

    def test_external_dimension_conversion(self):
        internal = unfold_size_0201(200, 150, 100, thickness_mm=2, dimension_type="internal")
        external = unfold_size_0201(204, 154, 108, thickness_mm=2, dimension_type="external")
        self.assertEqual(internal["blank_width_mm"], external["blank_width_mm"])
        self.assertEqual(internal["blank_height_mm"], external["blank_height_mm"])

    def test_reference_0201_size_triple(self):
        result = unfold_size_0201(434, 214, 278, thickness_mm=3, dimension_type="manufacturing")
        sizes = size_triple_from_manufacturing(
            result["manufacturing_length_mm"],
            result["manufacturing_width_mm"],
            result["manufacturing_height_mm"],
            3,
        )
        self.assertEqual(sizes["internal"]["length_mm"], 430.0)
        self.assertEqual(sizes["internal"]["width_mm"], 210.0)
        self.assertEqual(sizes["internal"]["height_mm"], 270.0)
        self.assertEqual(sizes["external"]["length_mm"], 436.0)
        self.assertEqual(sizes["external"]["width_mm"], 216.0)
        self.assertEqual(sizes["external"]["height_mm"], 282.0)

    def test_invalid_dimensions(self):
        with self.assertRaises(PaperBoxGeometryError):
            unfold_size_0201(5, 150, 100)

    def test_unfold_by_code_0427(self):
        result = unfold_by_code("0427", 315, 202, 62, thickness_mm=1.5, dimension_type="manufacturing")
        self.assertEqual(result["box_code"], "0427")
        self.assertEqual(result["blank_width_mm"], 719.0)  # L + 2W
        self.assertAlmostEqual(result["blank_height_mm"], 588.5, places=1)  # 2H + 2W + tuck
        self.assertGreater(result["unfold_area_m2"], 0)

    def test_unfold_by_code_0427_legacy_dims(self):
        result = unfold_by_code("0427", 200, 150, 100)
        self.assertEqual(result["box_code"], "0427")
        self.assertEqual(result["blank_width_mm"], 506.0)  # 内尺寸换算后 mfg 202+2*152
        self.assertGreater(result["unfold_area_m2"], 0)

    def test_fefco_catalog_four_templates(self):
        catalog = build_fefco_catalog()
        self.assertEqual(len(catalog["templates"]), 4)
        self.assertEqual(len(catalog["categories"]), 3)
        self.assertEqual(set(catalog["by_category"].keys()), {"0200", "0400", "0700"})

    def test_unfold_by_code_unsupported(self):
        with self.assertRaises(PaperBoxGeometryError):
            unfold_by_code("9999", 200, 150, 100)
