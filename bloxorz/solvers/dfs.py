"""Depth-First Search (DFS) for Bloxorz.

Author: Member 3
Assignment: Project 1 - Bloxorz Solver (Introduction to Artificial Intelligence)
"""

from typing import List, Tuple, Set, Union
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
    ):
        super().__init__(name=name)
        self.max_depth = max_depth

    def search(self, board: Board) -> SolverResult:
        """Executes Depth-First Search on the given board configuration."""
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
