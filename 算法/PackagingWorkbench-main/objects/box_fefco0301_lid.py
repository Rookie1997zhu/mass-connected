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
"""FEFCO 0301 lid (cover) feature.

The lid is a shallow inverted tray: a top panel (roof), four walls hanging
down, and four small flaps at the bottom folding INWARD. Its default Length and
Width are the tray nominal plus the 1 mm allowance so it slips over the tray.
Built as an exploded compound with internal dimensions Length x Width x Height.
"""

from __future__ import annotations

from objects.base_box import BaseBox


class LidFEFCO0301(BaseBox):
    """Parametric FEFCO 0301 lid proxy."""

    def __init__(self, obj):
        """Set up the proxy and lid dimension properties.

        Defaults are the tray nominal (200 x 150) plus the 1 mm allowance, so
        the lid telescopes over a default tray; the lid is also shallower.
        """
        super().__init__(obj)
        self._add_property(
            obj, "App::PropertyLength", "Length", "Dimensions",
            "Internal length (X) of the lid (tray length + allowance)", 201.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Width", "Dimensions",
            "Internal width (Y) of the lid (tray width + allowance)", 151.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Height", "Dimensions",
            "Internal height (Z) of the lid", 25.0,
        )

    def execute(self, obj):
        """Build the exploded lid: roof + 4 walls + 4 inward bottom flaps."""
        import Part

        length = obj.Length.Value
        width = obj.Width.Value
        height = obj.Height.Value
        thickness = obj.Thickness.Value
        flap = 4.0 * thickness

        panels = []

        # Roof plate on top, covering the whole footprint.
        panels.append(self._make_panel(length + 2 * thickness, width + 2 * thickness,
                                       thickness, (-thickness, -thickness, height)))

        # Four walls hanging down around the cavity [0,L] x [0,W] x [0,H].
        panels.append(self._make_panel(length + 2 * thickness, thickness, height,
                                       (-thickness, -thickness, 0.0)))       # front
        panels.append(self._make_panel(length + 2 * thickness, thickness, height,
                                       (-thickness, width, 0.0)))            # back
        panels.append(self._make_panel(thickness, width, height,
                                       (-thickness, 0.0, 0.0)))              # left
        panels.append(self._make_panel(thickness, width, height,
                                       (length, 0.0, 0.0)))                  # right

        # Bottom flaps, laid flat at z = -T, pointing INWARD.
        bottom = -thickness
        panels.append(self._make_panel(length, flap, thickness,
                                       (0.0, 0.0, bottom)))                  # front, inward +Y
        panels.append(self._make_panel(length, flap, thickness,
                                       (0.0, width - flap, bottom)))         # back, inward -Y
        panels.append(self._make_panel(flap, width, thickness,
                                       (0.0, 0.0, bottom)))                  # left, inward +X
        panels.append(self._make_panel(flap, width, thickness,
                                       (length - flap, 0.0, bottom)))        # right, inward -X

        obj.Shape = Part.makeCompound(panels)
