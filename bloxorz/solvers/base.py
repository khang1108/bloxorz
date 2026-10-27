"""Abstract base class and data contracts for Bloxorz puzzle solvers."""

import time
import tracemalloc
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Literal, Optional, Tuple, Union

from bloxorz.core.constants import Direction
from bloxorz.core.block import BaseBlockState, BlockState
from bloxorz.core.board import Board
from bloxorz.core.game import Game


SWITCH_ACTION: Literal["SWITCH"] = "SWITCH"
SolverAction = Union[Direction, Literal["SWITCH"]]
StateKey = Tuple[tuple, Tuple[Tuple[str, bool], ...]]


@dataclass
class SolverResult:
    """Encapsulates the output and performance metrics of a solver execution."""
    moves: List[SolverAction] = field(default_factory=list)
    is_solved: bool = False
    visited_count: int = 0
    execution_time_ms: float = 0.0
    max_depth: int = 0
    message: str = ""
    expanded_nodes: int = 0
    solution_cost: Optional[float] = None
    peak_memory_kb: float = 0.0

    @property
    def solution_length(self) -> int:
        """Number of physical rolls, excluding control switches as in Game.move_count."""
        return sum(isinstance(action, Direction) for action in self.moves)

    def summary(self) -> str:
        """Returns a formatted one-line performance summary."""
        status = "SOLVED" if self.is_solved else "FAILED"
        cost = "N/A" if self.solution_cost is None else f"{self.solution_cost:g}"
        return (
            f"[{status}] Moves: {self.solution_length} | "
            f"Cost: {cost} | "
            f"Visited: {self.visited_count} | "
            f"Expanded: {self.expanded_nodes} | "
            f"Depth: {self.max_depth} | "
            f"Time: {self.execution_time_ms:.2f} ms | "
            f"Peak Mem: {self.peak_memory_kb:.2f} KB"
        )


@dataclass(frozen=True)
class Successor:
    """Represents a valid transition in the state-space graph."""
    direction: SolverAction
    block: BaseBlockState
    board: Board
    outcome: str  # 'SAFE', 'TELEPORT', 'MERGED' or 'VICTORY'


@dataclass(frozen=True)
class SearchNode:
    """An immutable search tree node shared across pathfinding algorithms (UCS, A*, BFS, DFS).

    Immutable path records ensure that improved routes or alternative search branches
    cannot overwrite old parent pointers or corrupt priority queue order.
    """

    block: BaseBlockState
    board: Board
    cost: float = 0.0
    depth: int = 0
    parent: Optional["SearchNode"] = None
    direction: Optional[SolverAction] = None

    def reconstruct_moves(self) -> List[SolverAction]:
        """Follow the parent chain back to the root search node to extract action sequence."""
        moves: List[SolverAction] = []
        curr: Optional["SearchNode"] = self
        while curr is not None and curr.parent is not None:
            if curr.direction is None:
                raise RuntimeError("A non-root search node must have an incoming direction.")
            moves.append(curr.direction)
            curr = curr.parent
        moves.reverse()
        return moves


class BaseSolver(ABC):
    """Abstract base class for all Bloxorz search algorithms.

    Subclasses must implement the `search()` method.
    Instances can be passed directly as callbacks to `BloxorzApp.register_solver()`
    or `run.launch(solver=...)` via the `__call__` interface.
    """

    def __init__(self, name: str = "BaseSolver"):
        self.name: str = name

    @staticmethod
    def get_state_key(block: BaseBlockState, board: Board) -> StateKey:
        """Generates a canonical hashable key for state-space graph search.

        Canonical block keys remove equivalent cube labels while preserving which
        cube is active. Bridge configurations remain part of the state identity.
        """
        block_key = block.canonical_key() if hasattr(block, "canonical_key") else block
        return (block_key, board.get_bridge_state_key())

    @staticmethod
    def is_goal(block: BaseBlockState, board: Board) -> bool:
        """Determines if the block is standing upright on the goal hole."""
        if getattr(block, "is_split", False):
            return False
        outcome, _ = board.evaluate_block_state(block)
        return outcome == "VICTORY"

    @classmethod
    def get_successors(cls, block: BaseBlockState, board: Board) -> List[Successor]:
        """Calculates all legal next states from the current block and board configuration.

        Delegate all move effects to Game on independent board snapshots so search
        and playback agree about teleports, switches and merging. Split states also
        offer a SWITCH action. Recheck support after effects such as closing bridges
        or teleporting a cube; never return a floating or collapsed successor.
        """
        successors: List[Successor] = []

        actions: List[SolverAction] = [Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT]
        if block.is_split:
            actions.append(SWITCH_ACTION)

        for action in actions:
            branch = Game(board.clone())
            branch.block = block
            if action == SWITCH_ACTION:
                if not branch.switch_block():
                    continue
                outcome = "SAFE"
            else:
                outcome, _, _ = branch.roll(action)

            if outcome not in ("SAFE", "VICTORY", "TELEPORT", "MERGED"):
                continue
            final_outcome, _ = branch.board.evaluate_block_state(branch.block)
            if final_outcome not in ("SAFE", "VICTORY"):
                continue

            successors.append(Successor(action, branch.block, branch.board, outcome))

        return successors

    def solve(self, board: Board) -> SolverResult:
        """Template execution method with automatic performance benchmarking."""
        tracemalloc.start()
        start_time = time.perf_counter()
        result = self.search(board)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result.execution_time_ms = elapsed_ms
        if result.peak_memory_kb <= 0.0:
            result.peak_memory_kb = peak_bytes / 1024.0
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

    def __call__(self, board: Board) -> List[SolverAction]:
        """Return movement/control actions for the BloxorzApp playback callback."""
        result = self.solve(board)
        return result.moves if result.is_solved else []
