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
"""Command that creates a parametric FEFCO 0301 tray + lid pair."""

from __future__ import annotations

import FreeCAD
import FreeCADGui

from PackagingWB import icon_path

# Command identifier used with FreeCADGui.addCommand and on the toolbar/menu.
COMMAND_ID = "Packaging_FEFCO0301"


class CmdPackagingFEFCO0301:
    """Insert a parametric FEFCO 0301 (tray + lid) two-piece box."""

    def GetResources(self):
        """Return the icon, menu text and tooltip shown by FreeCAD."""
        return {
            "Pixmap": icon_path("FEFCO0301.svg"),
            "MenuText": "FEFCO 0301 tray + lid",
            "ToolTip": "Create a parametric FEFCO 0301 tray and matching lid",
            "Accel": "P, T",
        }

    def Activated(self):
        """Create the tray and lid FeaturePython objects side by side."""
        from objects.box_fefco0301_lid import LidFEFCO0301
        from objects.box_fefco0301_tray import TrayFEFCO0301
        from objects.view_provider import BoxViewProvider

        doc = FreeCAD.ActiveDocument
        if doc is None:
            doc = FreeCAD.newDocument()

        tray = doc.addObject("Part::FeaturePython", "BoxFEFCO0301_Tray")
        TrayFEFCO0301(tray)
        if tray.ViewObject is not None:
            BoxViewProvider(tray.ViewObject)

        lid = doc.addObject("Part::FeaturePython", "BoxFEFCO0301_Lid")
        LidFEFCO0301(lid)
        if lid.ViewObject is not None:
            BoxViewProvider(lid.ViewObject)

        # Place the lid beside the tray so both are visible at once.
        lid.Placement = FreeCAD.Placement(
            FreeCAD.Vector(2.0 * tray.Length.Value, 0.0, 0.0), FreeCAD.Rotation()
        )

        doc.recompute()
        FreeCADGui.SendMsgToActiveView("ViewFit")

    def IsActive(self):
        """Return whether the command can run (always, when the GUI is up)."""
        return True


def register():
    """Register this command with FreeCAD and return its identifier."""
    FreeCADGui.addCommand(COMMAND_ID, CmdPackagingFEFCO0301())
    return COMMAND_ID
