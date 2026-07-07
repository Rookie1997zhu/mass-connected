# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tests for the "Hello Box" command.

FreeCAD's ``FreeCAD`` and ``FreeCADGui`` modules are mocked so the command
module can be imported and exercised under a plain Python interpreter.
"""

import os
import sys
import types
import unittest

ADDON_ROOT = os.path.dirname(os.path.dirname(__file__))


def _install_mocks():
    """Install minimal FreeCAD / FreeCADGui mocks into ``sys.modules``.

    Returns:
        The ``(gui, registered)`` pair, where ``registered`` maps command ids to
        the command objects passed to ``FreeCADGui.addCommand``.
    """
    registered = {}

    gui = types.ModuleType("FreeCADGui")
    gui.addCommand = lambda cmd_id, obj: registered.__setitem__(cmd_id, obj)
    gui.SendMsgToActiveView = lambda *a, **k: None

    app = types.ModuleType("FreeCAD")
    app.ActiveDocument = None
    app.newDocument = lambda *a, **k: None

    sys.modules["FreeCAD"] = app
    sys.modules["FreeCADGui"] = gui
    return gui, registered


class HelloBoxTest(unittest.TestCase):
    def setUp(self):
        if ADDON_ROOT not in sys.path:
            sys.path.insert(0, ADDON_ROOT)
        # Force a fresh import so the command module rebinds to these mocks.
        for name in ("PackagingWB", "commands", "commands.cmd_hello_box"):
            sys.modules.pop(name, None)
        self.gui, self.registered = _install_mocks()

    def test_module_imports(self):
        from commands import cmd_hello_box

        self.assertTrue(hasattr(cmd_hello_box, "CmdPackagingHelloBox"))
        self.assertEqual(cmd_hello_box.COMMAND_ID, "Packaging_HelloBox")

    def test_get_resources(self):
        from commands import cmd_hello_box

        res = cmd_hello_box.CmdPackagingHelloBox().GetResources()
        for key in ("Pixmap", "MenuText", "ToolTip"):
            self.assertIn(key, res)
        self.assertEqual(res["MenuText"], "Hello Box")
        self.assertTrue(os.path.isfile(res["Pixmap"]), f"icon missing: {res['Pixmap']}")

    def test_command_registered_via_manager(self):
        from PackagingWB import PackagingWorkbenchManager

        ids = PackagingWorkbenchManager().register_commands()
        # Other steps add more commands; just assert Hello Box is present.
        self.assertIn("Packaging_HelloBox", ids)
        self.assertIn("Packaging_HelloBox", self.registered)


if __name__ == "__main__":
    unittest.main()
