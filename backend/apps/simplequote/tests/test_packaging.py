"""packaging 模块单元测试。"""

from django.test import SimpleTestCase, TestCase

from apps.simplequote.board_allowances import resolve_board_allowances
from apps.simplequote.dieline_import import default_mapping_schema
from apps.simplequote.fefco_catalog import build_fefco_catalog, get_box_template
from apps.simplequote.models import DielineCategory, DielineTemplate, DielineTemplateAsset
from apps.simplequote.packaging import (
    PaperBoxGeometryError,
    size_triple_from_manufacturing,
    unfold_by_code,
    unfold_size_0201,
)
from apps.simplequote.serializers import DielineTemplateSerializer
from core.exceptions import AppAPIException

PARAMETRIC_PARSED_GEOMETRY = {
    "schema_version": 1,
    "source_format": "svg",
    "unit": "mm",
    "bbox": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 50},
    "width": 100,
    "height": 50,
    "entities": [
        {
            "entity_id": "svg_00001",
            "type": "line",
            "role": "cut",
            "x1": 0,
            "y1": 0,
            "x2": 100,
            "y2": 0,
        },
        {
            "entity_id": "svg_00002",
            "type": "line",
            "role": "crease",
            "x1": 100,
            "y1": 0,
            "x2": 100,
            "y2": 50,
        },
    ],
}

BASE_DIMENSIONS = {"length": 100, "width": 80, "height": 50, "thickness": 1.5}


