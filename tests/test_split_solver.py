"""Search must model the same teleport, control and merge actions as real gameplay."""

from copy import deepcopy
from pathlib import Path
from typing import List

import pytest

from bloxorz.core.block import BaseBlockState, BlockState, SingleBlock, SplitBlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import BlockOrientation, Direction, GameStatus
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file, parse_level_data
from bloxorz.solvers import BaseSolver, SolverAction, SolverResult, Successor, UCSSolver, fragile_cost


LEVELS = Path(__file__).resolve().parents[1] / "bloxorz" / "levels"


def test_split_key_ignores_cube_labels_but_preserves_active_coordinate() -> None:
    board = load_level_from_file(LEVELS / "stage_08.json")
    first = SplitBlockState(SingleBlock(10, 1), SingleBlock(10, 7), 0)
    relabeled = SplitBlockState(SingleBlock(10, 7), SingleBlock(10, 1), 1)
    other_active = first.switch_active()
    assert BaseSolver.get_state_key(first, board) == BaseSolver.get_state_key(relabeled, board)
    assert BaseSolver.get_state_key(first, board) != BaseSolver.get_state_key(other_active, board)


def test_teleport_successor_contains_the_two_real_destination_cubes() -> None:
    board = load_level_from_file(LEVELS / "stage_08.json")
    before_teleport = board.spawn_state.roll(Direction.RIGHT)
    children = BaseSolver.get_successors(before_teleport, board)
    destination = next((child for child in children if child.direction == Direction.RIGHT), None)
    assert destination is not None, "Standing on the configured teleport must be a legal successor."
    assert destination.outcome == "TELEPORT"
    assert destination.block == SplitBlockState(SingleBlock(10, 1), SingleBlock(10, 7), 0)
    assert not before_teleport.is_split


def test_split_control_switch_changes_active_cube_without_moving_or_mutating_board() -> None:
    board = load_level_from_file(LEVELS / "stage_08.json")
    original = deepcopy(board)
    split = SplitBlockState(SingleBlock(10, 1), SingleBlock(10, 7), 0)
    children = BaseSolver.get_successors(split, board)
    selection = next((child for child in children if child.direction == "SWITCH"), None)
    assert selection is not None, "A solver must be able to choose the other cube."
    assert selection.block == SplitBlockState(SingleBlock(10, 1), SingleBlock(10, 7), 1)
    assert selection.board.current_tiles == original.current_tiles
    assert board.current_tiles == original.current_tiles
    assert board.get_bridge_state_key() == original.get_bridge_state_key()


def test_adjacent_cubes_merge_in_successor_before_further_rolls() -> None:
    board = parse_level_data({"layout": ["11111111", "11111112"], "spawn": {"x": 0, "y": 0}})
    split = SplitBlockState(SingleBlock(3, 0), SingleBlock(5, 0), 0)
    children = BaseSolver.get_successors(split, board)
    destination = next(child for child in children if child.direction == Direction.RIGHT)
    assert destination.outcome == "MERGED"
    assert destination.block == BlockState(4, 0, BlockOrientation.LYING_X)


def test_successors_reject_switch_effects_that_remove_support_under_passive_cube() -> None:
    board = load_level_from_file(LEVELS / "stage_15.json")
    game = Game(board)
    directions = {"U": Direction.UP, "D": Direction.DOWN, "L": Direction.LEFT, "R": Direction.RIGHT}
    # This real level prefix ends immediately before closing a bridge under b1.
    for action in "RRRRUU_UUUUURRRUURRRDRDU_LLL_":
        if action == "_":
            assert game.switch_block()
        else:
            game.roll(directions[action])
        assert board.evaluate_block_state(game.block)[0] == "SAFE"
    children = BaseSolver.get_successors(game.block, board)
    assert Direction.DOWN not in [child.direction for child in children]
    assert board.evaluate_block_state(game.block)[0] == "SAFE"


def test_successors_reject_teleport_targets_in_void() -> None:
    board = parse_level_data({
        "layout": ["11111112"], "spawn": {"x": 0, "y": 0},
        "teleports": [{"x": 3, "y": 0, "target_1": [-5, 0], "target_2": [5, 0]}],
    })
    before_teleport = board.spawn_state.roll(Direction.RIGHT)
    assert Direction.RIGHT not in [child.direction for child in BaseSolver.get_successors(before_teleport, board)]


