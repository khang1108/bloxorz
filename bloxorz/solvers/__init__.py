"""Bloxorz solvers package."""

from typing import Dict, Optional, Type
from bloxorz.solvers.base import BaseSolver, SolverAction, SolverResult, StateKey, Successor, SWITCH_ACTION
from bloxorz.solvers.bfs import BFSSolver, BFSSolverResult
from bloxorz.solvers.dfs import DFSSolver, DFSSolverResult
from bloxorz.solvers.astar import AstarSolver
from bloxorz.solvers.costs import CostFunction, fragile_cost
from bloxorz.solvers.ucs import UCSSolver

SOLVER_REGISTRY: Dict[str, Optional[Type[BaseSolver]]] = {
    "BFS": BFSSolver,
    "DFS": DFSSolver,
    "UCS": UCSSolver,
    "A*": None,  # Coming soon
}


def get_solver(name: str) -> Optional[BaseSolver]:
    """Returns an instantiated solver by algorithm name, or None if not implemented."""
    cls = SOLVER_REGISTRY.get(name.upper().strip())
    if cls is not None:
        return cls()
    return None


__all__ = [
    "BaseSolver",
    "SolverAction",
    "SolverResult",
    "StateKey",
    "Successor",
    "SWITCH_ACTION",
    "BFSSolver",
    "BFSSolverResult",
    "DFSSolver",
    "DFSSolverResult",
    "AstarSolver",
    "CostFunction",
    "fragile_cost",
    "UCSSolver",
    "SOLVER_REGISTRY",
    "get_solver",
]
