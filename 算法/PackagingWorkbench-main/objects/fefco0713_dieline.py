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
"""Flat dieline generator for the FEFCO 0713 tuck-end carton.

Body strip of four panels (W, L, W, L) plus a glue flap on the right. On the
two short (W) panels sit small dust flaps; on the second long (L) panel sits the
main cover with its tuck-in tongue. The bottom mirrors the top.

      dust         dust
      +--+  +--+        tuck
      |  |  |  |     +------+
      |  |  |  |     |cover |
   +--+--+--+--+-----+------+----+
   | W| L| W| L      | glue |        body (height H)
   +--+--+--+--+-----+------+----+
      |  |  |  |     |cover |
      +--+  +--+     +------+
                        tuck
"""

from __future__ import annotations


def generate(box_feature):
    """Generate the flat dieline for a FEFCO 0713 carton feature."""
    from utils import die_lines
    from utils.die_lines import DielineLayer

    doc = box_feature.Document
    length = box_feature.Length.Value
    width = box_feature.Width.Value
    height = box_feature.Height.Value
    thickness = box_feature.Thickness.Value
    glue = box_feature.GlueFlapWidth.Value
    tuck = box_feature.TuckLength.Value

    ox = 0.0
    oy = -200.0 - width - height  # below the 3D model

    main = die_lines.create_dieline_group(doc, box_feature.Name)
    cut = die_lines.get_layer_group(main, DielineLayer.CUT)
    crease = die_lines.get_layer_group(main, DielineLayer.CREASE)

    _build_creases(crease, length, width, height, thickness, glue, tuck, ox, oy)
    _build_cuts(cut, length, width, height, thickness, glue, tuck, ox, oy)

    doc.recompute()
    return main


def _columns(length, width, glue, ox):
    """Return the vertical fold x-coordinates of the body strip."""
    x0 = ox                       # left edge
    xa = ox + width               # col0(W) | col1(L)
    xb = ox + width + length      # col1(L) | col2(W)
    xc = ox + 2 * width + length  # col2(W) | col3(L)
    xd = ox + 2 * width + 2 * length  # col3(L) | glue
    xe = xd + glue                # right edge of glue flap
    return x0, xa, xb, xc, xd, xe


def _build_creases(group, length, width, height, thickness, glue, tuck, ox=0.0, oy=0.0):
    """Create the fold (crease) lines."""
    from utils import die_lines

    x0, xa, xb, xc, xd, xe = _columns(length, width, glue, ox)
    y0 = oy
    yh = oy + height

    def line(p1, p2):
        die_lines.add_line(group, (p1[0], p1[1], 0.0), (p2[0], p2[1], 0.0), "Crease")

    # Vertical folds between body panels and the glue flap.
    for x in (xa, xb, xc, xd):
        line((x, y0), (x, yh))

    # Horizontal folds where the top/bottom flaps attach (W panels + cover L).
    for a, b in ((x0, xa), (xb, xc), (xc, xd)):  # col0, col2, col3
        line((a, yh), (b, yh))   # top
        line((a, y0), (b, y0))   # bottom

    # Cover <-> tuck folds (on col3).
    line((xc, yh + width), (xd, yh + width))    # top cover/tuck
    line((xc, y0 - width), (xd, y0 - width))    # bottom cover/tuck


def _build_cuts(group, length, width, height, thickness, glue, tuck, ox=0.0, oy=0.0):
    """Create the cut lines (free outer edges + flap edges)."""
    from utils import die_lines

    x0, xa, xb, xc, xd, xe = _columns(length, width, glue, ox)
    y0 = oy
    yh = oy + height
    dust = 3.0 * thickness

    def line(p1, p2):
        die_lines.add_line(group, (p1[0], p1[1], 0.0), (p2[0], p2[1], 0.0), "Cut")

    # Body outline (left/right edges + the bare top/bottom segments).
    line((x0, y0), (x0, yh))            # left
    line((xe, y0), (xe, yh))            # right (glue flap)
    line((xa, yh), (xb, yh))            # top over col1 (bare)
    line((xd, yh), (xe, yh))            # top over glue (bare)
    line((xa, y0), (xb, y0))            # bottom over col1 (bare)
    line((xd, y0), (xe, y0))            # bottom over glue (bare)

    def dust_flap(x_left, x_right, y_base, y_tip):
        line((x_left, y_base), (x_left, y_tip))
        line((x_left, y_tip), (x_right, y_tip))
        line((x_right, y_tip), (x_right, y_base))

    # Top dust flaps on the two W panels (col0, col2).
    dust_flap(x0, xa, yh, yh + dust)
    dust_flap(xb, xc, yh, yh + dust)
    # Bottom dust flaps.
    dust_flap(x0, xa, y0, y0 - dust)
    dust_flap(xb, xc, y0, y0 - dust)

    # Cover side edges (col3) top and bottom.
    line((xc, yh), (xc, yh + width))    # top cover left
    line((xd, yh), (xd, yh + width))    # top cover right
    line((xc, y0), (xc, y0 - width))    # bottom cover left
    line((xd, y0), (xd, y0 - width))    # bottom cover right

    def tuck_flap(y_base, y_tip):
        line((xc, y_base), (xc, y_tip))
        line((xc, y_tip), (xd, y_tip))
        line((xd, y_tip), (xd, y_base))

    # Tuck tongues, top and bottom.
    tuck_flap(yh + width, yh + width + tuck)
    tuck_flap(y0 - width, y0 - width - tuck)
