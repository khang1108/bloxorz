from pathlib import Path
from bloxorz.core.constants import Direction
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.core.board import Board
from bloxorz.solvers.base import BaseSolver, SolverResult


class DummySolver(BaseSolver):
    """Minimal dummy solver for testing abstract base contracts."""

    def __init__(self):
        super().__init__(name="DummySolver")

    def search(self, board: Board) -> SolverResult:
        # Simple dummy execution
        return SolverResult(
            moves=[Direction.RIGHT, Direction.DOWN],
            is_solved=True,
            visited_count=4,
            max_depth=2,
            message="Test solution",
        )


def test_base_solver_contracts():
    board = load_level_from_file(Path("bloxorz/levels/stage_01.json"))
    solver = DummySolver()

    # 1. Test solve() template method and benchmarking
    result = solver.solve(board)
    assert result.is_solved is True
    assert result.moves == [Direction.RIGHT, Direction.DOWN]
    assert result.visited_count == 4
    assert result.execution_time_ms >= 0.0
    assert "SOLVED" in result.summary()

    # 2. Test __call__ interface compatibility
    moves = solver(board)
    assert moves == [Direction.RIGHT, Direction.DOWN]

    # 3. Test get_successors() helper
    successors = BaseSolver.get_successors(board.spawn_state, board)
    assert len(successors) > 0
    # From spawn state in stage 1, rolling right or down should be safe
    dirs = [s.direction for s in successors]
    assert Direction.RIGHT in dirs or Direction.DOWN in dirs

    # 4. Test state_key helper
    key = BaseSolver.get_state_key(board.spawn_state, board)
    assert key[0] == board.spawn_state
    assert isinstance(key[1], tuple)

    # 5. Test is_goal helper
    assert BaseSolver.is_goal(board.spawn_state, board) is False
