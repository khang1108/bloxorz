from __future__ import annotations

from typing import Callable, Optional

from bloxorz.core.block import BlockState
from bloxorz.core.board import Board
from bloxorz.solvers import SolverResult, BaseSolver


class AstarSolver(BaseSolver):
    """
    A* search algorithm implementation for Bloxorz puzzles.

    Author: Phuc-Khang Nguyen
    Date: 24 Oct, 2026
    """

    def __init__(
        self,
        heuristic_fn: Optional[Callable[[BlockState, Board], int]] = None,
    ):
        super().__init__(name="A* Solver")
        self.heuristic_fn = heuristic_fn or self.heuristic

    @staticmethod
    def heuristic(block: BlockState, board: Board) -> int:
        """
        Heuristic function to calculate the cost of each move

        Args:
            block: The current block state
            board: The current board state

        Returns:
            The heuristic value
        """
        return 0

    def search(self, board: Board) -> SolverResult:
        return SolverResult(solved=False, moves=[], nodes_explored=0, elapsed_seconds=0.0)
