from pathlib import Path
import tempfile
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.simplequote.dieline_import import (
    DielineImportError,
    default_mapping_schema,
    parse_dxf,
    parse_svg,
    parse_uploaded_dieline,
    render_parametric_dieline,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


class DielineImportTests(SimpleTestCase):
    def test_parse_svg_lines_to_geometry(self):
        result = parse_svg(FIXTURE_DIR / "sample_dieline.svg")

        self.assertEqual(result["source_format"], "svg")
        self.assertEqual(len(result["entities"]), 3)
        self.assertEqual(result["bbox"]["max_x"], 100)
        self.assertEqual(result["bbox"]["max_y"], 50)
        roles = [entity["role"] for entity in result["entities"]]
        self.assertEqual(roles, ["cut", "crease", "crease"])

    def test_parse_dxf_lines_to_geometry(self):
        result = parse_dxf(FIXTURE_DIR / "sample_dieline.dxf")

        self.assertEqual(result["source_format"], "dxf")
        self.assertEqual(len(result["entities"]), 2)
        self.assertEqual(result["bbox"]["max_x"], 100)
        self.assertEqual(result["bbox"]["max_y"], 50)
        roles = [entity["role"] for entity in result["entities"]]
        self.assertEqual(roles, ["cut", "crease"])

    def test_parse_svg_style_and_dasharray_to_roles(self):
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">
          <g stroke="blue">
            <line x1="0" y1="0" x2="100" y2="0" />
          </g>
          <line x1="0" y1="10" x2="100" y2="10" style="stroke:red;stroke-dasharray:8 4" />
          <line id="bleed-guide" x1="0" y1="20" x2="100" y2="20" stroke="green" />
        </svg>
        """
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", encoding="utf-8", delete=False) as tmp:
            tmp.write(svg)
            tmp_path = tmp.name
        try:
            result = parse_svg(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        roles = [entity["role"] for entity in result["entities"]]
        self.assertEqual(roles, ["cut", "crease", "bleed"])
        self.assertTrue(all(entity["role_confidence"] > 0.7 for entity in result["entities"]))

    def test_ai_pdf_are_attachment_only_for_parametric_parse(self):
        with self.assertRaises(DielineImportError):
            parse_uploaded_dieline(SimpleNamespace(chunks=lambda: []), "pdf")

    def test_render_parametric_dieline_scales_from_mapping(self):
        parsed = {
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
                    "bbox": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 0},
                },
                {
                    "entity_id": "svg_00002",
                    "type": "line",
                    "role": "crease",
                    "x1": 100,
                    "y1": 0,
                    "x2": 100,
                    "y2": 50,
                    "bbox": {"min_x": 100, "min_y": 0, "max_x": 100, "max_y": 50},
                },
            ],
        }
        base_dimensions = {"length": 100, "width": 80, "height": 50, "thickness": 1.5}
        asset = SimpleNamespace(
            source_format="svg",
            parsed_geometry=parsed,
            mapping_schema=default_mapping_schema(parsed, base_dimensions),
            base_dimensions=base_dimensions,
        )

        result = render_parametric_dieline(asset, {"length": 200, "width": 80, "height": 100})

        self.assertEqual(result["width"], 200)
        self.assertEqual(result["height"], 100)
        self.assertAlmostEqual(result["area_m2"], 0.02)
