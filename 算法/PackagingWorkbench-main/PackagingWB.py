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
"""Main implementation module for the Packaging workbench.

Kept lightweight (stdlib-only imports) so :mod:`InitGui` can import it at
startup just to resolve resource paths; the heavy command/object imports happen
lazily inside :meth:`PackagingWorkbenchManager.register_commands`.
"""

# Defer annotation evaluation so generic builtins like ``list[str]`` parse on
# any Python this code might run under, not only 3.9+.
from __future__ import annotations

import os

# Absolute path to the addon root, used to resolve resource files.
ADDON_DIR = os.path.dirname(__file__)
ICON_DIR = os.path.join(ADDON_DIR, "resources", "icons")


def icon_path(name: str) -> str:
    """Return the absolute path to an icon shipped with the workbench.

    Args:
        name: File name of the icon inside ``resources/icons`` (e.g.
            ``"Packaging.svg"``).

    Returns:
        Absolute filesystem path to the icon.
    """
    return os.path.join(ICON_DIR, name)


class PackagingWorkbenchManager:
    """Owns command registration for the Packaging workbench.

    Keeping this logic out of :mod:`InitGui` lets the GUI bootstrap stay
    lightweight and makes the command set easy to unit-test without a running
    GUI.
    """

    def register_commands(self) -> list[str]:
        """Register all workbench commands with FreeCAD.

        Imports of command modules are kept local (lazy) so this module stays
        cheap to import at startup.

        Returns:
            The ordered list of command identifiers to place on the toolbar and
            menu, in display order.
        """
        from commands import (
            cmd_fefco0201,
            cmd_fefco0301,
            cmd_fefco0713,
            cmd_generate_dieline,
            cmd_hello_box,
        )

        command_ids: list[str] = []
        command_ids.append(cmd_hello_box.register())
        command_ids.append(cmd_fefco0201.register())
        command_ids.append(cmd_fefco0301.register())
        command_ids.append(cmd_fefco0713.register())
        command_ids.append(cmd_generate_dieline.register())
        return command_ids
