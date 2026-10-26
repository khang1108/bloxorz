"""Verify the shared route preference against real, legal core transitions."""

import pytest

from bloxorz.core.constants import Direction
from bloxorz.core.level_loader import parse_level_data
from bloxorz.solvers import BaseSolver, fragile_cost


@pytest.mark.parametrize(
    ("layout", "expected"),
    [("1112", 1), ("1312", 3), ("1332", 3), ("1SS2", 1), ("1HH2", 1)],
)
def test_destination_contact_cost(layout: str, expected: float) -> None:
    board = parse_level_data({"layout": [layout], "spawn": {"x": 0, "y": 0}})
    successor = next(
        child for child in BaseSolver.get_successors(board.spawn_state, board)
        if child.direction == Direction.RIGHT
    )
    assert fragile_cost(board.spawn_state, board, successor) == expected


def test_open_bridge_has_normal_cost() -> None:
    board = parse_level_data({
        "layout": ["1BB2"],
        "spawn": {"x": 0, "y": 0},
        "bridges": [{"id": "b1", "tiles": [[1, 0], [2, 0]], "initially_open": True}],
    })
    successor = BaseSolver.get_successors(board.spawn_state, board)[0]
    assert fragile_cost(board.spawn_state, board, successor) == 1


def test_leaving_fragile_for_goal_has_normal_cost() -> None:
    board = parse_level_data({"layout": ["1332"], "spawn": {"x": 0, "y": 0}})
    first = BaseSolver.get_successors(board.spawn_state, board)[0]
    goal = next(
        child for child in BaseSolver.get_successors(first.block, first.board)
        if child.outcome == "VICTORY"
    )
    assert fragile_cost(board.spawn_state, board, first) == 3
    assert fragile_cost(first.block, first.board, goal) == 1


def test_consecutive_fragile_contact_is_charged_per_roll() -> None:
    board = parse_level_data({"layout": ["1331", "1332"], "spawn": {"x": 0, "y": 0}})
    first = next(
        child for child in BaseSolver.get_successors(board.spawn_state, board)
        if child.direction == Direction.RIGHT
    )
    second = next(
        child for child in BaseSolver.get_successors(first.block, first.board)
        if child.direction == Direction.DOWN
    )
    assert fragile_cost(board.spawn_state, board, first) == 3
    assert fragile_cost(first.block, first.board, second) == 3


def test_illegal_fragile_and_void_moves_are_not_successors() -> None:
    board = parse_level_data({"layout": ["13332"], "spawn": {"x": 0, "y": 0}})
    successors = BaseSolver.get_successors(board.spawn_state, board)
    assert [child.direction for child in successors] == [Direction.RIGHT]
    first = successors[0]
    assert [child.direction for child in BaseSolver.get_successors(first.block, first.board)] == [Direction.LEFT]
