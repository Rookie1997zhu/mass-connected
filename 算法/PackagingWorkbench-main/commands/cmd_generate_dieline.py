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
"""Command that generates the flat 2D dieline from a selected box."""

from __future__ import annotations

import FreeCAD
import FreeCADGui

from PackagingWB import icon_path

# Command identifier used with FreeCADGui.addCommand and on the toolbar/menu.
COMMAND_ID = "Packaging_GenerateDieline"


def _dieline_action(obj):
    """Return a no-arg callable that builds ``obj``'s dieline, or ``None``.

    Dispatches on the object's proxy type across all supported box kinds.
    """
    from objects import fefco0201_dieline, fefco0301_dieline, fefco0713_dieline
    from objects.box_fefco0201 import BoxFEFCO0201
    from objects.box_fefco0301_lid import LidFEFCO0301
    from objects.box_fefco0301_tray import TrayFEFCO0301
    from objects.box_fefco0713 import BoxFEFCO0713

    proxy = getattr(obj, "Proxy", None)
    if isinstance(proxy, BoxFEFCO0201):
        return lambda: fefco0201_dieline.generate(obj)
    if isinstance(proxy, TrayFEFCO0301):
        return lambda: fefco0301_dieline.generate_tray(obj)
    if isinstance(proxy, LidFEFCO0301):
        return lambda: fefco0301_dieline.generate_lid(obj)
    if isinstance(proxy, BoxFEFCO0713):
        return lambda: fefco0713_dieline.generate(obj)
    return None


def _selected_boxes():
    """Return the selected objects that have a supported dieline action."""
    return [obj for obj in FreeCADGui.Selection.getSelection() if _dieline_action(obj)]


class CmdGenerateDieline:
    """Generate the flat dieline for each selected FEFCO 0201 box."""

    def GetResources(self):
        """Return the icon, menu text and tooltip shown by FreeCAD."""
        return {
            "Pixmap": icon_path("GenerateDieline.svg"),
            "MenuText": "Generate dieline",
            "ToolTip": "Generate the flat 2D dieline (cut/crease layers) from a selected box",
            "Accel": "P, D",
        }

    def Activated(self):
        """Generate the dieline for every selected box (any supported type)."""
        for obj in FreeCADGui.Selection.getSelection():
            action = _dieline_action(obj)
            if action is not None:
                action()

        if FreeCAD.ActiveDocument is not None:
            FreeCAD.ActiveDocument.recompute()
        FreeCADGui.SendMsgToActiveView("ViewFit")

    def IsActive(self):
        """Enable only when the selection holds at least one supported box."""
        return bool(_selected_boxes())


def register():
    """Register this command with FreeCAD and return its identifier."""
    FreeCADGui.addCommand(COMMAND_ID, CmdGenerateDieline())
    return COMMAND_ID
