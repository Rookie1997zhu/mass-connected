# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the Generate Dieline command."""

import os
import sys
import types
import unittest

ADDON_ROOT = os.path.dirname(os.path.dirname(__file__))


class _Q:
    def __init__(self, value):
        self.Value = float(value)


class _FakeFeature:
    """Minimal Part::FeaturePython stand-in for building a real proxy."""

    def __init__(self):
        object.__setattr__(self, "_types", {})
        object.__setattr__(self, "_vals", {})
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


class _Selection:
    def __init__(self):
        self._sel = []

    def set(self, objs):
        self._sel = objs

    def getSelection(self):
        return self._sel


def _install_mocks():
    registered = {}
    selection = _Selection()

    gui = types.ModuleType("FreeCADGui")
    gui.addCommand = lambda cmd_id, obj: registered.__setitem__(cmd_id, obj)
    gui.SendMsgToActiveView = lambda *a, **k: None
    gui.Selection = selection

    app = types.ModuleType("FreeCAD")
    app.ActiveDocument = None
    app.newDocument = lambda *a, **k: None

    sys.modules["FreeCADGui"] = gui
    sys.modules["FreeCAD"] = app
    return gui, registered, selection


class GenerateDielineCmdTest(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        for name in list(sys.modules):
            if name in ("PackagingWB",) or name.startswith(("commands", "objects", "utils")):
                sys.modules.pop(name, None)
        self.gui, self.registered, self.selection = _install_mocks()

    def _make_box_object(self):
        from objects.box_fefco0201 import BoxFEFCO0201

        proxy = BoxFEFCO0201(_FakeFeature())
        return types.SimpleNamespace(Proxy=proxy, Name="BoxFEFCO0201")

    def _make_tray_object(self):
        from objects.box_fefco0301_tray import TrayFEFCO0301

        proxy = TrayFEFCO0301(_FakeFeature())
        return types.SimpleNamespace(Proxy=proxy, Name="BoxFEFCO0301_Tray")

    def _make_lid_object(self):
        from objects.box_fefco0301_lid import LidFEFCO0301

        proxy = LidFEFCO0301(_FakeFeature())
        return types.SimpleNamespace(Proxy=proxy, Name="BoxFEFCO0301_Lid")

    def _make_tuck_object(self):
        from objects.box_fefco0713 import BoxFEFCO0713

        proxy = BoxFEFCO0713(_FakeFeature())
        return types.SimpleNamespace(Proxy=proxy, Name="BoxFEFCO0713")

    def test_command_registered(self):
        from PackagingWB import PackagingWorkbenchManager

        ids = PackagingWorkbenchManager().register_commands()
        self.assertIn("Packaging_GenerateDieline", ids)
        self.assertIn("Packaging_GenerateDieline", self.registered)

    def test_is_active_false_without_selection(self):
        from commands.cmd_generate_dieline import CmdGenerateDieline

        self.selection.set([])
        self.assertFalse(CmdGenerateDieline().IsActive())

    def test_is_active_true_with_box(self):
        from commands.cmd_generate_dieline import CmdGenerateDieline

        self.selection.set([self._make_box_object()])
        self.assertTrue(CmdGenerateDieline().IsActive())

    def test_is_active_true_with_tray(self):
        from commands.cmd_generate_dieline import CmdGenerateDieline

        self.selection.set([self._make_tray_object()])
        self.assertTrue(CmdGenerateDieline().IsActive())

    def test_is_active_true_with_lid(self):
        from commands.cmd_generate_dieline import CmdGenerateDieline

        self.selection.set([self._make_lid_object()])
        self.assertTrue(CmdGenerateDieline().IsActive())

    def test_is_active_true_with_tuck_end(self):
        from commands.cmd_generate_dieline import CmdGenerateDieline

        self.selection.set([self._make_tuck_object()])
        self.assertTrue(CmdGenerateDieline().IsActive())

    def test_activated_dispatches_by_type(self):
        from commands.cmd_generate_dieline import CmdGenerateDieline
        from objects import fefco0201_dieline, fefco0301_dieline, fefco0713_dieline

        calls = []
        fefco0201_dieline.generate = lambda box: calls.append(("0201", box))
        fefco0301_dieline.generate_tray = lambda tray: calls.append(("tray", tray))
        fefco0301_dieline.generate_lid = lambda lid: calls.append(("lid", lid))
        fefco0713_dieline.generate = lambda box: calls.append(("0713", box))

        box_obj = self._make_box_object()
        tray_obj = self._make_tray_object()
        lid_obj = self._make_lid_object()
        tuck_obj = self._make_tuck_object()
        self.selection.set([box_obj, tray_obj, lid_obj, tuck_obj])
        CmdGenerateDieline().Activated()

        self.assertEqual(
            calls,
            [("0201", box_obj), ("tray", tray_obj), ("lid", lid_obj), ("0713", tuck_obj)],
        )


if __name__ == "__main__":
    unittest.main()