def create_mapped_template(
    code,
    category,
    *,
    engine_key="slotted_rsc",
    quote_enabled=True,
    preview_enabled=True,
    is_active=True,
    default_glue_tab_mm=25,
    **extra,
):
    defaults = {
        "category": category,
        "category_code": category.code,
        "engine_key": engine_key,
        "default_length_mm": 200,
        "default_width_mm": 150,
        "default_height_mm": 100,
        "default_manufacturing_length_mm": 200,
        "default_manufacturing_width_mm": 150,
        "default_manufacturing_height_mm": 100,
        "default_internal_length_mm": 198,
        "default_internal_width_mm": 148,
        "default_internal_height_mm": 96,
        "default_external_length_mm": 202,
        "default_external_width_mm": 152,
        "default_external_height_mm": 104,
        "default_thickness_mm": 1.5,
        "default_glue_tab_mm": default_glue_tab_mm,
        "quote_enabled": quote_enabled,
        "preview_enabled": preview_enabled,
        "is_active": is_active,
        "sort_order": 1,
    }
    defaults.update(extra)
    template = DielineTemplate.objects.create(code=code, **defaults)
    mapping_schema = default_mapping_schema(PARAMETRIC_PARSED_GEOMETRY, BASE_DIMENSIONS)
    DielineTemplateAsset.objects.create(
        template=template,
        source_format="svg",
        parsed_geometry=PARAMETRIC_PARSED_GEOMETRY,
        mapping_schema=mapping_schema,
        base_dimensions=BASE_DIMENSIONS,
        mapping_status="mapped",
        is_active=True,
        version=1,
    )
    return template


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
    @classmethod
    def setUpTestData(cls):
        cls.cat0200 = DielineCategory.objects.create(
            code="0200",
            name_i18n={"zh": "开槽箱"},
            sort_order=20,
        )
        cls.cat0400 = DielineCategory.objects.create(
            code="0400",
            name_i18n={"zh": "翻盖箱"},
            sort_order=40,
        )
        cls.template0201 = create_mapped_template("0201", cls.cat0200, sort_order=1)
        cls.template0427 = create_mapped_template(
            "0427",
            cls.cat0400,
            engine_key="mailer_folder",
            material_type="white_card",
            flute_type="none",
            sort_order=2,
        )
        DielineTemplate.objects.create(
            code="DRAFT01",
            category=cls.cat0200,
            category_code="0200",
            engine_key="slotted_rsc",
            quote_enabled=False,
            preview_enabled=False,
            is_active=False,
            sort_order=99,
        )

    def test_catalog_reads_db_templates(self):
        catalog = build_fefco_catalog()
        self.assertEqual(len(catalog["templates"]), 2)
        tpl = get_box_template("0201")
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl["engine_key"], "slotted_rsc")
        self.assertIsNotNone(tpl["active_parametric_asset"])

    def test_catalog_categories_from_db(self):
        catalog = build_fefco_catalog()
        codes = {c["code"] for c in catalog["categories"]}
        self.assertIn("0200", codes)
        self.assertIn("0400", codes)
        self.assertTrue(any(c.get("name_i18n") for c in catalog["categories"]))

    def test_catalog_template_triple_dimensions(self):
        tpl = get_box_template("0201")
        self.assertIsNotNone(tpl["default_manufacturing_length_mm"])
        self.assertIsNotNone(tpl["default_internal_length_mm"])
        self.assertIsNotNone(tpl["default_external_length_mm"])

    def test_catalog_only_lists_mapped_asset_templates(self):
        catalog = build_fefco_catalog()
        codes = {t["code"] for t in catalog["templates"]}
        self.assertIn("0201", codes)
        self.assertIn("0427", codes)
        self.assertNotIn("DRAFT01", codes)

    def test_unfold_by_code_uses_parametric_bbox(self):
        result = unfold_by_code("0427", 315, 202, 62, thickness_mm=1.5, dimension_type="manufacturing")
        self.assertEqual(result["box_code"], "0427")
        self.assertEqual(result["blank_width_mm"], 315.0)
        self.assertEqual(result["blank_height_mm"], 62.0)
        self.assertAlmostEqual(result["unfold_area_m2"], 0.01953, places=5)

    def test_unfold_by_code_parametric_legacy_dims(self):
        result = unfold_by_code("0427", 200, 150, 100)
        self.assertEqual(result["box_code"], "0427")
        self.assertAlmostEqual(result["blank_width_mm"], 201.5, places=1)
        self.assertGreater(result["unfold_area_m2"], 0)

    def test_unfold_by_code_without_asset_rejected(self):
        cat = DielineCategory.objects.create(code="0700", name_i18n={"zh": "插舌盒"}, sort_order=70)
        DielineTemplate.objects.create(
            code="0713",
            category=cat,
            category_code="0700",
            engine_key="tuck_end",
            quote_enabled=True,
            preview_enabled=True,
            is_active=True,
            sort_order=3,
        )
        with self.assertRaises(PaperBoxGeometryError):
            unfold_by_code("0713", 200, 150, 100, dimension_type="manufacturing")

    def test_unfold_by_code_unsupported(self):
        with self.assertRaises(PaperBoxGeometryError):
            unfold_by_code("9999", 200, 150, 100)

    def test_unfold_uses_template_glue_tab(self):
        create_mapped_template(
            "0201A",
            self.cat0200,
            default_glue_tab_mm=30,
            sort_order=10,
        )
        result = unfold_by_code("0201A", 434, 214, 278, thickness_mm=3, dimension_type="manufacturing")
        self.assertEqual(result["box_code"], "0201A")
        self.assertEqual(result["engine_key"], "slotted_rsc")
        self.assertEqual(result["glue_tab_mm"], 30)
        self.assertEqual(result["blank_width_mm"], 434.0)
        self.assertEqual(result["blank_height_mm"], 278.0)

    def test_unfold_template_dimension_limits(self):
        cat = DielineCategory.objects.create(code="0700", name_i18n={"zh": "插舌盒"}, sort_order=70)
        create_mapped_template(
            "0713LIM",
            cat,
            engine_key="tuck_end",
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
        self.assertEqual(result["blank_width_mm"], 200.0)
        self.assertEqual(result["blank_height_mm"], 100.0)


class DielineTemplateSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = DielineCategory.objects.create(
            code="0200",
            name_i18n={"zh": "开槽箱"},
            sort_order=20,
        )

    def test_enable_without_asset_rejected(self):
        template = DielineTemplate.objects.create(
            code="NOASSET",
            category=self.category,
            category_code="0200",
            engine_key="slotted_rsc",
            quote_enabled=False,
            preview_enabled=False,
            is_active=False,
            sort_order=1,
        )
        serializer = DielineTemplateSerializer(
            instance=template,
            data={"is_active": True},
            partial=True,
        )
        with self.assertRaises(AppAPIException) as ctx:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(ctx.exception.default_code, "DIELINE_TEMPLATE_ASSET_REQUIRED")

    def test_enable_with_mapped_asset_allowed(self):
        template = create_mapped_template(
            "WITHASSET",
            self.category,
            is_active=False,
            preview_enabled=False,
            quote_enabled=False,
            sort_order=2,
        )
        serializer = DielineTemplateSerializer(
            instance=template,
            data={"is_active": True, "preview_enabled": True, "quote_enabled": True},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(raise_exception=True))
