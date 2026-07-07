# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the reusable dieline layer helpers (utils/die_lines.py)."""

import os
import sys
import types
import unittest

ADDON_ROOT = os.path.dirname(os.path.dirname(__file__))


class _FakeView:
    def __init__(self):
        self.LineColor = None
        self.DrawStyle = None


class _FakeLine:
    def __init__(self):
        self.ViewObject = _FakeView()
        self.Label = ""


class _FakeGroup:
    def __init__(self, label="", name=""):
        self.Label = label
        self.Name = name or label
        self.ViewObject = None
        self._children = []

    @property
    def Group(self):
        return self._children

    def addObject(self, obj):
        self._children.append(obj)
        return obj


class _FakeDoc:
    def __init__(self):
        self.created = []

    def addObject(self, type_, name):
        group = _FakeGroup(label=name, name=name)
        self.created.append(group)
        return group


def _install_mocks():
    app = types.ModuleType("FreeCAD")
    app.Vector = lambda x=0.0, y=0.0, z=0.0: (float(x), float(y), float(z))

    draft = types.ModuleType("Draft")
    draft.make_line = lambda p1, p2: _FakeLine()
    draft.make_wire = lambda pts, closed=False: _FakeLine()

    sys.modules["FreeCAD"] = app
    sys.modules["Draft"] = draft


class DieLinesTest(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        for name in list(sys.modules):
            if name in ("utils", "utils.die_lines"):
                sys.modules.pop(name, None)
        _install_mocks()

    def test_layer_definitions(self):
        from utils.die_lines import DielineLayer

        self.assertEqual(DielineLayer.CUT.name, "Cut")
        self.assertEqual(DielineLayer.CUT.color, (1.0, 0.0, 0.0))
        self.assertEqual(DielineLayer.CUT.draw_style, "Solid")
        self.assertEqual(DielineLayer.CREASE.name, "Crease")
        self.assertEqual(DielineLayer.CREASE.color, (0.0, 0.0, 1.0))
        self.assertEqual(DielineLayer.CREASE.draw_style, "Dashed")
        self.assertEqual(DielineLayer.PERFORATION.name, "Perforation")
        self.assertEqual(DielineLayer.PERFORATION.color, (0.0, 0.7, 0.0))
        self.assertEqual(DielineLayer.PERFORATION.draw_style, "Dotted")
        self.assertEqual(len(DielineLayer.all()), 3)

    def test_create_dieline_group(self):
        from utils import die_lines

        doc = _FakeDoc()
        main = die_lines.create_dieline_group(doc, "Box")
        self.assertTrue(main.Label.endswith("_Dieline"))
        self.assertEqual(len(main.Group), 3)
        self.assertEqual([g.Label for g in main.Group], ["Cut", "Crease", "Perforation"])

    def test_add_line_applies_layer_style(self):
        from utils import die_lines

        cut_group = _FakeGroup(label="Cut")
        line = die_lines.add_line(cut_group, (0, 0, 0), (10, 0, 0))
        self.assertIn(line, cut_group.Group)
        self.assertEqual(line.ViewObject.LineColor, (1.0, 0.0, 0.0))
        self.assertEqual(line.ViewObject.DrawStyle, "Solid")

    def test_get_layer_group(self):
        from utils import die_lines
        from utils.die_lines import DielineLayer

        doc = _FakeDoc()
        main = die_lines.create_dieline_group(doc, "Box")
        crease = die_lines.get_layer_group(main, DielineLayer.CREASE)
        self.assertIsNotNone(crease)
        self.assertEqual(crease.Label, "Crease")

    def test_for_label_handles_freecad_suffix(self):
        # A second dieline in the same document gets auto-suffixed labels.
        from utils.die_lines import DielineLayer

        self.assertIs(DielineLayer.for_label("Cut009"), DielineLayer.CUT)
        self.assertIs(DielineLayer.for_label("Crease009"), DielineLayer.CREASE)
        self.assertIs(DielineLayer.for_label("Perforation001"), DielineLayer.PERFORATION)

    def test_get_layer_group_with_suffixed_labels(self):
        from utils import die_lines
        from utils.die_lines import DielineLayer

        main = _FakeGroup(label="X_Dieline")
        main.addObject(_FakeGroup(label="Cut009"))
        main.addObject(_FakeGroup(label="Crease009"))
        main.addObject(_FakeGroup(label="Perforation001"))
        crease = die_lines.get_layer_group(main, DielineLayer.CREASE)
        self.assertIsNotNone(crease)
        self.assertEqual(crease.Label, "Crease009")

    def test_add_line_styles_suffixed_group(self):
        from utils import die_lines

        crease = _FakeGroup(label="Crease009")
        line = die_lines.add_line(crease, (0, 0, 0), (1, 0, 0))
        self.assertEqual(line.ViewObject.LineColor, (0.0, 0.0, 1.0))
        self.assertEqual(line.ViewObject.DrawStyle, "Dashed")


if __name__ == "__main__":
    unittest.main()