def replay_split_solution(board: Board, actions: List[SolverAction]) -> Game:
    """Use real manual-play methods and verify support after every action."""
    game = Game(deepcopy(board))
    for action in actions:
        if action == "SWITCH":
            previous_count = game.move_count
            assert game.switch_block()
            assert game.move_count == previous_count
        else:
            outcome, _, _ = game.roll(action)
            assert outcome in ("SAFE", "TELEPORT", "MERGED", "VICTORY")
        assert game.board.evaluate_block_state(game.block)[0] in ("SAFE", "VICTORY")
    assert game.status == GameStatus.VICTORY
    return game


def test_ucs_solves_stage_eight_with_zero_cost_control_switch() -> None:
    board = load_level_from_file(LEVELS / "stage_08.json")
    result = UCSSolver().solve(board)
    assert result.is_solved
    assert "SWITCH" in result.moves
    assert result.solution_cost == 10
    assert result.solution_length == 10
    game = replay_split_solution(board, result.moves)
    assert game.move_count == 10


def test_solution_length_counts_rolls_instead_of_control_switches() -> None:
    result = SolverResult(moves=[Direction.RIGHT, "SWITCH", Direction.DOWN], is_solved=True)
    assert "Moves: 2 |" in result.summary()
    assert getattr(result, "solution_length", None) == 2


@pytest.mark.parametrize(
    ("layout", "expected"),
    [(["11112", "11111", "31111"], 1), (["11312", "11111", "11111"], 3)],
)
def test_split_fragile_cost_depends_on_moving_cube_only(layout: List[str], expected: float) -> None:
    board = parse_level_data({"layout": layout, "spawn": {"x": 0, "y": 0}})
    split = SplitBlockState(SingleBlock(1, 0), SingleBlock(0, 2), 0)
    child = next(item for item in BaseSolver.get_successors(split, board) if item.direction == Direction.RIGHT)
    assert fragile_cost(split, board, child) == expected


def test_control_switch_is_free_even_when_a_cube_rests_on_fragile() -> None:
    board = parse_level_data({"layout": ["11112", "11111", "31111"], "spawn": {"x": 0, "y": 0}})
    split = SplitBlockState(SingleBlock(1, 0), SingleBlock(0, 2), 0)
    child = next(item for item in BaseSolver.get_successors(split, board) if item.direction == "SWITCH")
    assert fragile_cost(split, board, child) == 0


def test_teleport_tile_without_targets_is_invalid_input() -> None:
    board = parse_level_data({"layout": ["1112"], "tiles": {"1,0": 8}, "spawn": {"x": 0, "y": 0}})
    with pytest.raises(ValueError, match="teleport.*targets"):
        UCSSolver().solve(board)


@pytest.mark.parametrize("stage", [8, 9, 10, 15, 16, 20, 23, 24, 26, 28])
def test_packaged_split_level_solution_replays_with_safe_support(stage: int) -> None:
    board = load_level_from_file(LEVELS / f"stage_{stage:02d}.json")
    original = deepcopy(board)
    result = UCSSolver().solve(board)
    assert result.is_solved, f"Stage {stage}: {result.message}"
    game = replay_split_solution(board, result.moves)
    assert game.move_count == result.solution_length
    assert board.current_tiles == original.current_tiles
    assert board.get_bridge_state_key() == original.get_bridge_state_key()


def test_custom_cost_keeps_labels_when_reversed_teleports_change_cube_costs() -> None:
    board = parse_level_data({
        "layout": ["11111"] * 4 + ["11112"],
        "spawn": {"x": 0, "y": 0},
        "teleports": [
            {"x": 3, "y": 0, "target_1": [1, 2], "target_2": [4, 2], "selected": 0},
            {"x": 0, "y": 3, "target_1": [4, 2], "target_2": [1, 2], "selected": 1},
        ],
    })

    def cube_cost(block: BaseBlockState, source_board: Board, successor: Successor) -> float:
        if successor.direction == "SWITCH":
            return 10000
        if isinstance(block, SplitBlockState):
            return 100 if block.active_index == 0 else 1
        if successor.outcome == "TELEPORT":
            return 1 if successor.direction == Direction.RIGHT else 2
        return 100

    # A hand-checked legal route costs 100 + 2 + 1 + 1 + 1 + 1 + 100 = 206.
    witness = [Direction.DOWN, Direction.DOWN, Direction.RIGHT, Direction.DOWN,
               Direction.RIGHT, Direction.RIGHT, Direction.DOWN]
    replay_split_solution(board, witness)
    result = UCSSolver(cost_fn=cube_cost).solve(board)
    assert result.is_solved
    assert result.solution_cost <= 206
    replay_split_solution(board, result.moves)
