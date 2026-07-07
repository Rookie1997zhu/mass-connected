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
"""FEFCO 0713 tuck-end carton feature.

The classic one-piece retail carton (medicines, cosmetics): four upright walls,
a glue flap on the right, and a closing structure on top and bottom made of a
main cover panel, two small dust flaps and a tuck-in tongue. Built as an
exploded compound (flaps splayed open), typically tall and narrow.
"""

from __future__ import annotations

from objects.base_box import BaseBox


class BoxFEFCO0713(BaseBox):
    """Parametric FEFCO 0713 tuck-end carton proxy."""

    def __init__(self, obj):
        """Set up the proxy and tuck-end dimension properties."""
        super().__init__(obj)
        # Tuck-end cartons use thinner board and a tighter clearance; override
        # the BaseBox common defaults (this runs once, at creation).
        obj.Thickness = 1.5
        obj.Allowance = 0.5
        self._add_property(
            obj, "App::PropertyLength", "Length", "Dimensions",
            "Internal length (X) of the carton", 50.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Width", "Dimensions",
            "Internal width/depth (Y) of the carton", 30.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Height", "Dimensions",
            "Internal height (Z) of the carton", 150.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "GlueFlapWidth", "Tuck-End",
            "Width of the glue flap on the right wall", 12.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "TuckLength", "Tuck-End",
            "Length of the tuck-in tongue", 25.0,
        )

    def execute(self, obj):
        """Build the exploded tuck-end carton (13 panels)."""
        import Part

        length = obj.Length.Value
        width = obj.Width.Value
        height = obj.Height.Value
        thickness = obj.Thickness.Value
        glue = obj.GlueFlapWidth.Value
        tuck = obj.TuckLength.Value
        dust = 3.0 * thickness  # small dust-flap depth

        panels = []

        # -- four upright walls around the cavity [0,L] x [0,W] x [0,H] -------
        panels.append(self._make_panel(length + 2 * thickness, thickness, height,
                                       (-thickness, -thickness, 0.0)))       # front
        panels.append(self._make_panel(length + 2 * thickness, thickness, height,
                                       (-thickness, width, 0.0)))            # back
        panels.append(self._make_panel(thickness, width, height,
                                       (-thickness, 0.0, 0.0)))              # left
        panels.append(self._make_panel(thickness, width, height,
                                       (length, 0.0, 0.0)))                  # right

        # -- glue flap, vertical tab extending past the right wall -----------
        panels.append(self._make_panel(glue, thickness, height,
                                       (length + thickness, 0.0, 0.0)))

        # -- top closure: cover (folds out front), 2 dust flaps, tuck --------
        top = height
        panels.append(self._make_panel(length, width, thickness,
                                       (0.0, -thickness - width, top)))      # cover
        panels.append(self._make_panel(dust, width, thickness,
                                       (-thickness - dust, 0.0, top)))       # left dust flap
        panels.append(self._make_panel(dust, width, thickness,
                                       (length + thickness, 0.0, top)))      # right dust flap
        panels.append(self._make_panel(length, tuck, thickness,
                                       (0.0, -thickness - width, top + thickness)))  # tuck

        # -- bottom closure: mirror of the top -------------------------------
        bottom = -thickness
        panels.append(self._make_panel(length, width, thickness,
                                       (0.0, -thickness - width, bottom)))   # cover
        panels.append(self._make_panel(dust, width, thickness,
                                       (-thickness - dust, 0.0, bottom)))    # left dust flap
        panels.append(self._make_panel(dust, width, thickness,
                                       (length + thickness, 0.0, bottom)))   # right dust flap
        panels.append(self._make_panel(length, tuck, thickness,
                                       (0.0, -thickness - width, bottom - thickness)))  # tuck

        obj.Shape = Part.makeCompound(panels)
