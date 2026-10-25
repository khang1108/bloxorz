#!/usr/bin/env python3
"""Root launcher and programmatic entry point for Bloxorz 3D with Solver support."""

import sys
from pathlib import Path
from typing import Optional, Callable, List

# Add project root to sys.path
root_dir = Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ursina import Ursina  # noqa: E402
from bloxorz.core.constants import Direction  # noqa: E402
from bloxorz.core.board import Board  # noqa: E402
from bloxorz.solvers.dfs import DFSSolver  # noqa: E402
from bloxorz.main import BloxorzApp  # noqa: E402


def launch(solver: Optional[Callable[[Board], List[Direction]]] = None) -> BloxorzApp:
    """Launches the 3D Bloxorz app, optionally binding a custom solver function."""
    app = Ursina()
    bloxorz = BloxorzApp()

    # Register solver (default to DFSSolver if not specified)
    active_solver = solver or DFSSolver()
    bloxorz.register_solver(active_solver)

    app.run()
    return bloxorz


if __name__ == "__main__":
    launch()
