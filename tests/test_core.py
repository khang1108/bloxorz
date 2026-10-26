"""Unit tests for Bloxorz core mechanics."""

import unittest
from pathlib import Path
from bloxorz.core.constants import Direction, BlockOrientation, TileType, GameStatus
from bloxorz.core.block import BlockState
from bloxorz.core.block.split import SplitBlockState
from bloxorz.core.game import Game
from bloxorz.core.level_loader import parse_level_data, load_level_from_file


class TestBlockRollMechanics(unittest.TestCase):
    """Tests the geometric rolling transitions of the 1x1x2 block."""

    def test_standing_roll_right_and_left(self):
        b = BlockState(0, 0, BlockOrientation.STANDING)
        assert b.occupied_cells == {(0, 0)}

        # Roll right
        b_right = b.roll(Direction.RIGHT)
        assert b_right.orientation == BlockOrientation.LYING_X
        assert b_right.x == 1 and b_right.y == 0
        assert b_right.occupied_cells == {(1, 0), (2, 0)}

        # Roll left should return to original standing state
        b_back = b_right.roll(Direction.LEFT)
        assert b_back == b

    def test_standing_roll_down_and_up(self):
        b = BlockState(0, 0, BlockOrientation.STANDING)

        # Roll down
        b_down = b.roll(Direction.DOWN)
        assert b_down.orientation == BlockOrientation.LYING_Y
        assert b_down.x == 0 and b_down.y == 1
        assert b_down.occupied_cells == {(0, 1), (0, 2)}

        # Roll up returns to standing
        b_back = b_down.roll(Direction.UP)
        assert b_back == b

    def test_lying_x_lateral_rolls(self):
        b = BlockState(1, 1, BlockOrientation.LYING_X)
        assert b.occupied_cells == {(1, 1), (2, 1)}

        # Rolling UP while lying X keeps it lying X
        b_up = b.roll(Direction.UP)
        assert b_up.orientation == BlockOrientation.LYING_X
        assert b_up.x == 1 and b_up.y == 0
        assert b_up.occupied_cells == {(1, 0), (2, 0)}

        # Rolling DOWN returns to (1, 1)
        b_down = b_up.roll(Direction.DOWN)
        assert b_down == b

    def test_lying_y_lateral_rolls(self):
        b = BlockState(1, 1, BlockOrientation.LYING_Y)
        assert b.occupied_cells == {(1, 1), (1, 2)}

        # Rolling RIGHT while lying Y keeps it lying Y
        b_right = b.roll(Direction.RIGHT)
        assert b_right.orientation == BlockOrientation.LYING_Y
        assert b_right.x == 2 and b_right.y == 1

        b_back = b_right.roll(Direction.LEFT)
        assert b_back == b

    def test_3d_coordinates(self):
        standing = BlockState(2, 3, BlockOrientation.STANDING)
        assert standing.get_center_3d() == (2.0, 3.0, 1.0)
        assert standing.get_dimensions_3d() == (1.0, 1.0, 2.0)

        lying_x = BlockState(2, 3, BlockOrientation.LYING_X)
        assert lying_x.get_center_3d() == (2.5, 3.0, 0.5)
        assert lying_x.get_dimensions_3d() == (2.0, 1.0, 1.0)


