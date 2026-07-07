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
"""Flat dieline generator for the FEFCO 0201 box.

Reads Length/Width/Height/Thickness from a :class:`BoxFEFCO0201` feature and
lays out the classic RSC blank in the XY plane, below the 3D box:

      +----+----+----+----+
      |    |    |    |    |          top flaps (W/2 tall)
      +----+----+----+----+----+
      | L  | W  | L  | W  |Tab |     body (H tall) + 30 mm glue tab
      +----+----+----+----+----+
      |    |    |    |    |
      +----+----+----+----+          bottom flaps (W/2 tall)

Cut lines = outer perimeter + the slits between flaps. Crease lines = the four
vertical panel folds and the two horizontal body/flap folds. Perforation is
empty for the basic FEFCO 0201.
"""

from __future__ import annotations

# Default glue-tab width in millimetres.
TAB = 30.0


def generate(box_feature):
    """Generate the flat dieline for ``box_feature``.

    Args:
        box_feature: A ``Part::FeaturePython`` whose proxy is a BoxFEFCO0201.

    Returns:
        The main ``App::DocumentObjectGroup`` holding the dieline layers.
    """
    from utils import die_lines
    from utils.die_lines import DielineLayer

    doc = box_feature.Document
    length = box_feature.Length.Value
    width = box_feature.Width.Value
    height = box_feature.Height.Value
    thickness = box_feature.Thickness.Value

    # Place the blank well below the 3D box so the two never overlap.
    ox = 0.0
    oy = -200.0 - width / 2.0 - height

    main = die_lines.create_dieline_group(doc, box_feature.Name)
    cut = die_lines.get_layer_group(main, DielineLayer.CUT)
    crease = die_lines.get_layer_group(main, DielineLayer.CREASE)

    _build_cuts(cut, length, width, height, thickness, TAB, ox, oy)
    _build_creases(crease, length, width, height, thickness, TAB, ox, oy)

    doc.recompute()
    return main


def _x_positions(length, width, tab, ox):
    """Return the vertical fold x-coordinates ``(x0..x5)`` of the blank."""
    x0 = ox
    x1 = ox + length
    x2 = ox + length + width
    x3 = ox + 2 * length + width
    x4 = ox + 2 * length + 2 * width
    x5 = x4 + tab
    return x0, x1, x2, x3, x4, x5


def _y_levels(width, height, oy):
    """Return ``(y_bot, y_body0, y_bodyH, y_top)`` y-coordinates of the blank."""
    y_body0 = oy
    y_bodyH = oy + height
    y_top = oy + height + width / 2.0
    y_bot = oy - width / 2.0
    return y_bot, y_body0, y_bodyH, y_top


def _build_cuts(group, length, width, height, thickness, tab=TAB, ox=0.0, oy=0.0):
    """Create the Cut lines: outer perimeter (8) + flap slits (6)."""
    from utils import die_lines

    x0, x1, x2, x3, x4, x5 = _x_positions(length, width, tab, ox)
    y_bot, y0, yh, y_top = _y_levels(width, height, oy)

    # Outer perimeter, traced clockwise.
    perimeter = [
        ((x0, y_bot, 0.0), (x4, y_bot, 0.0)),    # bottom edge of bottom flaps
        ((x4, y_bot, 0.0), (x4, y0, 0.0)),       # up to body on the right
        ((x4, y0, 0.0), (x5, y0, 0.0)),          # bottom edge of glue tab
        ((x5, y0, 0.0), (x5, yh, 0.0)),          # right edge of glue tab
        ((x5, yh, 0.0), (x4, yh, 0.0)),          # top edge of glue tab
        ((x4, yh, 0.0), (x4, y_top, 0.0)),       # up to top flaps
        ((x4, y_top, 0.0), (x0, y_top, 0.0)),    # top edge of top flaps
        ((x0, y_top, 0.0), (x0, y_bot, 0.0)),    # left edge
    ]
    for p1, p2 in perimeter:
        die_lines.add_line(group, p1, p2, "Cut")

    # Slits between adjacent flaps (length W/2 each), top and bottom.
    for xi in (x1, x2, x3):
        die_lines.add_line(group, (xi, yh, 0.0), (xi, y_top, 0.0), "CutSlit")
        die_lines.add_line(group, (xi, y_bot, 0.0), (xi, y0, 0.0), "CutSlit")


def _build_creases(group, length, width, height, thickness, tab=TAB, ox=0.0, oy=0.0):
    """Create the Crease lines: 4 vertical panel folds + 2 horizontal folds."""
    from utils import die_lines

    x0, x1, x2, x3, x4, x5 = _x_positions(length, width, tab, ox)
    _, y0, yh, _ = _y_levels(width, height, oy)

    # Vertical folds between panels and before the glue tab.
    for xi in (x1, x2, x3, x4):
        die_lines.add_line(group, (xi, y0, 0.0), (xi, yh, 0.0), "Crease")

    # Horizontal folds separating the body from the top and bottom flaps.
    die_lines.add_line(group, (x0, y0, 0.0), (x4, y0, 0.0), "Crease")
    die_lines.add_line(group, (x0, yh, 0.0), (x4, yh, 0.0), "Crease")
