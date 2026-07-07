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
"""GUI bootstrap for the Packaging workbench.

FreeCAD executes this file at GUI startup, injecting ``Workbench``, ``Gui``
(FreeCADGui) and ``App`` (FreeCAD) as globals into the execution namespace.

IMPORTANT: the base class is the injected global ``Workbench`` -- NOT
``FreeCADGui.Workbench``. Every core/addon workbench (A2plus, Assembly4,
SheetMetal, Woodworking) subclasses the bare ``Workbench`` global and calls the
bare ``Gui.addWorkbench`` -- we do the same.

Two FreeCAD-specific constraints shaped this file:

1. ``__file__`` is NOT defined here -- ``RunInitGuiPy`` ``exec``s the file as a
   compiled string, so ``os.path.dirname(__file__)`` would raise ``NameError``.
2. The file is exec'd with *separate* globals/locals dicts, so module-level
   names are invisible inside the class body and methods. Anything a method or
   the class body needs must be a literal or a local import.

Both are handled by resolving the icon inside ``__init__`` with a local import
(the A2plus pattern), rather than from a module-level variable.
"""

class PackagingWorkbench(Workbench):  # noqa: F821 - `Workbench` injected by FreeCAD
    """The Packaging workbench definition seen by FreeCAD's workbench selector.

    Heavy imports (commands, scripted objects) are deferred to ``Initialize``
    so importing this module at startup remains cheap, as required by the
    FreeCAD addon guidelines.
    """

    # FreeCAD reads these class attributes during ``addWorkbench``. Plain string
    # literals are safe in the class body; the icon path needs a module lookup,
    # which is NOT reliable here (RunInitGuiPy exec's this file with separate
    # globals/locals, so module-level names are invisible inside the class body
    # and methods). It is therefore resolved in ``__init__`` with a local
    # import, exactly as A2plus does.
    MenuText = "Packaging"
    ToolTip = "Parametric design of cardboard boxes and dielines (FEFCO standards)"
    Icon = ""

    def __init__(self):
        # Local import: a name bound in this method's own scope is immune to the
        # globals/locals split that breaks module-level references here.
        from PackagingWB import icon_path

        self.__class__.Icon = icon_path("Packaging.svg")

    def Initialize(self):
        """Populate toolbars and menus the first time the workbench is shown."""
        # Lazy import: the actual workbench logic lives in PackagingWB.
        from PackagingWB import PackagingWorkbenchManager

        self._manager = PackagingWorkbenchManager()
        commands = self._manager.register_commands()

        # Toolbars and menus are empty in Step 1 (scaffold); commands are added
        # in later steps. FreeCAD raises if ``appendToolbar``/``appendMenu`` is
        # given an empty list, so only register when there is something to show.
        if commands:
            self.appendToolbar("Packaging", commands)
            self.appendMenu("Packaging", commands)

    def Activated(self):
        """Called when the user switches to this workbench."""
        return

    def Deactivated(self):
        """Called when the user switches away from this workbench."""
        return

    def GetClassName(self):
        """Return the C++ class name this Python workbench maps to."""
        return "Gui::PythonWorkbench"


Gui.addWorkbench(PackagingWorkbench())  # noqa: F821 - `Gui` injected by FreeCAD
