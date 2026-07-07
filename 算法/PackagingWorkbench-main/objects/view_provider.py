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
"""ViewProvider for box features.

Provides the tree icon and standard view behaviour for the parametric box
objects. Display of the geometry itself is handled by FreeCAD's default
Part view provider.
"""

from __future__ import annotations


class BoxViewProvider:
    """Minimal ViewProvider shared by all box features."""

    def __init__(self, vobj):
        """Bind this view provider to the object's ViewObject.

        Args:
            vobj: The ``ViewObject`` (``Gui.ViewProviderDocumentObject``).
        """
        vobj.Proxy = self

    def attach(self, vobj):
        """Keep a reference to the owning object when attached."""
        self.Object = vobj.Object

    def getIcon(self):
        """Return the path to the tree icon for box features."""
        from PackagingWB import icon_path

        return icon_path("FEFCO0201.svg")

    # Serialization: no Python-side state to persist (see BaseBox notes).

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None
