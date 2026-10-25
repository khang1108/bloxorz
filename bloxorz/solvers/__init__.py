"""Bloxorz solvers package."""

from typing import Dict, Optional, Type
from bloxorz.solvers.base import BaseSolver, SolverResult, Successor
from bloxorz.solvers.bfs import BFSSolver, BFSSolverResult, SolverAction
from bloxorz.solvers.astar import AstarSolver

SOLVER_REGISTRY: Dict[str, Optional[Type[BaseSolver]]] = {
    "BFS": BFSSolver,
    "DFS": None,  # Coming soon
    "UCS": None,  # Coming soon
    "A*": AstarSolver,  # Coming soon / in progress
}


def get_solver(name: str) -> Optional[BaseSolver]:
    """Returns an instantiated solver by algorithm name, or None if not implemented."""
    cls = SOLVER_REGISTRY.get(name.upper().strip())
    if cls is not None:
        return cls()
    return None


__all__ = [
    "BaseSolver",
    "SolverResult",
    "Successor",
    "BFSSolver",
    "BFSSolverResult",
    "AstarSolver",
    "SolverAction",
    "SOLVER_REGISTRY",
    "get_solver",
]
