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
"""Flat dieline generator for the FEFCO 0301 tray and lid.

Both pieces share the same cross-shaped tray blank: a central bottom panel,
four walls folding up from its edges, and four small corner-reinforcement flaps
on the front/back walls. Cut = the free outer edges; Crease = the fold lines
between bottom/walls and walls/flaps. Perforation is empty.
"""

from __future__ import annotations


def generate_tray(tray_feature):
    """Generate the flat dieline for a FEFCO 0301 tray feature."""
    return _generate(tray_feature, x_offset=0.0)


def generate_lid(lid_feature):
    """Generate the flat dieline for a FEFCO 0301 lid feature."""
    # Offset in X so the lid dieline sits beside the tray dieline.
    return _generate(lid_feature, x_offset=2.0 * lid_feature.Length.Value)


def _generate(feature, x_offset):
    from utils import die_lines
    from utils.die_lines import DielineLayer

    doc = feature.Document
    length = feature.Length.Value
    width = feature.Width.Value
    height = feature.Height.Value
    thickness = feature.Thickness.Value

    ox = x_offset
    oy = -200.0 - width - height  # below the 3D model

    main = die_lines.create_dieline_group(doc, feature.Name)
    cut = die_lines.get_layer_group(main, DielineLayer.CUT)
    crease = die_lines.get_layer_group(main, DielineLayer.CREASE)

    _build_tray_blank(cut, crease, length, width, height, thickness, ox, oy)

    doc.recompute()
    return main


def _build_tray_blank(cut, crease, length, width, height, thickness, ox, oy):
    """Lay out a cross-shaped tray/lid blank into the cut and crease groups."""
    from utils import die_lines

    cf = 4.0 * thickness  # corner-flap depth

    # Central bottom rectangle.
    bx0, bx1 = ox, ox + length
    by0, by1 = oy, oy + width

    def line(group, p1, p2, label):
        die_lines.add_line(group, (p1[0], p1[1], 0.0), (p2[0], p2[1], 0.0), label)

    # -- Crease lines (folds) ------------------------------------------------
    # Four bottom edges (bottom <-> walls).
    line(crease, (bx0, by0), (bx1, by0), "Crease")  # south
    line(crease, (bx0, by1), (bx1, by1), "Crease")  # north
    line(crease, (bx0, by0), (bx0, by1), "Crease")  # west
    line(crease, (bx1, by0), (bx1, by1), "Crease")  # east
    # Wall <-> corner-flap folds (vertical, at the ends of north/south walls).
    line(crease, (bx0, by1), (bx0, by1 + height), "Crease")  # NW
    line(crease, (bx1, by1), (bx1, by1 + height), "Crease")  # NE
    line(crease, (bx0, by0 - height), (bx0, by0), "Crease")  # SW
    line(crease, (bx1, by0 - height), (bx1, by0), "Crease")  # SE

    # -- Cut lines (free edges) ---------------------------------------------
    # North and south wall outer edges.
    line(cut, (bx0, by1 + height), (bx1, by1 + height), "Cut")  # north top
    line(cut, (bx0, by0 - height), (bx1, by0 - height), "Cut")  # south bottom

    # West wall (three free edges).
    line(cut, (bx0 - height, by0), (bx0 - height, by1), "Cut")
    line(cut, (bx0 - height, by1), (bx0, by1), "Cut")
    line(cut, (bx0 - height, by0), (bx0, by0), "Cut")

    # East wall (three free edges).
    line(cut, (bx1 + height, by0), (bx1 + height, by1), "Cut")
    line(cut, (bx1, by1), (bx1 + height, by1), "Cut")
    line(cut, (bx1, by0), (bx1 + height, by0), "Cut")

    # Four corner flaps (three free edges each).
    flaps = [
        (bx0 - cf, by1, bx0, by1 + height),        # NW
        (bx1, by1, bx1 + cf, by1 + height),        # NE
        (bx0 - cf, by0 - height, bx0, by0),        # SW
        (bx1, by0 - height, bx1 + cf, by0),        # SE
    ]
    for fx0, fy0, fx1, fy1 in flaps:
        line(cut, (fx0, fy0), (fx0, fy1), "CutFlap")  # outer vertical
        line(cut, (fx0, fy1), (fx1, fy1), "CutFlap")  # top
        line(cut, (fx0, fy0), (fx1, fy0), "CutFlap")  # bottom
