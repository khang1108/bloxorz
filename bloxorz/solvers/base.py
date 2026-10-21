"""Abstract base class and data contracts for Bloxorz puzzle solvers."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple

from bloxorz.core.constants import Direction
from bloxorz.core.block import BlockState
from bloxorz.core.board import Board


@dataclass
class SolverResult:
    """Encapsulates the output and performance metrics of a solver execution."""
    moves: List[Direction] = field(default_factory=list)
    is_solved: bool = False
    visited_count: int = 0
    execution_time_ms: float = 0.0
    max_depth: int = 0
    message: str = ""

    def summary(self) -> str:
        """Returns a formatted one-line performance summary."""
        status = "SOLVED" if self.is_solved else "FAILED"
        return (
            f"[{status}] Moves: {len(self.moves)} | "
            f"Visited States: {self.visited_count} | "
            f"Depth: {self.max_depth} | "
            f"Time: {self.execution_time_ms:.2f} ms"
        )


@dataclass(frozen=True)
class Successor:
    """Represents a valid transition in the state-space graph."""
    direction: Direction
    block: BlockState
    board: Board
    outcome: str  # 'SAFE' or 'VICTORY'


class BaseSolver(ABC):
    """Abstract base class for all Bloxorz search algorithms.

    Subclasses must implement the `search()` method.
    Instances can be passed directly as callbacks to `BloxorzApp.register_solver()`
    or `run.launch(solver=...)` via the `__call__` interface.
    """

    def __init__(self, name: str = "BaseSolver"):
        self.name: str = name

    @staticmethod
    def get_state_key(block: BlockState, board: Board) -> Tuple[BlockState, Tuple[Tuple[str, bool], ...]]:
        """Generates a canonical hashable key for state-space graph search.

        Combines the immutable BlockState with the hashable tuple of all bridge states.
        """
        return (block, board.get_bridge_state_key())

    @staticmethod
    def is_goal(block: BlockState, board: Board) -> bool:
        """Determines if the block is standing upright on the goal hole."""
        outcome, _ = board.evaluate_block_state(block)
        return outcome == "VICTORY"

    @classmethod
    def get_successors(cls, block: BlockState, board: Board) -> List[Successor]:
        """Calculates all legal next states from the current block and board configuration.

        Iterates over all 4 directions (UP, RIGHT, DOWN, LEFT). For any move resulting
        in 'SAFE' or 'VICTORY', creates a cloned board, applies switch triggers,
        and yields the successor.
        """
        successors: List[Successor] = []

        for direction in (Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT):
            next_block = block.roll(direction)
            outcome, _ = board.evaluate_block_state(next_block)

            if outcome in ("SAFE", "VICTORY"):
                next_board = board.clone()
                if outcome == "SAFE":
                    next_board.trigger_switches(next_block)

                successors.append(
                    Successor(
                        direction=direction,
                        block=next_block,
                        board=next_board,
                        outcome=outcome,
                    )
                )

        return successors

    def solve(self, board: Board) -> SolverResult:
        """Template execution method with automatic performance benchmarking."""
        start_time = time.perf_counter()
        result = self.search(board)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        result.execution_time_ms = elapsed_ms
        return result

    @abstractmethod
    def search(self, board: Board) -> SolverResult:
        """Core search implementation.

        Args:
            board: The initial Board configuration of the stage.

        Returns:
            SolverResult containing found moves and traversal statistics.
        """
        pass

    def __call__(self, board: Board) -> List[Direction]:
        """Enables passing the solver instance directly as a callback to BloxorzApp."""
        result = self.solve(board)
        return result.moves if result.is_solved else []
