# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the FEFCO 0713 tuck-end carton feature."""

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


class FEFCO0713Test(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        for name in list(sys.modules):
            if name in ("PackagingWB",) or name.startswith(("commands", "objects")):
                sys.modules.pop(name, None)
        self.gui, self.registered = _install_mocks()

    def test_module_imports(self):
        from objects.box_fefco0713 import BoxFEFCO0713

        self.assertTrue(callable(BoxFEFCO0713))

    def test_property_defaults(self):
        from objects.box_fefco0713 import BoxFEFCO0713

        obj = _FakeFeature()
        BoxFEFCO0713(obj)
        self.assertEqual(obj.Length.Value, 50.0)
        self.assertEqual(obj.Width.Value, 30.0)
        self.assertEqual(obj.Height.Value, 150.0)
        self.assertEqual(obj.GlueFlapWidth.Value, 12.0)
        self.assertEqual(obj.TuckLength.Value, 25.0)
        self.assertEqual(obj.Thickness.Value, 1.5)
        self.assertEqual(obj.Allowance.Value, 0.5)

    def test_execute_builds_thirteen_panels(self):
        from objects.box_fefco0713 import BoxFEFCO0713

        obj = _FakeFeature()
        proxy = BoxFEFCO0713(obj)
        proxy.execute(obj)
        kind, solids = obj.Shape
        self.assertEqual(kind, "compound")
        # 4 walls + glue + (cover + 2 dust + tuck) x 2
        self.assertEqual(len(solids), 13)

    def test_command_registered(self):
        from PackagingWB import PackagingWorkbenchManager

        ids = PackagingWorkbenchManager().register_commands()
        self.assertIn("Packaging_FEFCO0713", ids)
        self.assertIn("Packaging_FEFCO0713", self.registered)
        self.assertLess(ids.index("Packaging_FEFCO0713"), ids.index("Packaging_GenerateDieline"))


if __name__ == "__main__":
    unittest.main()
