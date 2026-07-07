# SPDX-License-Identifier: LGPL-2.1-or-later
# ***************************************************************************
# *   Copyright (c) 2026 Packaging Workbench Team                           *
# *                                                                         *
# *   This file is part of the Packaging workbench for FreeCAD.             *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
# *   the License, or (at your option) any later version.                   *
# ***************************************************************************
"""The "Hello Box" demo command.

Creates a fixed-size ``Part::Box`` in the active document. This is the simplest
possible command and mainly verifies that command registration, the toolbar and
the menu are wired up correctly end to end.
"""

from __future__ import annotations

import FreeCAD
import FreeCADGui

from PackagingWB import icon_path

# Command identifier used with FreeCADGui.addCommand and on the toolbar/menu.
COMMAND_ID = "Packaging_HelloBox"

# Demo box dimensions in millimetres (Part::Box: Length=X, Width=Y, Height=Z).
_BOX_LENGTH = 200.0
_BOX_WIDTH = 150.0
_BOX_HEIGHT = 100.0


class CmdPackagingHelloBox:
    """Create a 200x150x100 mm demo box in the active document."""

    def GetResources(self):
        """Return the icon, menu text and tooltip shown by FreeCAD.

        Returns:
            Mapping consumed by FreeCAD to build the toolbar button and menu
            entry for this command.
        """
        return {
            "Pixmap": icon_path("HelloBox.svg"),
            "MenuText": "Hello Box",
            "ToolTip": "Create a 200x150x100 mm demo box in the active document",
            "Accel": "P, B",
        }

    def Activated(self):
        """Create the demo box, recompute and fit the view."""
        doc = FreeCAD.ActiveDocument
        if doc is None:
            doc = FreeCAD.newDocument()

        box = doc.addObject("Part::Box", "PackagingHelloBox")
        box.Length = _BOX_LENGTH
        box.Width = _BOX_WIDTH
        box.Height = _BOX_HEIGHT

        doc.recompute()
        FreeCADGui.SendMsgToActiveView("ViewFit")

    def IsActive(self):
        """Return whether the command can run (always, when the GUI is up)."""
        return True


def register():
    """Register this command with FreeCAD and return its identifier.

    Returns:
        The command identifier, so the caller can add it to toolbars/menus.
    """
    FreeCADGui.addCommand(COMMAND_ID, CmdPackagingHelloBox())
    return COMMAND_ID
