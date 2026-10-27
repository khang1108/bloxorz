"""A* Search algorithm using admissible heuristic functions for Bloxorz."""

from __future__ import annotations

import heapq
import itertools
import math
from typing import Callable, Dict, List, Optional, Tuple, Union

from bloxorz.core.block import BaseBlockState, BlockState, SplitBlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import BlockOrientation, Direction, TileType
from bloxorz.solvers.base import (
    BaseSolver,
    SearchNode,
    SolverAction,
    SolverResult,
    StateKey,
)
from bloxorz.solvers.costs import CostFunction, fragile_cost

AstarSolverResult = SolverResult
__all__ = ["AstarSolver", "AstarSolverResult"]


class AstarSolver(BaseSolver):
    """A* search algorithm implementation for Bloxorz puzzles.

    Combines cumulative path cost g(n) with an admissible heuristic h(n)
    estimating the remaining distance/cost to the goal:
        f(n) = g(n) + h(n)

    Guarantees optimal solution when h(n) is admissible (h(n) <= h*(n)).
    Uses Min-Heap priority queue ordered by f(n), breaking ties by h(n)
    (favouring states closer to the goal).
    """

    def __init__(
        self,
        cost_fn: CostFunction = fragile_cost,
        heuristic_fn: Optional[Callable[[BaseBlockState, Board], float]] = None,
    ) -> None:
        super().__init__(name="A*")
        self.cost_fn: CostFunction = cost_fn
        self.heuristic_fn: Callable[[BaseBlockState, Board], float] = (
            heuristic_fn if heuristic_fn is not None else self.heuristic
        )

    @staticmethod
    def heuristic(block: BaseBlockState, board: Board) -> float:
        """Admissible heuristic function h(n) estimating the cost to reach the goal.

        For a unified 1x1x2 block:
            In a single roll, the block can cover at most 2 Manhattan distance units
            towards the goal. Therefore, the minimum number of rolls required is
            ceil(min_distance / 2.0).
            If min_distance == 0 but the block is not standing upright, it requires
            at least 2 rolls to stand on the goal hole.

        For a split block (two 1x1x1 unit cubes):
            The two cubes must move to adjacent cells (|x1 - x2| + |y1 - y2| = 1)
            to merge into a single 1x1x2 block, which requires at least
            max(0, dist_between_cubes - 1) moves.
            Once merged, the resulting block requires at least
            ceil(min(dist1_to_goal, dist2_to_goal) / 2.0) rolls to reach the goal.

        Because step costs for physical rolls are at least 1.0 (fragile_cost charges
        >= 1.0, and control switches cost 0.0), h(n) is strictly admissible:
            h(n) <= h*(n) for all states n.
        """
        gx, gy = board.goal_pos

        if isinstance(block, SplitBlockState):
            c1 = block.cube1 if hasattr(block, "cube1") else (block.b1.x, block.b1.y)
            c2 = block.cube2 if hasattr(block, "cube2") else (block.b2.x, block.b2.y)

            dist_between = abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
            merge_cost = max(0, dist_between - 1)

            d1 = abs(c1[0] - gx) + abs(c1[1] - gy)
            d2 = abs(c2[0] - gx) + abs(c2[1] - gy)
            goal_cost = math.ceil(min(d1, d2) / 2.0)

            return float(merge_cost + goal_cost)

        occupied = block.occupied_cells
        if not occupied:
            return 0.0

        min_d = min(abs(x - gx) + abs(y - gy) for x, y in occupied)

        if min_d == 0:
            if getattr(block, "orientation", None) == BlockOrientation.STANDING:
                return 0.0
            return 2.0

        return float(math.ceil(min_d / 2.0))

    def _search_state_key(self, block: BaseBlockState, board: Board) -> StateKey:
        """Preserves cube labels for arbitrary costs that may depend on active_index."""
        key = self.get_state_key(block, board)
        if self.cost_fn is not fragile_cost and isinstance(block, SplitBlockState):
            return ((True, block.b1, block.b2, block.active_index), key[1])
        return key

    def search(self, board: Board) -> SolverResult:
        """Executes A* search from spawn to the goal hole.

        Priority queue items: (f_score, h_score, tie_breaker_counter, node).
        Goal test is performed when a node is dequeued (popped) from the frontier
        to ensure optimality.
        """
        for tiles in (board.base_tiles, board.current_tiles):
            for coordinate, tile in tiles.items():
                if tile == TileType.TELEPORT and coordinate not in board.teleports:
                    raise ValueError(f"Invalid teleport at {coordinate}: destination targets are missing.")

        outcome, _ = board.evaluate_block_state(board.spawn_state)
        if outcome not in ("SAFE", "VICTORY", "TELEPORT"):
            raise ValueError(f"Invalid spawn state: {outcome}")

        if self.is_goal(board.spawn_state, board):
            return SolverResult(
                moves=[],
                is_solved=True,
                visited_count=1,
                expanded_nodes=0,
                max_depth=0,
                message="Goal already reached at spawn.",
                solution_cost=0.0,
            )

        start_node = SearchNode(board.spawn_state, board, cost=0.0, depth=0)
        start_key = self._search_state_key(start_node.block, board)
        start_h = float(self.heuristic_fn(start_node.block, board))

        counter = itertools.count()
        frontier: List[Tuple[float, float, int, SearchNode]] = [
            (start_h, start_h, next(counter), start_node)
        ]
        best_cost: Dict[StateKey, float] = {start_key: 0.0}

        expanded_nodes = 0
        max_depth = 0

        while frontier:
            f_score, h_score, _, node = heapq.heappop(frontier)
            key = self._search_state_key(node.block, node.board)

            if node.cost > best_cost[key]:
                continue

            if self.is_goal(node.block, node.board):
                return SolverResult(
                    moves=node.reconstruct_moves(),
                    is_solved=True,
                    visited_count=len(best_cost),
                    max_depth=max_depth,
                    message="Optimal solution found by A* Search.",
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

                candidate_g = node.cost + step_cost
                if not math.isfinite(candidate_g):
                    raise ValueError("Accumulated path cost must remain finite.")

                successor_key = self._search_state_key(successor.block, successor.board)
                if candidate_g >= best_cost.get(successor_key, math.inf):
                    continue

                best_cost[successor_key] = candidate_g
                succ_h = float(self.heuristic_fn(successor.block, successor.board))
                succ_f = candidate_g + succ_h

                is_physical_roll = (
                    isinstance(successor.direction, Direction)
                    and successor.direction != Direction.SWITCH_CUBE
                )
                child = SearchNode(
                    block=successor.block,
                    board=successor.board,
                    cost=candidate_g,
                    depth=node.depth + int(is_physical_roll),
                    parent=node,
                    direction=successor.direction,
                )
                heapq.heappush(frontier, (succ_f, succ_h, next(counter), child))

        return SolverResult(
            moves=[],
            is_solved=False,
            visited_count=len(best_cost),
            max_depth=max_depth,
            message="No solution: all reachable states have been explored.",
            expanded_nodes=expanded_nodes,
        )
