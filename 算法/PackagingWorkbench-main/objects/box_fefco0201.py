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
"""FEFCO 0201 box (Regular Slotted Container) feature.

Models the classic "American" shipping box as an *exploded* 3D shape: four
upright wall panels around the internal cavity, with all eight top/bottom flaps
folded open flat (90 degrees) so the construction reads clearly as a carton.
The flat dieline is generated separately in Step 4.

Dimensions are INTERNAL (the cavity is exactly Length x Width x Height); panels
of real thickness sit outside that cavity, per FEFCO practice.
"""

from __future__ import annotations

from objects.base_box import BaseBox


class BoxFEFCO0201(BaseBox):
    """Parametric FEFCO 0201 box proxy."""

    def __init__(self, obj):
        """Set up the proxy and FEFCO 0201 dimension properties."""
        super().__init__(obj)
        self._add_property(
            obj, "App::PropertyLength", "Length", "Dimensions",
            "Internal length (X) of the box", 200.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Width", "Dimensions",
            "Internal width (Y) of the box", 150.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Height", "Dimensions",
            "Internal height (Z) of the box", 100.0,
        )

    def execute(self, obj):
        """Rebuild the exploded shape from the current properties.

        Builds 12 solid panels (4 walls + 4 top flaps + 4 bottom flaps) and
        combines them into a single compound. No boolean operations are used.
        """
        import Part

        length = obj.Length.Value
        width = obj.Width.Value
        height = obj.Height.Value
        thickness = obj.Thickness.Value
        flap = width / 2.0  # each flap is half the width deep (RSC)

        panels = []

        # -- four upright walls around the cavity [0,L] x [0,W] x [0,H] -------
        # Length panels (front/back) span the full outer length to close corners.
        panels.append(self._make_panel(length + 2 * thickness, thickness, height,
                                       (-thickness, -thickness, 0.0)))         # front
        panels.append(self._make_panel(length + 2 * thickness, thickness, height,
                                       (-thickness, width, 0.0)))              # back
        # Width panels (left/right) fit between them.
        panels.append(self._make_panel(thickness, width, height,
                                       (-thickness, 0.0, 0.0)))                # left
        panels.append(self._make_panel(thickness, width, height,
                                       (length, 0.0, 0.0)))                    # right

        # Flaps are inset by 2*thickness on each side and centred on their own
        # panel, so that when splayed open at 90 degrees they no longer overlap
        # the adjacent panels at the corners. The 2D dieline is unaffected.
        inset = 2.0 * thickness
        flap_len = length - 2.0 * inset   # length-direction flap width
        flap_wid = width - 2.0 * inset    # width-direction flap width

        # -- top flaps (folded flat at z = H), splayed outward ----------------
        top = height
        panels.append(self._make_panel(flap_len, flap, thickness,
                                       (inset, -thickness - flap, top)))       # front-top
        panels.append(self._make_panel(flap_len, flap, thickness,
                                       (inset, width + thickness, top)))       # back-top
        panels.append(self._make_panel(flap, flap_wid, thickness,
                                       (-thickness - flap, inset, top)))       # left-top
        panels.append(self._make_panel(flap, flap_wid, thickness,
                                       (length + thickness, inset, top)))      # right-top

        # -- bottom flaps (folded flat at z = -T), splayed outward ------------
        bottom = -thickness
        panels.append(self._make_panel(flap_len, flap, thickness,
                                       (inset, -thickness - flap, bottom)))    # front
        panels.append(self._make_panel(flap_len, flap, thickness,
                                       (inset, width + thickness, bottom)))    # back
        panels.append(self._make_panel(flap, flap_wid, thickness,
                                       (-thickness - flap, inset, bottom)))    # left
        panels.append(self._make_panel(flap, flap_wid, thickness,
                                       (length + thickness, inset, bottom)))   # right

        obj.Shape = Part.makeCompound(panels)
