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
"""Command that creates a parametric FEFCO 0713 tuck-end carton."""

from __future__ import annotations

import FreeCAD
import FreeCADGui

from PackagingWB import icon_path

# Command identifier used with FreeCADGui.addCommand and on the toolbar/menu.
COMMAND_ID = "Packaging_FEFCO0713"


class CmdPackagingFEFCO0713:
    """Insert a parametric FEFCO 0713 (tuck-end) carton."""

    def GetResources(self):
        """Return the icon, menu text and tooltip shown by FreeCAD."""
        return {
            "Pixmap": icon_path("FEFCO0713.svg"),
            "MenuText": "FEFCO 0713 tuck-end",
            "ToolTip": "Create a parametric FEFCO 0713 tuck-end retail carton",
            "Accel": "P, E",
        }

    def Activated(self):
        """Create the carton FeaturePython object with proxy + view provider."""
        from objects.box_fefco0713 import BoxFEFCO0713
        from objects.view_provider import BoxViewProvider

        doc = FreeCAD.ActiveDocument
        if doc is None:
            doc = FreeCAD.newDocument()

        obj = doc.addObject("Part::FeaturePython", "BoxFEFCO0713")
        BoxFEFCO0713(obj)
        if obj.ViewObject is not None:
            BoxViewProvider(obj.ViewObject)

        doc.recompute()
        FreeCADGui.SendMsgToActiveView("ViewFit")

    def IsActive(self):
        """Return whether the command can run (always, when the GUI is up)."""
        return True


def register():
    """Register this command with FreeCAD and return its identifier."""
    FreeCADGui.addCommand(COMMAND_ID, CmdPackagingFEFCO0713())
    return COMMAND_ID
