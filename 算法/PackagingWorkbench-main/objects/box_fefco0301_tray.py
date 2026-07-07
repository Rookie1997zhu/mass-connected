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
"""FEFCO 0301 tray (base) feature.

The tray is an open-top box: a bottom panel, four upright walls, and four small
reinforcement flaps on top of the walls that fold INWARD to stiffen the
corners. Built as an exploded compound (flaps laid flat at 90 degrees), with
internal dimensions Length x Width x Height.
"""

from __future__ import annotations

from objects.base_box import BaseBox


class TrayFEFCO0301(BaseBox):
    """Parametric FEFCO 0301 tray proxy."""

    def __init__(self, obj):
        """Set up the proxy and tray dimension properties."""
        super().__init__(obj)
        self._add_property(
            obj, "App::PropertyLength", "Length", "Dimensions",
            "Internal length (X) of the tray", 200.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Width", "Dimensions",
            "Internal width (Y) of the tray", 150.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Height", "Dimensions",
            "Internal height (Z) of the tray", 60.0,
        )

    def execute(self, obj):
        """Build the exploded tray: bottom + 4 walls + 4 inward top flaps."""
        import Part

        length = obj.Length.Value
        width = obj.Width.Value
        height = obj.Height.Value
        thickness = obj.Thickness.Value
        flap = 4.0 * thickness  # small corner-reinforcement flap depth

        panels = []

        # Bottom plate covering the whole footprint (under the walls).
        panels.append(self._make_panel(length + 2 * thickness, width + 2 * thickness,
                                       thickness, (-thickness, -thickness, -thickness)))

        # Four upright walls around the cavity [0,L] x [0,W] x [0,H].
        panels.append(self._make_panel(length + 2 * thickness, thickness, height,
                                       (-thickness, -thickness, 0.0)))       # front
        panels.append(self._make_panel(length + 2 * thickness, thickness, height,
                                       (-thickness, width, 0.0)))            # back
        panels.append(self._make_panel(thickness, width, height,
                                       (-thickness, 0.0, 0.0)))              # left
        panels.append(self._make_panel(thickness, width, height,
                                       (length, 0.0, 0.0)))                  # right

        # Top reinforcement flaps, laid flat at z = H, pointing INWARD.
        top = height
        panels.append(self._make_panel(length, flap, thickness,
                                       (0.0, 0.0, top)))                     # front, inward +Y
        panels.append(self._make_panel(length, flap, thickness,
                                       (0.0, width - flap, top)))            # back, inward -Y
        panels.append(self._make_panel(flap, width, thickness,
                                       (0.0, 0.0, top)))                     # left, inward +X
        panels.append(self._make_panel(flap, width, thickness,
                                       (length - flap, 0.0, top)))           # right, inward -X

        obj.Shape = Part.makeCompound(panels)
