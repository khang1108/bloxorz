from collections import deque
from dataclasses import dataclass, field
from time import perf_counter
import tracemalloc
from typing import Iterator, List, Literal, Tuple, Union

from bloxorz.core.block.base import BaseBlockState
from bloxorz.solvers.base import BaseSolver, SolverResult
from bloxorz.core.board import Board
from bloxorz.core.constants import Direction
from bloxorz.core.game import Game


SolverAction = Union[Direction, Literal["_"]]


@dataclass
class BFSSolverResult(SolverResult):
    moves: List[SolverAction] = field(default_factory=list)
    peak_memory_bytes: int = 0
    expanded_nodes: int = 0

    def summary(self) -> str:
        status = "SOLVED" if self.is_solved else "FAILED"
        return (
            f"[{status}] Moves: {len(self.moves)} | "
            f"Visited States: {self.visited_count} | "
            f"Depth: {self.max_depth} | "
            f"Search Time: {self.execution_time_ms:.2f} ms | "
            f"Peak Memory: {self.peak_memory_bytes / 1024:.2f} KiB | "
            f"Expanded Nodes: {self.expanded_nodes}"
        )


class BFSSolver(BaseSolver):
    """Bloxorz Solver using Breadth-First Search Algorithm."""

    def __init__(self):
        super().__init__(name="BFS Solver")

    @staticmethod
    def _state_key(block: BaseBlockState, board: Board) -> tuple:
        return block.canonical_key(), board.get_bridge_state_key()

    @staticmethod
    def _successors(
        block: BaseBlockState,
        board: Board,
    ) -> Iterator[Tuple[SolverAction, BaseBlockState, Board]]:
        if block.is_split:
            switch_game = Game(board.clone())
            switch_game.block = block
            if switch_game.switch_block():
                yield "_", switch_game.block, switch_game.board

        for direction in Direction:
            next_board = board.clone()
            game = Game(next_board)
            game.block = block
            outcome, next_block, _ = game.roll(direction)
            if outcome in ("SAFE", "MERGED", "TELEPORT", "VICTORY"):
                yield direction, next_block, next_board

    def search(
        self,
        board: Board,
        start_block: BaseBlockState | None = None,
    ) -> SolverResult:
        """Search from the spawn state or a supplied live block state.

        The board's current bridge configuration is copied into the initial
        search state, so live-game searches continue from the actual puzzle state.
        """
        started_tracing_here = not tracemalloc.is_tracing()
        if started_tracing_here:
            tracemalloc.start()

        try:
            start_time = perf_counter()
            initial_block = board.spawn_state if start_block is None else start_block
            initial_board = board.clone()
            start_key = self._state_key(initial_block, initial_board)

            queue = deque([(initial_block, initial_board, [])])
            visited = {start_key}
            visited_count = 0
            expanded_nodes = 0
            max_depth = 0

            while queue:
                curr_block, curr_board, path = queue.popleft()
                visited_count += 1
                max_depth = max(max_depth, len(path))

                if self.is_goal(curr_block, curr_board):
                    result = BFSSolverResult(
                        moves=path,
                        is_solved=True,
                        visited_count=visited_count,
                        expanded_nodes=expanded_nodes,
                        max_depth=max_depth,
                        message="Solution found",
                    )
                    break

                expanded_nodes += 1
                for action, next_block, next_board in self._successors(
                    curr_block,
                    curr_board,
                ):
                    next_key = self._state_key(next_block, next_board)

                    if next_key not in visited:
                        visited.add(next_key)
                        queue.append((next_block, next_board, path + [action]))
            else:
                result = BFSSolverResult(
                    moves=[],
                    is_solved=False,
                    visited_count=visited_count,
                    expanded_nodes=expanded_nodes,
                    max_depth=max_depth,
                    message="No solution",
                )

            _, peak_memory_bytes = tracemalloc.get_traced_memory()
            result.peak_memory_bytes = peak_memory_bytes
            result.execution_time_ms = (perf_counter() - start_time) * 1000
            print(result.summary())
            return result
        finally:
            if started_tracing_here:
                tracemalloc.stop()

    def solve_from(
        self,
        board: Board,
        start_block: BaseBlockState,
    ) -> List[SolverAction]:
        """Returns a solution beginning at the supplied live block state."""
        result = self.search(board, start_block)
        return result.moves if result.is_solved else []