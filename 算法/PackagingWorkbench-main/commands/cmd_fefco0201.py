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
"""Command that creates a parametric FEFCO 0201 box."""

from __future__ import annotations

import FreeCAD
import FreeCADGui

from PackagingWB import icon_path

# Command identifier used with FreeCADGui.addCommand and on the toolbar/menu.
COMMAND_ID = "Packaging_FEFCO0201"


class CmdPackagingFEFCO0201:
    """Insert a parametric FEFCO 0201 (RSC) box into the active document."""

    def GetResources(self):
        """Return the icon, menu text and tooltip shown by FreeCAD."""
        return {
            "Pixmap": icon_path("FEFCO0201.svg"),
            "MenuText": "FEFCO 0201 box",
            "ToolTip": "Create a parametric FEFCO 0201 (Regular Slotted Container) box",
            "Accel": "P, F",
        }

    def Activated(self):
        """Create the FeaturePython object, attach proxy + view provider."""
        from objects.box_fefco0201 import BoxFEFCO0201
        from objects.view_provider import BoxViewProvider

        doc = FreeCAD.ActiveDocument
        if doc is None:
            doc = FreeCAD.newDocument()

        obj = doc.addObject("Part::FeaturePython", "BoxFEFCO0201")
        BoxFEFCO0201(obj)
        if obj.ViewObject is not None:
            BoxViewProvider(obj.ViewObject)

        doc.recompute()
        FreeCADGui.SendMsgToActiveView("ViewFit")

    def IsActive(self):
        """Return whether the command can run (always, when the GUI is up)."""
        return True


def register():
    """Register this command with FreeCAD and return its identifier."""
    FreeCADGui.addCommand(COMMAND_ID, CmdPackagingFEFCO0201())
    return COMMAND_ID
