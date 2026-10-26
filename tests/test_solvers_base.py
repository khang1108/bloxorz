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
    assert key[0] == board.spawn_state.canonical_key()
    assert isinstance(key[1], tuple)

    # 5. Test is_goal helper
    assert BaseSolver.is_goal(board.spawn_state, board) is False


def test_search_node():
    """Verifies that SearchNode is immutable and reconstructs action sequences properly."""
    import pytest
    from dataclasses import FrozenInstanceError
    from bloxorz.solvers.base import SearchNode

    board = load_level_from_file(Path("bloxorz/levels/stage_01.json"))
    root = SearchNode(block=board.spawn_state, board=board, cost=0.0, depth=0)
    assert root.reconstruct_moves() == []

    # Child step 1
    child_1 = SearchNode(
        block=board.spawn_state,
        board=board,
        cost=1.0,
        depth=1,
        parent=root,
        direction=Direction.RIGHT,
    )
    assert child_1.reconstruct_moves() == [Direction.RIGHT]

    # Child step 2
    child_2 = SearchNode(
        block=board.spawn_state,
        board=board,
        cost=2.0,
        depth=2,
        parent=child_1,
        direction=Direction.DOWN,
    )
    assert child_2.reconstruct_moves() == [Direction.RIGHT, Direction.DOWN]

    # Immutability check
    with pytest.raises(FrozenInstanceError):
        child_2.cost = 99.0  # type: ignore

    # Error when a non-root search node has missing direction
    invalid_node = SearchNode(
        block=board.spawn_state,
        board=board,
        cost=3.0,
        depth=3,
        parent=child_2,
        direction=None,
    )
    with pytest.raises(RuntimeError, match="must have an incoming direction"):
        invalid_node.reconstruct_moves()

