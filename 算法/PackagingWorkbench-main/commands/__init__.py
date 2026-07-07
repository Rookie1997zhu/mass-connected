# SPDX-License-Identifier: LGPL-2.1-or-later
"""GUI commands for the Packaging workbench.

Each module in this package defines a single FreeCAD command class registered
via ``FreeCADGui.addCommand``. Commands are imported lazily by
:class:`PackagingWB.PackagingWorkbenchManager` to keep startup fast.
"""
