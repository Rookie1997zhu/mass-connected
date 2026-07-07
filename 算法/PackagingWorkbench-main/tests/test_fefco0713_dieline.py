# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the FEFCO 0713 tuck-end flat dieline generator."""

import os
import sys
import types
import unittest

ADDON_ROOT = os.path.dirname(os.path.dirname(__file__))


class _Q:
    def __init__(self, value):
        self.Value = float(value)


class _FakeView:
    def __init__(self):
        self.LineColor = None
        self.DrawStyle = None


class _FakeLine:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        self.ViewObject = _FakeView()
        self.Label = ""


class _FakeGroup:
    def __init__(self, label):
        self.Label = label
        self.Name = label
        self.ViewObject = None
        self._children = []

    @property
    def Group(self):
        return self._children

    def addObject(self, obj):
        self._children.append(obj)
        return obj


class _FakeDoc:
    def addObject(self, type_, name):
        return _FakeGroup(name)

    def recompute(self):
        pass


class _FakeBox:
    def __init__(self):
        self.Document = _FakeDoc()
        self.Name = "BoxFEFCO0713"
        self.Length = _Q(50.0)
        self.Width = _Q(30.0)
        self.Height = _Q(150.0)
        self.Thickness = _Q(1.5)
        self.GlueFlapWidth = _Q(12.0)
        self.TuckLength = _Q(25.0)


def _install_mocks():
    app = types.ModuleType("FreeCAD")
    app.Vector = lambda x=0.0, y=0.0, z=0.0: (float(x), float(y), float(z))
    draft = types.ModuleType("Draft")
    draft.make_line = lambda p1, p2: _FakeLine(p1, p2)
    draft.make_wire = lambda pts, closed=False: _FakeLine(pts[0], pts[-1])
    sys.modules["FreeCAD"] = app
    sys.modules["Draft"] = draft


def _points(group):
    pts = []
    for line in group.Group:
        pts.extend([line.p1, line.p2])
    return pts


class FEFCO0713DielineTest(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        for name in list(sys.modules):
            if name.startswith(("utils", "objects")):
                sys.modules.pop(name, None)
        _install_mocks()

    def _generate(self):
        from objects import fefco0713_dieline
        from utils import die_lines
        from utils.die_lines import DielineLayer

        main = fefco0713_dieline.generate(_FakeBox())
        cut = die_lines.get_layer_group(main, DielineLayer.CUT)
        crease = die_lines.get_layer_group(main, DielineLayer.CREASE)
        perf = die_lines.get_layer_group(main, DielineLayer.PERFORATION)
        return main, cut, crease, perf

    def test_structure_and_counts(self):
        main, cut, crease, perf = self._generate()
        self.assertEqual(len(main.Group), 3)
        self.assertGreaterEqual(len(cut.Group), 4)
        self.assertGreaterEqual(len(crease.Group), 5)
        self.assertEqual(len(cut.Group), 28)
        self.assertEqual(len(crease.Group), 12)
        self.assertEqual(len(perf.Group), 0)

    def test_bounding_box(self):
        length, width, height, glue, tuck = 50.0, 30.0, 150.0, 12.0, 25.0
        _, cut, crease, _ = self._generate()
        pts = _points(cut) + _points(crease)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.assertAlmostEqual(max(xs) - min(xs), 2 * length + 2 * width + glue, places=3)
        self.assertAlmostEqual(max(ys) - min(ys), height + 2 * width + 2 * tuck, places=3)


if __name__ == "__main__":
    unittest.main()
