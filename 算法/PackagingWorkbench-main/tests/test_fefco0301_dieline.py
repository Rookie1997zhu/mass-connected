# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the FEFCO 0301 tray/lid flat dieline generator."""

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


class _FakeFeature:
    def __init__(self, name, length, width, height, thickness=3.0):
        self.Document = _FakeDoc()
        self.Name = name
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


def _points(group):
    pts = []
    for line in group.Group:
        pts.extend([line.p1, line.p2])
    return pts


class FEFCO0301DielineTest(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        for name in list(sys.modules):
            if name.startswith(("utils", "objects")):
                sys.modules.pop(name, None)
        _install_mocks()

    def _layers(self, main):
        from utils import die_lines
        from utils.die_lines import DielineLayer

        return (
            die_lines.get_layer_group(main, DielineLayer.CUT),
            die_lines.get_layer_group(main, DielineLayer.CREASE),
            die_lines.get_layer_group(main, DielineLayer.PERFORATION),
        )

    def test_generate_tray_structure_and_counts(self):
        from objects import fefco0301_dieline

        tray = _FakeFeature("BoxFEFCO0301_Tray", 200.0, 150.0, 60.0)
        main = fefco0301_dieline.generate_tray(tray)
        cut, crease, perf = self._layers(main)
        self.assertEqual(len(main.Group), 3)
        self.assertGreaterEqual(len(cut.Group), 4)
        self.assertGreaterEqual(len(crease.Group), 5)
        self.assertEqual(len(cut.Group), 20)  # 2 walls + 6 side walls + 12 flap edges
        self.assertEqual(len(crease.Group), 8)  # 4 bottom + 4 wall/flap folds
        self.assertEqual(len(perf.Group), 0)

    def test_generate_lid_structure(self):
        from objects import fefco0301_dieline

        lid = _FakeFeature("BoxFEFCO0301_Lid", 201.0, 151.0, 25.0)
        main = fefco0301_dieline.generate_lid(lid)
        cut, crease, _ = self._layers(main)
        self.assertEqual(len(cut.Group), 20)
        self.assertEqual(len(crease.Group), 8)

    def test_tray_bounding_box(self):
        from objects import fefco0301_dieline

        length, width, height = 200.0, 150.0, 60.0
        tray = _FakeFeature("BoxFEFCO0301_Tray", length, width, height)
        main = fefco0301_dieline.generate_tray(tray)
        cut, crease, _ = self._layers(main)
        pts = _points(cut) + _points(crease)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.assertAlmostEqual(max(xs) - min(xs), length + 2 * height, places=3)
        self.assertAlmostEqual(max(ys) - min(ys), width + 2 * height, places=3)


if __name__ == "__main__":
    unittest.main()
