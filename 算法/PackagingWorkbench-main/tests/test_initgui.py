# SPDX-License-Identifier: LGPL-2.1-or-later
"""Regression test for workbench registration in InitGui.py.

This reproduces how FreeCAD executes ``InitGui.py`` at GUI startup: it injects
``Workbench`` (the base class), ``Gui`` (FreeCADGui) and ``App`` (FreeCAD) as
globals into the execution namespace, then ``exec``s the file. The base class
is the injected ``Workbench`` global, NOT ``FreeCADGui.Workbench`` (which does
not exist as a module attribute) -- getting this wrong makes the workbench
silently fail to appear in the selector.

Runs with a plain Python interpreter; no FreeCAD installation required.
"""

import os
import sys
import unittest

INIT_GUI = os.path.join(os.path.dirname(os.path.dirname(__file__)), "InitGui.py")


class _FakeWorkbench:
    """Stand-in for FreeCAD's injected ``Workbench`` base class."""

    def appendToolbar(self, *args, **kwargs):
        pass

    def appendMenu(self, *args, **kwargs):
        pass


class _FakeGui:
    """Stand-in for the injected ``Gui`` global, recording registration."""

    def __init__(self):
        self.registered = None

    def addWorkbench(self, workbench):
        self.registered = workbench() if isinstance(workbench, type) else workbench


class InitGuiRegistrationTest(unittest.TestCase):
    def _run_initgui(self):
        gui = _FakeGui()
        # Reproduce RunInitGuiPy faithfully, so this test catches the bugs that
        # only bite under FreeCAD:
        #   * no ``__file__`` in scope (it exec's a compiled string);
        #   * SEPARATE globals/locals dicts, so module-level names are invisible
        #     inside the class body and methods.
        # FreeCAD injects Workbench/Gui/App as globals.
        init_globals = {
            "__name__": "__main__",
            "Workbench": _FakeWorkbench,
            "Gui": gui,
            "App": None,
        }
        init_locals = {}
        # The addon root must be importable so InitGui's local `from PackagingWB`
        # resolves, exactly as FreeCAD puts the Mod subdir on sys.path at boot.
        addon_root = os.path.dirname(INIT_GUI)
        if addon_root not in sys.path:
            sys.path.insert(0, addon_root)
        with open(INIT_GUI, encoding="utf-8") as handle:
            code = compile(handle.read(), INIT_GUI, "exec")
        exec(code, init_globals, init_locals)
        return gui.registered

    def test_workbench_is_registered(self):
        wb = self._run_initgui()
        self.assertIsNotNone(wb, "Gui.addWorkbench was never called")

    def test_required_attributes(self):
        wb = self._run_initgui()
        self.assertEqual(wb.MenuText, "Packaging")
        self.assertTrue(wb.ToolTip)
        self.assertEqual(wb.GetClassName(), "Gui::PythonWorkbench")

    def test_icon_file_exists(self):
        wb = self._run_initgui()
        self.assertTrue(os.path.isfile(wb.Icon), f"icon not found: {wb.Icon}")


if __name__ == "__main__":
    unittest.main()
