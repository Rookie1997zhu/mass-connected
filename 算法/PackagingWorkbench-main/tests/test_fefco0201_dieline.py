# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the FEFCO 0201 flat dieline generator."""

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
    def __init__(self, length=200.0, width=150.0, height=100.0, thickness=3.0):
        self.Document = _FakeDoc()
        self.Name = "BoxFEFCO0201"
        self.Length = _Q(length)
        self.Width = _Q(width)
        self.Height = _Q(height)
        self.Thickness = _Q(thickness)


def _install_mocks():
    app = types.ModuleType("FreeCAD")
    app.Vector = lambda x=0.0, y=0.0, z=0.0: (float(x), float(y), float(z))
    draft = types.ModuleType("Draft")
    draft.make_line = lambda p1, p2: _FakeLine(p1, p2)
    draft.make_wire = lambda pts, closed=False: _FakeLine(pts[0], pts[-1])
    sys.modules["FreeCAD"] = app
    sys.modules["Draft"] = draft


def _all_points(group):
    pts = []
    for line in group.Group:
        pts.append(line.p1)
        pts.append(line.p2)
    return pts


class FEFCO0201DielineTest(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        for name in list(sys.modules):
            if name.startswith(("utils", "objects")):
                sys.modules.pop(name, None)
        _install_mocks()

    def _generate(self, **kw):
        from objects import fefco0201_dieline
        from utils import die_lines
        from utils.die_lines import DielineLayer

        main = fefco0201_dieline.generate(_FakeBox(**kw))
        cut = die_lines.get_layer_group(main, DielineLayer.CUT)
        crease = die_lines.get_layer_group(main, DielineLayer.CREASE)
        perf = die_lines.get_layer_group(main, DielineLayer.PERFORATION)
        return main, cut, crease, perf

    def test_group_structure(self):
        main, cut, crease, perf = self._generate()
        self.assertTrue(main.Label.endswith("_Dieline"))
        self.assertEqual(len(main.Group), 3)
        self.assertIsNotNone(cut)
        self.assertIsNotNone(crease)
        self.assertIsNotNone(perf)
        self.assertEqual(len(perf.Group), 0)  # perforation empty for FEFCO 0201

    def test_line_counts(self):
        _, cut, crease, _ = self._generate()
        self.assertGreaterEqual(len(cut.Group), 4)
        self.assertGreaterEqual(len(crease.Group), 5)
        self.assertEqual(len(cut.Group), 14)  # 8 perimeter + 6 slits
        self.assertEqual(len(crease.Group), 6)  # 4 vertical + 2 horizontal

    def test_bounding_box(self):
        length, width, height, tab = 200.0, 150.0, 100.0, 30.0
        _, cut, crease, _ = self._generate(length=length, width=width, height=height)
        pts = _all_points(cut) + _all_points(crease)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox_w = max(xs) - min(xs)
        bbox_h = max(ys) - min(ys)
        self.assertAlmostEqual(bbox_w, 2 * length + 2 * width + tab, places=3)
        self.assertAlmostEqual(bbox_h, height + width, places=3)


if __name__ == "__main__":
    unittest.main()