class TestBoardMechanics(unittest.TestCase):
    """Tests board validation, fragile tiles, goals, and switches."""

    def test_victory_condition(self):
        board_data = {
            "layout": [
                "111",
                "121",
                "111"
            ],
            "spawn": {"x": 0, "y": 0, "orientation": "STANDING"}
        }
        board = parse_level_data(board_data)
        game = Game(board)

        # Move to goal at (1, 1)
        # (0, 0) STANDING -> DOWN -> (0, 1) LYING_Y (cells (0,1), (0,2))
        res, state, _ = game.roll(Direction.DOWN)
        assert res == "SAFE"

        # (0, 1) LYING_Y -> RIGHT -> (1, 1) LYING_Y (cells (1,1), (1,2))
        # Note: cell (1,1) is GOAL, cell (1,2) is NORMAL tile -> lying across goal is SAFE!
        res, state, _ = game.roll(Direction.RIGHT)
        assert res == "SAFE"

    def test_stage_01_lying_on_goal_is_safe(self):
        """Verifies the exact scenario from Stage 1: lying horizontally across goal is SAFE."""
        stage_file = Path(__file__).parent.parent / "bloxorz" / "levels" / "stage_01.json"
        board = load_level_from_file(stage_file)

        # In Stage 1, goal is at board.goal_pos (7, 4)
        gx, gy = board.goal_pos
        # Block lying on (gx - 1, gy) and (gx, gy)
        lying_block = BlockState(gx - 1, gy, BlockOrientation.LYING_X)
        outcome, cause = board.evaluate_block_state(lying_block)
        assert outcome == "SAFE"
        assert cause is None

        # Standing on goal (gx, gy)
        standing_block = BlockState(gx, gy, BlockOrientation.STANDING)
        outcome, cause = board.evaluate_block_state(standing_block)
        assert outcome == "VICTORY"

    def test_standing_on_goal_wins(self):
        # Create a layout where we stand directly onto goal
        # (0, 0) -> R -> (1, 0) LYING_X -> R -> (3, 0) STANDING on GOAL
        board_data = {
            "layout": [
                "1112"
            ],
            "spawn": {"x": 0, "y": 0, "orientation": "STANDING"}
        }
        board = parse_level_data(board_data)
        game = Game(board)

        res, state, _ = game.roll(Direction.RIGHT)
        assert res == "SAFE"
        assert state.orientation == BlockOrientation.LYING_X

        res, state, _ = game.roll(Direction.RIGHT)
        assert res == "VICTORY"
        assert game.status == GameStatus.VICTORY

    def test_fragile_tiles(self):
        # (0, 0) NORMAL -> R -> (1, 0) LYING_X on FRAGILE (safe) -> R -> (3, 0) STANDING on FRAGILE (breaks)
        board_data = {
            "layout": [
                "1333",
                "1111"
            ],
            "spawn": {"x": 0, "y": 0, "orientation": "STANDING"}
        }
        board = parse_level_data(board_data)
        game = Game(board)

        # Roll right: covers (1, 0) and (2, 0) which are fragile (3)
        res, state, _ = game.roll(Direction.RIGHT)
        assert res == "SAFE"
        assert state.orientation == BlockOrientation.LYING_X

        # Roll right again: stands upright at (3, 0) which is fragile (3) -> breaks!
        res, state, _ = game.roll(Direction.RIGHT)
        assert res == "FELL_FRAGILE"

    def test_switches_and_bridges(self):
        board_data = {
            "layout": [
                "1S1B12",
                "111.11"
            ],
            "spawn": {"x": 0, "y": 0, "orientation": "STANDING"},
            "bridges": [
                {"id": "b1", "tiles": [[3, 0]], "initially_open": False}
            ],
            "switches": [
                {"x": 1, "y": 0, "type": "SOFT", "targets": ["b1"], "action": "TOGGLE"}
            ]
        }
        board = parse_level_data(board_data)
        game = Game(board)

        assert board.get_tile(3, 0) == TileType.BRIDGE_CLOSED

        # Roll right to (1, 0) LYING_X: touches switch at (1, 0)
        res, state, toggled = game.roll(Direction.RIGHT)
        assert res == "SAFE"
        assert "b1" in toggled
        # Bridge (3, 0) should now be OPEN!
        assert board.get_tile(3, 0) == TileType.BRIDGE_OPEN

        # Test Undo restores bridge state
        assert game.undo() is True
        assert board.get_tile(3, 0) == TileType.BRIDGE_CLOSED

    def test_teleport_split_switch_merge_and_undo(self):
        board_data = {
            "layout": [
                "11111111",
                "11181111",
                "11111112",
            ],
            "spawn": {"x": 0, "y": 1, "orientation": "STANDING"},
            "teleports": [
                {"x": 3, "y": 1, "target_1": [3, 0], "target_2": [5, 0], "selected": 0}
            ]
        }
        board = parse_level_data(board_data)
        game = Game(board)

        # Move 1: Roll right to (1, 1), (2, 1) lying_x -> SAFE
        res1, state1, _ = game.roll(Direction.RIGHT)
        assert res1 == "SAFE"
        assert state1.orientation == BlockOrientation.LYING_X
        assert game.move_count == 1

        # Move 2: Roll right onto teleport tile at (3, 1) standing -> triggers TELEPORT
        res2, state2, targets = game.roll(Direction.RIGHT)
        assert res2 == "TELEPORT"
        assert getattr(state2, "is_split", False) is True
        assert state2.active_index == 0
        assert state2.active_block.x == 3 and state2.active_block.y == 0
        assert state2.passive_block.x == 5 and state2.passive_block.y == 0
        assert game.move_count == 2

        # Switch active block
        assert game.switch_block() is True
        assert game.block.active_index == 1
        assert game.block.active_block.x == 5 and game.block.active_block.y == 0
        assert game.move_count == 2  # switch does not increment move count

        # Undo switch
        assert game.undo() is True
        assert game.block.active_index == 0
        assert game.move_count == 2

        # Move active block (3, 0) RIGHT to (4, 0)
        res3, state3, _ = game.roll(Direction.RIGHT)
        # Block 1 is now at (4, 0), Block 2 is at (5, 0).
        # Manhattan distance = 1 -> automatically MERGES!
        assert res3 == "MERGED"
        assert getattr(state3, "is_split", False) is False
        assert state3.x == 4 and state3.y == 0
        assert state3.orientation == BlockOrientation.LYING_X
        assert game.move_count == 3

    def test_heavy_switch_vs_soft_switch_mechanics(self):
        """Verifies exact Bloxorz rules for Soft (Circle) and Heavy (X) switches."""
        board_data = {
            "layout": [
                "111B1",
                "11111",
                "11111",
                "11111",
            ],
            "spawn": {"x": 1, "y": 3, "orientation": "STANDING"},
            "bridges": [
                {"id": "b1", "tiles": [[3, 0]], "initially_open": False}
            ],
            "switches": [
                {"x": 1, "y": 0, "type": "HEAVY", "targets": ["b1"], "action": "TOGGLE"}
            ]
        }
        board = parse_level_data(board_data)
        game = Game(board)

        # 1. Roll UP -> LYING_Y covering (1, 1) and (1, 0)
        res1, state1, toggled1 = game.roll(Direction.UP)
        assert res1 == "SAFE"
        assert state1.orientation == BlockOrientation.LYING_Y
        # Heavy switch must NOT trigger when block lies flat across it!
        assert len(toggled1) == 0
        assert board.get_tile(3, 0) == TileType.BRIDGE_CLOSED

        # 2. Roll UP again -> STANDING upright directly onto (1, 0)
        res2, state2, toggled2 = game.roll(Direction.UP)
        assert res2 == "SAFE"
        assert state2.orientation == BlockOrientation.STANDING
        # Heavy switch MUST trigger when block stands upright!
        assert "b1" in toggled2
        assert board.get_tile(3, 0) == TileType.BRIDGE_OPEN

        # 3. Test split 1x1x1 cube stepping on HEAVY switch (too light -> must NOT trigger)
        board_h = parse_level_data(board_data)
        game_h = Game(board_h)
        game_h.block = SplitBlockState.from_targets((1, 1), (4, 3), selected=0)
        res3, _, toggled3 = game_h.roll(Direction.UP)
        assert res3 == "SAFE"
        assert len(toggled3) == 0
        assert board_h.get_tile(3, 0) == TileType.BRIDGE_CLOSED

        # 4. Test split 1x1x1 cube stepping on SOFT switch (must trigger)
        board_data["switches"][0]["type"] = "SOFT"
        board_s = parse_level_data(board_data)
        game_s = Game(board_s)
        game_s.block = SplitBlockState.from_targets((1, 1), (4, 3), selected=0)
        res4, _, toggled4 = game_s.roll(Direction.UP)
        assert res4 == "SAFE"
        assert "b1" in toggled4
        assert board_s.get_tile(3, 0) == TileType.BRIDGE_OPEN
