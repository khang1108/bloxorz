"""Depth-First Search (DFS) and Iterative Deepening Search (IDS) for Bloxorz.

Author: Member 3
Assignment: Project 1 - Bloxorz Solver (Introduction to Artificial Intelligence)
"""

from typing import List, Tuple, Set, Dict, Optional, Union
from bloxorz.core.constants import Direction
from bloxorz.core.block import BlockState, SplitBlockState
from bloxorz.core.board import Board
from bloxorz.solvers.base import BaseSolver, SolverResult


class DFSSolver(BaseSolver):
    """Depth-First Search (DFS) solver with cycle detection via state hashing.

    Uses an explicit LIFO stack to eliminate recursion overhead and prevent stack overflow.
    Maintains a global visited set of (block_state, bridge_configuration) signatures
    to guarantee termination in cyclic state spaces.
    """

    def __init__(
        self,
        name: str = "DFS Solver",
        max_depth: int = 5000,
        use_ids: bool = False,
    ):
        super().__init__(name=name)
        self.max_depth = max_depth
        self.use_ids = use_ids

    def search(self, board: Board) -> SolverResult:
        """Executes DFS (or IDS if enabled) on the given board configuration."""
        if self.use_ids:
            return self._iterative_deepening_search(board)
        return self._depth_first_search(board)

    def _depth_first_search(self, board: Board) -> SolverResult:
        """Standard graph-search DFS with visited set to prune cycles."""
        start_block = board.spawn_state
        if self.is_goal(start_block, board):
            return SolverResult(
                moves=[],
                is_solved=True,
                visited_count=1,
                expanded_nodes=0,
                max_depth=0,
                message="Goal already reached at spawn",
            )

        start_key = self.get_state_key(start_block, board)
        visited: Set[Tuple[Union[BlockState, SplitBlockState], Tuple[Tuple[str, bool], ...]]] = {start_key}

        # Stack holds: (block, board, moves_path)
        stack: List[Tuple[Union[BlockState, SplitBlockState], Board, List[Direction]]] = [
            (start_block, board, [])
        ]

        expanded_nodes = 0
        max_depth_reached = 0

        while stack:
            current_block, current_board, moves = stack.pop()
            expanded_nodes += 1
            depth = len(moves)
            if depth > max_depth_reached:
                max_depth_reached = depth

            if depth >= self.max_depth:
                continue

            successors = self.get_successors(current_block, current_board)

            # Push in reverse order so the first successor (e.g. UP or RIGHT) is processed first
            for succ in reversed(successors):
                succ_key = self.get_state_key(succ.block, succ.board)
                if succ_key not in visited:
                    visited.add(succ_key)
                    new_moves = moves + [succ.direction]

                    if succ.outcome == "VICTORY" or self.is_goal(succ.block, succ.board):
                        return SolverResult(
                            moves=new_moves,
                            is_solved=True,
                            visited_count=len(visited),
                            expanded_nodes=expanded_nodes,
                            max_depth=max(max_depth_reached, len(new_moves)),
                            message=f"Goal reached at depth {len(new_moves)}",
                        )

                    stack.append((succ.block, succ.board, new_moves))

        return SolverResult(
            moves=[],
            is_solved=False,
            visited_count=len(visited),
            expanded_nodes=expanded_nodes,
            max_depth=max_depth_reached,
            message="No solution found within max depth limit",
        )

    def _iterative_deepening_search(self, board: Board) -> SolverResult:
        """Iterative Deepening Search (IDS): combines DFS space efficiency with BFS optimality."""
        start_block = board.spawn_state
        if self.is_goal(start_block, board):
            return SolverResult(
                moves=[],
                is_solved=True,
                visited_count=1,
                expanded_nodes=0,
                max_depth=0,
                message="Goal reached at spawn",
            )

        total_expanded = 0
        all_visited_count = 0
        limit_depth = min(self.max_depth, 80)

        for limit in range(1, limit_depth + 1):
            result = self._depth_limited_search(board, limit)
            total_expanded += result.expanded_nodes
            all_visited_count = max(all_visited_count, result.visited_count)

            if result.is_solved:
                result.expanded_nodes = total_expanded
                result.visited_count = all_visited_count
                return result

        return SolverResult(
            moves=[],
            is_solved=False,
            visited_count=all_visited_count,
            expanded_nodes=total_expanded,
            max_depth=limit_depth,
            message=f"IDS exhausted limit {limit_depth} without finding goal",
        )

    def _depth_limited_search(self, board: Board, limit: int) -> SolverResult:
        """Depth-Limited Search helper with path-based cycle detection and depth-indexed memoization."""
        start_block = board.spawn_state
        start_key = self.get_state_key(start_block, board)

        # Map state_key -> minimum depth at which it was visited during this iteration
        visited_depth: Dict[Any, int] = {start_key: 0}
        stack: List[Tuple[Union[BlockState, SplitBlockState], Board, List[Direction]]] = [
            (start_block, board, [])
        ]

        expanded_nodes = 0
        max_depth_reached = 0

        while stack:
            current_block, current_board, moves = stack.pop()
            expanded_nodes += 1
            depth = len(moves)
            if depth > max_depth_reached:
                max_depth_reached = depth

            if depth >= limit:
                continue

            successors = self.get_successors(current_block, current_board)

            for succ in reversed(successors):
                succ_key = self.get_state_key(succ.block, succ.board)
                succ_depth = depth + 1

                # Only explore if this state has not been reached at this or shallower depth
                if succ_key not in visited_depth or succ_depth < visited_depth[succ_key]:
                    visited_depth[succ_key] = succ_depth
                    new_moves = moves + [succ.direction]

                    if succ.outcome == "VICTORY" or self.is_goal(succ.block, succ.board):
                        return SolverResult(
                            moves=new_moves,
                            is_solved=True,
                            visited_count=len(visited_depth),
                            expanded_nodes=expanded_nodes,
                            max_depth=max(max_depth_reached, len(new_moves)),
                            message=f"Goal reached at limit {limit}",
                        )

                    stack.append((succ.block, succ.board, new_moves))

        return SolverResult(
            moves=[],
            is_solved=False,
            visited_count=len(visited_depth),
            expanded_nodes=expanded_nodes,
            max_depth=max_depth_reached,
            message="Limit reached without solution",
        )


class IDSSolver(DFSSolver):
    """Iterative Deepening Search (IDS) solver for Bloxorz puzzles."""

    def __init__(self, name: str = "IDS Solver", max_depth: int = 100):
        super().__init__(name=name, max_depth=max_depth, use_ids=True)
