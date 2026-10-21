"""Unit tests for Bloxorz core mechanics."""

import unittest
from bloxorz.core.constants import Direction, BlockOrientation, TileType, GameStatus
from bloxorz.core.block import BlockState
from bloxorz.core.game import Game
from bloxorz.core.level_loader import parse_level_data


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
        # Note: cell (1,1) is GOAL, lying on goal -> FELL_HALF_GOAL!
        res, state, _ = game.roll(Direction.RIGHT)
        assert res == "FELL_HALF_GOAL"

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
