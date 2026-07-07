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
"""Non-GUI initialization for the Packaging workbench.

FreeCAD imports this module on startup in both console and GUI modes. It must
stay lightweight: no GUI imports, no heavy computation. Document-level object
registration (scripted objects usable without the GUI) belongs here.
"""

# Nothing to register at the no-GUI level yet. Scripted objects are imported
# lazily by their commands when first invoked (see commands/ package), so this
# file intentionally stays empty for now.
