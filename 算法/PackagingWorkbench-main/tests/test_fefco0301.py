# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the FEFCO 0301 tray and lid features."""

import os
import sys
import types
import unittest

ADDON_ROOT = os.path.dirname(os.path.dirname(__file__))


class _Q:
    def __init__(self, value):
        self.Value = float(value)


class _FakeFeature:
    def __init__(self):
        object.__setattr__(self, "_types", {})
        object.__setattr__(self, "_vals", {})
        object.__setattr__(self, "Shape", None)
        object.__setattr__(self, "Proxy", None)

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
            return _Q(vals[name]) if "Length" in prop_type else vals[name]
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

    sys.modules["FreeCADGui"] = gui
    sys.modules["FreeCAD"] = app
    sys.modules["Part"] = part
    return gui, registered


class FEFCO0301Test(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        for name in list(sys.modules):
            if name in ("PackagingWB",) or name.startswith(("commands", "objects")):
                sys.modules.pop(name, None)
        self.gui, self.registered = _install_mocks()

    def test_modules_import(self):
        from objects.box_fefco0301_lid import LidFEFCO0301
        from objects.box_fefco0301_tray import TrayFEFCO0301

        self.assertTrue(callable(TrayFEFCO0301))
        self.assertTrue(callable(LidFEFCO0301))

    def test_tray_defaults(self):
        from objects.box_fefco0301_tray import TrayFEFCO0301

        obj = _FakeFeature()
        TrayFEFCO0301(obj)
        self.assertEqual(obj.Length.Value, 200.0)
        self.assertEqual(obj.Width.Value, 150.0)
        self.assertEqual(obj.Height.Value, 60.0)
        self.assertEqual(obj.Thickness.Value, 3.0)
        self.assertEqual(obj.Allowance.Value, 1.0)

    def test_lid_defaults(self):
        from objects.box_fefco0301_lid import LidFEFCO0301

        obj = _FakeFeature()
        LidFEFCO0301(obj)
        self.assertEqual(obj.Length.Value, 201.0)
        self.assertEqual(obj.Width.Value, 151.0)
        self.assertEqual(obj.Height.Value, 25.0)

    def test_tray_execute_builds_nine_panels(self):
        from objects.box_fefco0301_tray import TrayFEFCO0301

        obj = _FakeFeature()
        proxy = TrayFEFCO0301(obj)
        proxy.execute(obj)
        kind, solids = obj.Shape
        self.assertEqual(kind, "compound")
        self.assertEqual(len(solids), 9)  # bottom + 4 walls + 4 flaps

    def test_lid_execute_builds_nine_panels(self):
        from objects.box_fefco0301_lid import LidFEFCO0301

        obj = _FakeFeature()
        proxy = LidFEFCO0301(obj)
        proxy.execute(obj)
        kind, solids = obj.Shape
        self.assertEqual(kind, "compound")
        self.assertEqual(len(solids), 9)  # roof + 4 walls + 4 flaps

    def test_command_registered(self):
        from PackagingWB import PackagingWorkbenchManager

        ids = PackagingWorkbenchManager().register_commands()
        self.assertIn("Packaging_FEFCO0301", ids)
        self.assertIn("Packaging_FEFCO0301", self.registered)
        # Order: FEFCO 0301 comes before the dieline command.
        self.assertLess(ids.index("Packaging_FEFCO0301"), ids.index("Packaging_GenerateDieline"))


if __name__ == "__main__":
    unittest.main()
