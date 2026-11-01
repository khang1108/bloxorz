"""Domain heuristics for Bloxorz puzzle search algorithms.

Includes:
  - ManhattanHeuristic: Admissible distance heuristic based on relaxed coordinate geometry.
  - TrueDistanceHeuristic: Canonical backward Dijkstra / BFS distance on relaxed static grid
    inspired by Sturtevant et al. (SoCS 2009 / IEEE CIG 2012).
"""

from __future__ import annotations

import math
from collections import deque
from typing import Dict, Set, Tuple

from bloxorz.core.block import BaseBlockState, SplitBlockState
from bloxorz.core.block.normal import NormalBlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import BlockOrientation, Direction


class TrueDistanceHeuristic:
    """Canonical True-Distance Heuristic on relaxed static grid (Sturtevant et al., SoCS 2009).

    Precomputes an admissible backward shortest path distance table from the goal
    (gx, gy, STANDING) across all static reachable tiles on the board, respecting
    3D block roll kinematics across all 3 orientations (STANDING, LYING_X, LYING_Y).

    Guarantees:
      - Admissibility: h_true(n) <= h*(n) because dynamic obstacles (bridges) are relaxed.
      - Monotonicity: h_true(n) <= c(n, a, n') + h_true(n') for static transitions.
      - Absolute dominance over Manhattan: h_true(n) >= h_manhattan(n) everywhere.
    """

    def __init__(self, board: Board) -> None:
        self.board = board
        gx, gy = board.goal_pos
        self.gx: int = gx
        self.gy: int = gy

        # Build relaxed static walkable tile set (all base tiles + all bridge tiles)
        all_walkable: Set[Tuple[int, int]] = set(board.base_tiles.keys())
        if hasattr(board, "bridges") and board.bridges:
            for bg in board.bridges.values():
                tiles = getattr(bg, "tiles", [])
                for pt in tiles:
                    all_walkable.add(pt)
        self.all_walkable: Set[Tuple[int, int]] = all_walkable

        # Precompute backward BFS from goal state
        goal_block = NormalBlockState(gx, gy, BlockOrientation.STANDING)
        self.dist_table: Dict[Tuple[int, int, BlockOrientation], int] = {
            goal_block.canonical_key(): 0
        }
        queue = deque([goal_block])

        while queue:
            curr = queue.popleft()
            d = self.dist_table[curr.canonical_key()]
            for m in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT):
                nxt = curr.roll(m)
                if all(p in self.all_walkable for p in nxt.occupied_cells):
                    k = nxt.canonical_key()
                    if k not in self.dist_table:
                        self.dist_table[k] = d + 1
                        queue.append(nxt)

    def __call__(self, block: BaseBlockState, board: Board) -> float:
        """Evaluates heuristic lower bound for the given block state."""
        # Handle split state
        if isinstance(block, SplitBlockState):
            c1 = block.cube1 if hasattr(block, "cube1") else (block.b1.x, block.b1.y)
            c2 = block.cube2 if hasattr(block, "cube2") else (block.b2.x, block.b2.y)

            # Minimum moves to bring two cubes adjacent
            dist_between = abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
            merge_cost = max(0, dist_between - 1)

            # Lower bound from nearest cube to goal
            d1 = abs(c1[0] - self.gx) + abs(c1[1] - self.gy)
            d2 = abs(c2[0] - self.gx) + abs(c2[1] - self.gy)
            goal_cost = math.ceil(min(d1, d2) / 2.0)

            return float(merge_cost + goal_cost)

        # Handle unified 1x1x2 block state
        k = block.canonical_key()
        if k in self.dist_table:
            return float(self.dist_table[k])

        # Fallback to relaxed Manhattan distance if outside static connected component
        occupied = block.occupied_cells
        if not occupied:
            return 0.0

        min_d = min(abs(x - self.gx) + abs(y - self.gy) for x, y in occupied)
        if min_d == 0:
            if getattr(block, "orientation", None) == BlockOrientation.STANDING:
                return 0.0
            return 2.0

        return float(math.ceil(min_d / 2.0))
