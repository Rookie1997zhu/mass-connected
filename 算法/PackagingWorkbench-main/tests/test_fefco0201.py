# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the FEFCO 0201 parametric box feature.

FreeCAD's ``FreeCAD``, ``Part`` and ``FreeCADGui`` modules are mocked so the
feature logic can be exercised under a plain Python interpreter. Real geometry
validity (face count, bounding box) is checked by the in-FreeCAD probe.
"""

import os
import sys
import types
import unittest

ADDON_ROOT = os.path.dirname(os.path.dirname(__file__))


class _Q:
    """Minimal stand-in for an App::PropertyLength quantity."""

    def __init__(self, value):
        self.Value = float(value)

    def __float__(self):
        return self.Value


class _FakeFeature:
    """Mimics a Part::FeaturePython document object for property handling."""

    def __init__(self):
        object.__setattr__(self, "_types", {})
        object.__setattr__(self, "_vals", {})
        object.__setattr__(self, "Shape", None)
        object.__setattr__(self, "Proxy", None)
        object.__setattr__(self, "ViewObject", None)

    @property
    def PropertiesList(self):
        return list(self._vals.keys())

    def addProperty(self, prop_type, name, group="", doc=""):
        self._types[name] = prop_type
        self._vals[name] = 0.0
        return self

    def __getattr__(self, name):
        vals = object.__getattribute__(self, "_vals")
        if name in vals:
            prop_type = object.__getattribute__(self, "_types")[name]
            value = vals[name]
            return _Q(value) if "Length" in prop_type else value
        raise AttributeError(name)

    def __setattr__(self, name, value):
        vals = self.__dict__.get("_vals")
        if vals is not None and name in vals:
            vals[name] = value
        else:
            object.__setattr__(self, name, value)


def _install_mocks():
    registered = {}

    gui = types.ModuleType("FreeCADGui")
    gui.addCommand = lambda cmd_id, obj: registered.__setitem__(cmd_id, obj)
    gui.SendMsgToActiveView = lambda *a, **k: None

    app = types.ModuleType("FreeCAD")
    app.Vector = lambda x=0.0, y=0.0, z=0.0: (x, y, z)
    app.ActiveDocument = None
    app.newDocument = lambda *a, **k: None

    part = types.ModuleType("Part")
    part.makeBox = lambda dx, dy, dz, vec=None: ("box", dx, dy, dz, vec)
    part.makeCompound = lambda solids: ("compound", list(solids))

    sys.modules["FreeCAD"] = app
    sys.modules["FreeCADGui"] = gui
    sys.modules["Part"] = part
    return gui, registered


class FEFCO0201Test(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        for name in list(sys.modules):
            if name in ("PackagingWB",) or name.startswith(("commands", "objects")):
                sys.modules.pop(name, None)
        self.gui, self.registered = _install_mocks()

    def test_module_imports(self):
        from objects.box_fefco0201 import BoxFEFCO0201

        self.assertTrue(callable(BoxFEFCO0201))

    def test_property_defaults(self):
        from objects.box_fefco0201 import BoxFEFCO0201

        obj = _FakeFeature()
        BoxFEFCO0201(obj)
        self.assertEqual(obj.Length.Value, 200.0)
        self.assertEqual(obj.Width.Value, 150.0)
        self.assertEqual(obj.Height.Value, 100.0)
        self.assertEqual(obj.Thickness.Value, 3.0)
        self.assertEqual(obj.Allowance.Value, 1.0)
        self.assertIs(obj.Proxy.__class__, BoxFEFCO0201)

    def test_execute_builds_twelve_panels(self):
        from objects.box_fefco0201 import BoxFEFCO0201

        obj = _FakeFeature()
        proxy = BoxFEFCO0201(obj)
        proxy.execute(obj)
        self.assertIsNotNone(obj.Shape)
        kind, solids = obj.Shape
        self.assertEqual(kind, "compound")
        self.assertEqual(len(solids), 12)  # 4 walls + 4 top + 4 bottom flaps

    def test_flaps_are_inset_to_avoid_corner_overlap(self):
        from objects.box_fefco0201 import BoxFEFCO0201

        length, width, thickness = 200.0, 150.0, 3.0
        flap_len = length - 4 * thickness   # 188
        flap_wid = width - 4 * thickness    # 138
        flap_depth = width / 2.0            # 75

        obj = _FakeFeature()
        proxy = BoxFEFCO0201(obj)
        proxy.execute(obj)
        # Each panel from the mock is ("box", dx, dy, dz, origin).
        boxes = obj.Shape[1]
        dims = [(b[1], b[2]) for b in boxes]  # (dx, dy)

        # Length-direction flaps: dx == flap_len, dy == flap_depth.
        self.assertEqual(sum(1 for dx, dy in dims if dx == flap_len and dy == flap_depth), 4)
        # Width-direction flaps: dx == flap_depth, dy == flap_wid.
        self.assertEqual(sum(1 for dx, dy in dims if dx == flap_depth and dy == flap_wid), 4)
        # No flap spans the full outer length any more (that was the overlap bug).
        self.assertEqual(sum(1 for dx, dy in dims if dx == length + 2 * thickness
                             and dy == flap_depth), 0)

    def test_view_provider_icon_exists(self):
        from objects.view_provider import BoxViewProvider

        vobj = types.SimpleNamespace(Proxy=None, Object=None)
        vp = BoxViewProvider(vobj)
        icon = vp.getIcon()
        self.assertTrue(os.path.isfile(icon), f"icon missing: {icon}")

    def test_serialization_returns_none(self):
        from objects.box_fefco0201 import BoxFEFCO0201

        obj = _FakeFeature()
        proxy = BoxFEFCO0201(obj)
        self.assertIsNone(proxy.dumps())
        self.assertIsNone(proxy.loads(None))
        self.assertIsNone(proxy.__getstate__())
        self.assertIsNone(proxy.__setstate__(None))

    def test_command_registered_via_manager(self):
        from PackagingWB import PackagingWorkbenchManager

        ids = PackagingWorkbenchManager().register_commands()
        # Later steps add more commands; assert FEFCO 0201 is present and after Hello Box.
        self.assertIn("Packaging_FEFCO0201", ids)
        self.assertIn("Packaging_HelloBox", ids)
        self.assertLess(ids.index("Packaging_HelloBox"), ids.index("Packaging_FEFCO0201"))
        self.assertIn("Packaging_FEFCO0201", self.registered)


if __name__ == "__main__":
    unittest.main()
