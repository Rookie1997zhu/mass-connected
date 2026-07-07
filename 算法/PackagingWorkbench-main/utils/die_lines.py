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
"""Reusable dieline layer helpers, independent of the box type.

A dieline is organised as a main group ``<name>_Dieline`` containing three
sub-groups -- Cut, Crease and Perforation -- each holding Draft line objects
styled by colour and draw style. These helpers are shared by every box type.
"""

from __future__ import annotations

from collections import namedtuple

_Layer = namedtuple("_Layer", ["name", "color", "draw_style"])


class DielineLayer:
    """The three standard dieline layers, with colour and draw style.

    Colours are RGB floats in [0, 1]; draw styles are FreeCAD Draft view
    ``DrawStyle`` values.
    """

    CUT = _Layer("Cut", (1.0, 0.0, 0.0), "Solid")
    CREASE = _Layer("Crease", (0.0, 0.0, 1.0), "Dashed")
    PERFORATION = _Layer("Perforation", (0.0, 0.7, 0.0), "Dotted")

    @classmethod
    def all(cls):
        """Return all layers in display order (Cut, Crease, Perforation)."""
        return [cls.CUT, cls.CREASE, cls.PERFORATION]

    @classmethod
    def by_name(cls, name):
        """Return the layer whose ``name`` matches exactly, or ``None``."""
        for layer in cls.all():
            if layer.name == name:
                return layer
        return None

    @classmethod
    def for_label(cls, label):
        """Return the layer matching a (possibly auto-suffixed) group label.

        FreeCAD appends a numeric suffix when a label collides with an existing
        one (e.g. a second dieline's ``Cut`` group becomes ``Cut009``), so we
        match by prefix rather than equality. Layer names do not prefix one
        another, so this is unambiguous.
        """
        for layer in cls.all():
            if label.startswith(layer.name):
                return layer
        return None


def create_dieline_group(doc, name):
    """Create the main dieline group with its three layer sub-groups.

    Args:
        doc: The FreeCAD document.
        name: Base name, e.g. the box object's name; the main group is
            ``<name>_Dieline``.

    Returns:
        The main ``App::DocumentObjectGroup``.
    """
    main = doc.addObject("App::DocumentObjectGroup", f"{name}_Dieline")
    main.Label = f"{name}_Dieline"
    for layer in DielineLayer.all():
        sub = doc.addObject("App::DocumentObjectGroup", layer.name)
        sub.Label = layer.name
        main.addObject(sub)
    return main


def get_layer_group(main_group, layer):
    """Return the sub-group for ``layer`` inside ``main_group``, or ``None``.

    Args:
        main_group: The main dieline group.
        layer: A :class:`DielineLayer` entry or its name string.
    """
    name = getattr(layer, "name", layer)
    for obj in main_group.Group:
        # Match by prefix: FreeCAD may auto-suffix duplicate labels (Cut009).
        if obj.Label.startswith(name):
            return obj
    return None


def _apply_layer_style(group_layer, obj, label=None):
    """Apply the colour/draw style implied by ``group_layer`` to ``obj``."""
    layer = DielineLayer.for_label(group_layer.Label)
    if layer is None:
        layer = DielineLayer.for_label(getattr(group_layer, "Name", ""))
    if label:
        obj.Label = label
    if layer is not None and getattr(obj, "ViewObject", None) is not None:
        obj.ViewObject.LineColor = layer.color
        obj.ViewObject.DrawStyle = layer.draw_style
    return obj


def add_line(group_layer, p1, p2, label=None):
    """Create a Draft line inside ``group_layer`` styled by its layer.

    Args:
        group_layer: The Cut/Crease/Perforation sub-group.
        p1: Start point as an ``(x, y, z)`` tuple.
        p2: End point as an ``(x, y, z)`` tuple.
        label: Optional label for the created object.

    Returns:
        The created Draft line object.
    """
    import Draft
    import FreeCAD

    line = Draft.make_line(FreeCAD.Vector(*p1), FreeCAD.Vector(*p2))
    _apply_layer_style(group_layer, line, label)
    group_layer.addObject(line)
    return line


def add_polyline(group_layer, points, closed=False, label=None):
    """Create a Draft polyline inside ``group_layer`` styled by its layer.

    Args:
        group_layer: The Cut/Crease/Perforation sub-group.
        points: Iterable of ``(x, y, z)`` tuples.
        closed: Whether to close the polyline.
        label: Optional label for the created object.

    Returns:
        The created Draft wire object.
    """
    import Draft
    import FreeCAD

    vectors = [FreeCAD.Vector(*p) for p in points]
    wire = Draft.make_wire(vectors, closed=closed)
    _apply_layer_style(group_layer, wire, label)
    group_layer.addObject(wire)
    return wire
