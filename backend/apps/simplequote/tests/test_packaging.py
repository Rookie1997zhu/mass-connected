"""packaging 模块单元测试。"""

from django.test import SimpleTestCase

from apps.simplequote.packaging import PaperBoxGeometryError, unfold_by_code, unfold_size_0201


class UnfoldSize0201Tests(SimpleTestCase):
    def test_standard_case_200x150x100(self):
        result = unfold_size_0201(200, 150, 100, thickness_mm=1.5, dimension_type="internal")
        self.assertEqual(result["blank_width_mm"], 725.0)  # 2*(200+150)+25
        self.assertEqual(result["blank_height_mm"], 350.0)  # 150+2*100
        self.assertAlmostEqual(result["unfold_area_m2"], 0.25375, places=5)

    def test_external_dimension_conversion(self):
        internal = unfold_size_0201(200, 150, 100, thickness_mm=2, dimension_type="internal")
        external = unfold_size_0201(204, 154, 104, thickness_mm=2, dimension_type="external")
        self.assertEqual(internal["blank_width_mm"], external["blank_width_mm"])
        self.assertEqual(internal["blank_height_mm"], external["blank_height_mm"])

    def test_invalid_dimensions(self):
        with self.assertRaises(PaperBoxGeometryError):
            unfold_size_0201(5, 150, 100)

    def test_unfold_by_code_0427(self):
        result = unfold_by_code("0427", 200, 150, 100)
        self.assertEqual(result["box_code"], "0427")
        self.assertGreater(result["unfold_area_m2"], 0)

    def test_unfold_by_code_unsupported(self):
        with self.assertRaises(PaperBoxGeometryError):
            unfold_by_code("0301", 200, 150, 100)
