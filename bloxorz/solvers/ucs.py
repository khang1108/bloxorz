"""Uniform-cost graph search using the shared Bloxorz transition rules."""

import heapq
import itertools
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from bloxorz.core.block import BlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import Direction, TileType
from bloxorz.solvers.base import BaseSolver, SolverResult
from bloxorz.solvers.costs import CostFunction, fragile_cost


StateKey = Tuple[BlockState, Tuple[Tuple[str, bool], ...]]


@dataclass(frozen=True)
class _SearchNode:
    """An immutable path record so improved routes cannot overwrite old parents."""

    block: BlockState
    board: Board
    cost: float = 0.0
    depth: int = 0
    parent: Optional["_SearchNode"] = None
    direction: Optional[Direction] = None


class UCSSolver(BaseSolver):
    """Find a minimum-cost solution from a freshly loaded stage's spawn state.

    State identity includes both block placement and every bridge configuration.
    Costs must be finite and non-negative; the default charges 1 or 3 per roll.
    The caller's board is not mutated. Successor generation is delegated to the
    shared core, so its bridge-cloning bug must be fixed before bridge levels can
    be certified. Teleport/split levels are explicitly unsupported for now.
    """

    def __init__(self, cost_fn: CostFunction = fragile_cost) -> None:
        super().__init__(name="UCS")
        self.cost_fn: CostFunction = cost_fn

    def search(self, board: Board) -> SolverResult:
        """Search from spawn, returning a path only when its goal is dequeued.

        Raises:
            NotImplementedError: The board contains teleport/split tiles.
            ValueError: Spawn is invalid, or a supplied cost is invalid.

        ``visited_count`` counts discovered state keys, ``expanded_nodes`` counts
        calls to successor generation, and ``max_depth`` is the deepest expanded
        path. Goals and stale heap entries are not counted as expanded nodes.
        """
        if TileType.TELEPORT in board.base_tiles.values() or TileType.TELEPORT in board.current_tiles.values():
            raise NotImplementedError("UCS cannot solve teleport/split levels until the core supports split states.")

        outcome, _ = board.evaluate_block_state(board.spawn_state)
        if outcome not in ("SAFE", "VICTORY"):
            raise ValueError(f"Invalid spawn state: {outcome}")

        start = _SearchNode(board.spawn_state, board)
        counter = itertools.count()
        frontier: List[Tuple[float, int, _SearchNode]] = [(0.0, next(counter), start)]
        best_cost: Dict[StateKey, float] = {self.get_state_key(start.block, board): 0.0}
        expanded_nodes = 0
        max_depth = 0

        while frontier:
            _, _, node = heapq.heappop(frontier)
            key = self.get_state_key(node.block, node.board)
            if node.cost != best_cost[key]:
                continue

            if self.is_goal(node.block, node.board):
                return SolverResult(
                    moves=self._reconstruct_moves(node),
                    is_solved=True,
                    visited_count=len(best_cost),
                    max_depth=max_depth,
                    message="Minimum-cost solution found.",
                    expanded_nodes=expanded_nodes,
                    solution_cost=node.cost,
                )

            expanded_nodes += 1
            max_depth = max(max_depth, node.depth)
            for successor in self.get_successors(node.block, node.board):
                raw_cost = self.cost_fn(node.block, node.board, successor)
                try:
                    step_cost = float(raw_cost)
                except (TypeError, ValueError, OverflowError) as error:
                    raise ValueError("Step cost must be finite and non-negative.") from error
                if not math.isfinite(step_cost) or step_cost < 0:
                    raise ValueError("Step cost must be finite and non-negative.")

                candidate_cost = node.cost + step_cost
                if not math.isfinite(candidate_cost):
                    raise ValueError("Accumulated path cost must remain finite.")
                successor_key = self.get_state_key(successor.block, successor.board)
                if candidate_cost >= best_cost.get(successor_key, math.inf):
                    continue

                best_cost[successor_key] = candidate_cost
                child = _SearchNode(
                    successor.block, successor.board, candidate_cost,
                    node.depth + 1, node, successor.direction,
                )
                heapq.heappush(frontier, (candidate_cost, next(counter), child))

        return SolverResult(
            visited_count=len(best_cost),
            max_depth=max_depth,
            message="No solution: all reachable states have been explored.",
            expanded_nodes=expanded_nodes,
        )

    @staticmethod
    def _reconstruct_moves(node: _SearchNode) -> List[Direction]:
        """Follow the selected goal's parent chain back to the spawn state."""
        moves: List[Direction] = []
        while node.parent is not None:
            if node.direction is None:
                raise RuntimeError("A non-root search node must have an incoming direction.")
            moves.append(node.direction)
            node = node.parent
        moves.reverse()
        return moves
