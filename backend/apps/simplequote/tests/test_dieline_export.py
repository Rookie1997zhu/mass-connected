"""Unit tests for dieline PDF/AI export and fixed-asset normalization."""

from django.test import SimpleTestCase

from apps.simplequote.dieline_export import (
    drawable_segment_kinds,
    effective_bbox,
    normalize_fixed_segments,
    segments_to_ai_bytes,
    segments_to_pdf_bytes,
)


SAMPLE_SEGMENTS = [
    {"x1": 0, "y1": 0, "x2": 100, "y2": 0, "kind": "cut"},
    {"x1": 100, "y1": 0, "x2": 100, "y2": 50, "kind": "cut"},
    {"x1": 10, "y1": 10, "x2": 90, "y2": 10, "kind": "crease"},
    {"x1": -5, "y1": -5, "x2": 105, "y2": -5, "kind": "bleed"},
    {"x1": -5, "y1": -5, "x2": -5, "y2": 55, "kind": "bleed"},
]


class DielineExportPdfAiTests(SimpleTestCase):
    def test_drawable_kinds_include_bleed(self):
        self.assertEqual(drawable_segment_kinds(SAMPLE_SEGMENTS), ["bleed", "crease", "cut"])

    def test_pdf_and_ai_are_pdf_compatible(self):
        pdf = segments_to_pdf_bytes(SAMPLE_SEGMENTS)
        ai = segments_to_ai_bytes(SAMPLE_SEGMENTS)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertTrue(ai.startswith(b"%PDF"))
        # reportlab embeds unique doc IDs per call; payload size should match
        self.assertEqual(len(pdf), len(ai))
        self.assertEqual(drawable_segment_kinds(SAMPLE_SEGMENTS), ["bleed", "crease", "cut"])

    def test_pdf_bbox_includes_bleed(self):
        min_x, min_y, max_x, max_y = effective_bbox(SAMPLE_SEGMENTS, exclude_kinds=())
        self.assertEqual(min_x, -5)
        self.assertEqual(min_y, -5)
        self.assertEqual(max_x, 105)
        self.assertEqual(max_y, 55)

    def test_normalize_fixed_segments_translates_to_origin(self):
        entities = [
            {"role": "ignore", "x1": 0, "y1": 0, "x2": 500, "y2": 0},
            {"role": "cut", "x1": 200, "y1": 300, "x2": 250, "y2": 300},
            {"role": "bleed", "x1": 190, "y1": 290, "x2": 260, "y2": 290},
            {"role": "crease", "x1": 210, "y1": 320, "x2": 240, "y2": 320},
        ]
        segs = normalize_fixed_segments(entities)
        kinds = {s["kind"] for s in segs}
        self.assertEqual(kinds, {"cut", "bleed", "crease"})
        min_x, min_y, max_x, max_y = effective_bbox(segs, exclude_kinds=())
        self.assertAlmostEqual(min_x, 0.0)
        self.assertAlmostEqual(min_y, 0.0)
        self.assertGreater(max_x, 0)
        self.assertGreater(max_y, 0)
        # cut segment relative coords
        cut = next(s for s in segs if s["kind"] == "cut")
        self.assertAlmostEqual(cut["x1"], 10.0)
        self.assertAlmostEqual(cut["y1"], 10.0)
