"""packaging 模块单元测试。"""

from django.test import SimpleTestCase, TestCase

from apps.simplequote.board_allowances import resolve_board_allowances
from apps.simplequote.fefco_catalog import build_fefco_catalog, get_box_template
from apps.simplequote.models import DielineCategory, DielineTemplate
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


class BoardAllowancesTests(SimpleTestCase):
    def test_flute_allowances_differ(self):
        e_allow = resolve_board_allowances(1.5, flute_type="e")
        b_allow = resolve_board_allowances(3, flute_type="b")
        self.assertLess(e_allow["internal_lw"], b_allow["internal_lw"])
        self.assertLess(e_allow["internal_h"], b_allow["internal_h"])

    def test_template_allowances_override(self):
        allow = resolve_board_allowances(
            3,
            flute_type="b",
            template_allowances={
                "internal_lw": 5,
                "internal_h": 9,
                "external_lw": 2.5,
                "external_h": 4.5,
            },
        )
        self.assertEqual(allow["internal_lw"], 5)
        self.assertEqual(allow["external_h"], 4.5)


class DielineTemplateCatalogTests(TestCase):
    def test_catalog_reads_db_templates(self):
        catalog = build_fefco_catalog()
        self.assertGreaterEqual(len(catalog["templates"]), 4)
        self.assertGreaterEqual(len(catalog["categories"]), 3)
        tpl = get_box_template("0201")
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl["engine_key"], "slotted_rsc")

    def test_catalog_categories_from_db(self):
        catalog = build_fefco_catalog()
        codes = {c["code"] for c in catalog["categories"]}
        self.assertIn("0200", codes)
        self.assertTrue(any(c.get("name_i18n") for c in catalog["categories"]))

    def test_catalog_template_triple_dimensions(self):
        tpl = get_box_template("0201")
        self.assertIsNotNone(tpl["default_manufacturing_length_mm"])
        self.assertIsNotNone(tpl["default_internal_length_mm"])
        self.assertIsNotNone(tpl["default_external_length_mm"])

    def test_fefco_catalog_five_templates(self):
        catalog = build_fefco_catalog()
        self.assertGreaterEqual(len(catalog["templates"]), 5)
        self.assertGreaterEqual(len(catalog["categories"]), 3)
        self.assertIn("0200", catalog["by_category"])
        slotted = catalog["by_category"]["0200"]
        self.assertGreaterEqual(len(slotted), 2)
        codes = {t["code"] for t in slotted}
        self.assertIn("0201", codes)
        self.assertIn("0210", codes)

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

    def test_unfold_by_code_0210_folding_shipping(self):
        result = unfold_by_code("0210", 354, 354, 208, thickness_mm=3, dimension_type="manufacturing")
        self.assertEqual(result["box_code"], "0210")
        self.assertEqual(result["engine_key"], "folding_shipping")
        self.assertEqual(result["blank_width_mm"], 1441.0)  # 2*(354+354)+25
        self.assertEqual(result["blank_height_mm"], 562.0)  # 208+354

    def test_unfold_by_code_unsupported(self):
        with self.assertRaises(PaperBoxGeometryError):
            unfold_by_code("9999", 200, 150, 100)

    def test_unfold_uses_template_engine_key(self):
        cat = DielineCategory.objects.get(code="0200")
        DielineTemplate.objects.create(
            code="0201A",
            category=cat,
            category_code="0200",
            engine_key="slotted_rsc",
            default_length_mm=200,
            default_width_mm=150,
            default_height_mm=100,
            default_manufacturing_length_mm=200,
            default_manufacturing_width_mm=150,
            default_manufacturing_height_mm=100,
            default_internal_length_mm=198,
            default_internal_width_mm=148,
            default_internal_height_mm=96,
            default_external_length_mm=202,
            default_external_width_mm=152,
            default_external_height_mm=104,
            default_thickness_mm=1.5,
            default_glue_tab_mm=30,
            sort_order=99,
        )
        result = unfold_by_code("0201A", 434, 214, 278, thickness_mm=3, dimension_type="manufacturing")
        self.assertEqual(result["box_code"], "0201A")
        self.assertEqual(result["engine_key"], "slotted_rsc")
        self.assertEqual(result["glue_tab_mm"], 30)

    def test_unfold_template_dimension_limits(self):
        cat = DielineCategory.objects.get(code="0700")
        DielineTemplate.objects.create(
            code="0713LIM",
            category=cat,
            category_code="0700",
            engine_key="tuck_end",
            default_length_mm=200,
            default_width_mm=150,
            default_height_mm=100,
            default_manufacturing_length_mm=200,
            default_manufacturing_width_mm=150,
            default_manufacturing_height_mm=100,
            default_internal_length_mm=198,
            default_internal_width_mm=148,
            default_internal_height_mm=96,
            default_external_length_mm=202,
            default_external_width_mm=152,
            default_external_height_mm=104,
            min_length_mm=100,
            max_length_mm=300,
            min_width_mm=80,
            max_width_mm=250,
            min_height_mm=50,
            max_height_mm=200,
            material_type="white_card",
            flute_type="none",
            sort_order=199,
        )
        with self.assertRaises(PaperBoxGeometryError):
            unfold_by_code("0713LIM", 50, 150, 100, dimension_type="manufacturing")
        with self.assertRaises(PaperBoxGeometryError):
            unfold_by_code("0713LIM", 350, 150, 100, dimension_type="manufacturing")
        result = unfold_by_code("0713LIM", 200, 150, 100, dimension_type="manufacturing")
        self.assertEqual(result["box_code"], "0713LIM")
