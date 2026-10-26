"""Uniform-cost graph search using the shared Bloxorz transition rules."""

import heapq
import itertools
import math
from typing import Dict, List, Optional, Tuple

from bloxorz.core.block import BaseBlockState, SplitBlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import Direction, TileType
from bloxorz.solvers.base import BaseSolver, SearchNode, SolverAction, SolverResult, StateKey
from bloxorz.solvers.costs import CostFunction, fragile_cost

_SearchNode = SearchNode


class UCSSolver(BaseSolver):
    """Find a minimum-cost solution from a freshly loaded stage's spawn state.

    State identity includes both block placement and every bridge configuration.
    Costs must be finite and non-negative; the default charges 1 or 3 per roll.
    The caller's board is not mutated. Successors use the shared core's teleport,
    active-cube selection and merge rules. Default control switches cost zero.
    """

    def __init__(self, cost_fn: CostFunction = fragile_cost) -> None:
        super().__init__(name="UCS")
        self.cost_fn: CostFunction = cost_fn

    def search(self, board: Board) -> SolverResult:
        """Search from spawn, returning a path only when its goal is dequeued.

        Raises:
            ValueError: Teleport targets are missing, spawn is invalid, or a cost is invalid.

        ``visited_count`` counts discovered state keys, ``expanded_nodes`` counts
        calls to successor generation, and ``max_depth`` is the deepest expanded
        path in physical rolls. Goals and stale heap entries are not expanded.
        """
        for tiles in (board.base_tiles, board.current_tiles):
            for coordinate, tile in tiles.items():
                if tile == TileType.TELEPORT and coordinate not in board.teleports:
                    raise ValueError(f"Invalid teleport at {coordinate}: destination targets are missing.")

        outcome, _ = board.evaluate_block_state(board.spawn_state)
        if outcome not in ("SAFE", "VICTORY", "TELEPORT"):
            raise ValueError(f"Invalid spawn state: {outcome}")

        start = SearchNode(board.spawn_state, board)
        counter = itertools.count()
        frontier: List[Tuple[float, int, SearchNode]] = [(0.0, next(counter), start)]
        best_cost: Dict[StateKey, float] = {self._search_state_key(start.block, board): 0.0}
        expanded_nodes = 0
        max_depth = 0

        while frontier:
            _, _, node = heapq.heappop(frontier)
            key = self._search_state_key(node.block, node.board)
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
                successor_key = self._search_state_key(successor.block, successor.board)
                if candidate_cost >= best_cost.get(successor_key, math.inf):
                    continue

                best_cost[successor_key] = candidate_cost
                child = SearchNode(
                    successor.block, successor.board, candidate_cost,
                    node.depth + int(isinstance(successor.direction, Direction)), node, successor.direction,
                )
                heapq.heappush(frontier, (candidate_cost, next(counter), child))

        return SolverResult(
            visited_count=len(best_cost),
            max_depth=max_depth,
            message="No solution: all reachable states have been explored.",
            expanded_nodes=expanded_nodes,
        )

    def _search_state_key(self, block: BaseBlockState, board: Board) -> StateKey:
        """Preserve cube labels for arbitrary costs that may depend on active_index.

        The default cost is invariant under relabeling, so its smaller canonical
        state space remains safe. A caller-supplied function has no such guarantee.
        """
        key = self.get_state_key(block, board)
        if self.cost_fn is not fragile_cost and isinstance(block, SplitBlockState):
            return ((True, block.b1, block.b2, block.active_index), key[1])
        return key

    @staticmethod
    def _reconstruct_moves(node: SearchNode) -> List[SolverAction]:
        """Follow the selected goal's parent chain back to the spawn state."""
        return node.reconstruct_moves()
