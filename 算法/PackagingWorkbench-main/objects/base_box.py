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
"""Reusable base class for parametric cardboard box features.

``BaseBox`` is the ``Proxy`` of a ``Part::FeaturePython`` object. It declares
the properties shared by every box type (cardboard thickness and closing
allowance) and provides small geometry helpers. Concrete box types (FEFCO 0201,
tray+lid, tuck-end) subclass it and implement :meth:`execute`.
"""

from __future__ import annotations


class BaseBox:
    """Common ``Proxy`` behaviour for box features.

    Subclasses must implement :meth:`execute` and should call
    :meth:`_add_common_properties` (done here in ``__init__``) plus add their
    own dimension properties.
    """

    def __init__(self, obj):
        """Bind this proxy to ``obj`` and declare the common properties.

        Args:
            obj: The host ``Part::FeaturePython`` document object.
        """
        obj.Proxy = self
        self._add_common_properties(obj)

    # -- property setup -----------------------------------------------------

    def _add_common_properties(self, obj):
        """Declare properties shared by all box types."""
        self._add_property(
            obj, "App::PropertyLength", "Thickness", "Material",
            "Cardboard sheet thickness", 3.0,
        )
        self._add_property(
            obj, "App::PropertyLength", "Allowance", "Material",
            "Clearance added for closing/folding", 1.0,
        )

    def _add_property(self, obj, prop_type, name, group, doc, default):
        """Add a property once and set its default.

        Idempotent: safe to call again on a restored object whose properties
        already exist.

        Args:
            obj: Host document object.
            prop_type: FreeCAD property type, e.g. ``"App::PropertyLength"``.
            name: Property name.
            group: Property group shown in the editor.
            doc: Tooltip/documentation string.
            default: Initial value, applied only when the property is created.
        """
        if name not in obj.PropertiesList:
            obj.addProperty(prop_type, name, group, doc)
            setattr(obj, name, default)

    # -- geometry helpers ---------------------------------------------------

    def _make_panel(self, dx, dy, dz, origin=(0.0, 0.0, 0.0)):
        """Return a solid rectangular panel (a box) with real thickness.

        Args:
            dx: Extent along X (mm).
            dy: Extent along Y (mm).
            dz: Extent along Z (mm).
            origin: ``(x, y, z)`` of the panel's minimum corner (mm).

        Returns:
            A ``Part.Solid`` box.
        """
        import FreeCAD
        import Part

        return Part.makeBox(dx, dy, dz, FreeCAD.Vector(origin[0], origin[1], origin[2]))

    # -- lifecycle ----------------------------------------------------------

    def execute(self, obj):
        """Build the shape. Subclasses must override."""
        raise NotImplementedError("Subclasses must implement execute()")

    # -- serialization ------------------------------------------------------
    # FreeCAD 1.0 uses dumps/loads; __getstate__/__setstate__ are kept for
    # compatibility. All return None: there is no Python-side state to persist
    # (everything lives in the object's properties), and returning self.__dict__
    # would break serialization of the FeaturePython proxy.

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None
