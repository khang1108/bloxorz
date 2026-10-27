"""Unit and regression tests for Bloxorz split switch and unit cube mechanics."""

import unittest
from pathlib import Path
from bloxorz.core.constants import Direction, BlockOrientation, TileType
from bloxorz.core.block import BlockState
from bloxorz.core.split import SplitBlockState, Teleport
from bloxorz.core.board import Board, Switch
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file


class TestSplitMechanics(unittest.TestCase):
    """Verifies the mathematical and physical correctness of block splitting and rejoining."""

    def test_split_block_state_properties(self):
        s = SplitBlockState(cube1=(2, 3), cube2=(6, 7), active_cube=0)
        self.assertTrue(s.is_split)
        self.assertEqual(s.active_coord, (2, 3))
        self.assertEqual(s.inactive_coord, (6, 7))
        self.assertEqual(s.occupied_cells, {(2, 3), (6, 7)})

        # Switch active cube
        switched = s.switch_active()
        self.assertEqual(switched.active_cube, 1)
        self.assertEqual(switched.active_coord, (6, 7))
        self.assertEqual(switched.inactive_coord, (2, 3))

    def test_split_movement_without_merge(self):
        s = SplitBlockState(cube1=(2, 3), cube2=(6, 7), active_cube=0)
        s_down = s.roll(Direction.DOWN)
        self.assertTrue(s_down.is_split)
        self.assertEqual(s_down.active_coord, (2, 4))
        self.assertEqual(s_down.inactive_coord, (6, 7))

    def test_split_merge_horizontal(self):
        # Cube 1 at (2, 3), Cube 2 at (4, 3)
        s = SplitBlockState(cube1=(2, 3), cube2=(4, 3), active_cube=0)
        merged = s.roll(Direction.RIGHT)

        self.assertFalse(merged.is_split)
        self.assertIsInstance(merged, BlockState)
        self.assertEqual(merged.orientation, BlockOrientation.LYING_X)
        self.assertEqual(merged.x, 3)
        self.assertEqual(merged.y, 3)
        self.assertEqual(merged.occupied_cells, {(3, 3), (4, 3)})

    def test_split_merge_vertical(self):
        # Cube 1 at (5, 2), Cube 2 at (5, 4), controlling Cube 2
        s = SplitBlockState(cube1=(5, 2), cube2=(5, 4), active_cube=1)
        merged = s.roll(Direction.UP)

        self.assertFalse(merged.is_split)
        self.assertIsInstance(merged, BlockState)
        self.assertEqual(merged.orientation, BlockOrientation.LYING_Y)
        self.assertEqual(merged.x, 5)
        self.assertEqual(merged.y, 2)
        self.assertEqual(merged.occupied_cells, {(5, 2), (5, 3)})

    def test_split_on_fragile_is_safe(self):
        # Q&A rule: unit cube standing on fragile tile does NOT break it
        tiles = {
            (0, 0): TileType.FRAGILE,
            (5, 5): TileType.NORMAL,
        }
        board = Board(tiles=tiles, goal_pos=(9, 9), spawn_state=BlockState(5, 5, BlockOrientation.STANDING))
        s = SplitBlockState(cube1=(0, 0), cube2=(5, 5), active_cube=0)

        outcome, cause = board.evaluate_block_state(s)
        self.assertEqual(outcome, "SAFE")
        self.assertIsNone(cause)

    def test_split_on_goal_does_not_win(self):
        # Rule: a single unit cube cannot win on goal hole
        tiles = {
            (2, 2): TileType.GOAL,
            (5, 5): TileType.NORMAL,
        }
        board = Board(tiles=tiles, goal_pos=(2, 2), spawn_state=BlockState(5, 5, BlockOrientation.STANDING))
        s = SplitBlockState(cube1=(2, 2), cube2=(5, 5), active_cube=0)

        outcome, cause = board.evaluate_block_state(s)
        self.assertNotEqual(outcome, "VICTORY")
        self.assertEqual(outcome, "SAFE")

    def test_split_switches_interaction(self):
        # Soft switch triggers on unit cube; Heavy switch does NOT
        tiles = {
            (1, 1): TileType.SWITCH_SOFT,
            (2, 2): TileType.SWITCH_HEAVY,
            (5, 5): TileType.NORMAL,
        }
        soft_sw = Switch(x=1, y=1, switch_type=TileType.SWITCH_SOFT, target_bridge_ids=[])
        heavy_sw = Switch(x=2, y=2, switch_type=TileType.SWITCH_HEAVY, target_bridge_ids=[])
        board = Board(
            tiles=tiles,
            goal_pos=(9, 9),
            spawn_state=BlockState(5, 5, BlockOrientation.STANDING),
            switches=[soft_sw, heavy_sw],
        )

        s1 = SplitBlockState(cube1=(1, 1), cube2=(5, 5), active_cube=0)
        # Soft switch triggers
        toggled_soft = board.trigger_switches(s1)
        self.assertIsInstance(toggled_soft, list)

        # Heavy switch on unit cube should NOT trigger
        s2 = SplitBlockState(cube1=(2, 2), cube2=(5, 5), active_cube=0)
        toggled_heavy = board.trigger_switches(s2)
        self.assertEqual(toggled_heavy, [])

    def test_stage_08_ground_truth_solution(self):
        """Verifies full execution of Stage 08 ground-truth solution: RRDDDD_UURR."""
        stage_file = Path(__file__).parent.parent / "bloxorz" / "levels" / "stage_08.json"
        board = load_level_from_file(stage_file)
        self.assertTrue(len(board.teleports) > 0, "Stage 08 must have teleports")

        game = Game(board)

        dir_map = {
            "R": Direction.RIGHT,
            "L": Direction.LEFT,
            "U": Direction.UP,
            "D": Direction.DOWN,
            "_": Direction.SWITCH_CUBE,
        }

        moves_str = "RRDDDD_UURR"
        final_outcome = None

        for idx, char in enumerate(moves_str):
            d = dir_map[char]
            outcome, state, _ = game.roll(d)
            if idx == 1:
                # After second R, block landed on teleport and should be split
                self.assertTrue(state.is_split, "Block should be split after move 2")
            if idx == 7:
                # After U (char at index 7), cubes should be adjacent and merged
                self.assertFalse(state.is_split, "Block should be merged after move 8 (U)")
                self.assertEqual(state.orientation, BlockOrientation.LYING_Y)

            final_outcome = outcome

        self.assertEqual(final_outcome, "VICTORY")
        self.assertEqual(game.move_count, 10, "Move count should be 10 (excluding _ switch)")


if __name__ == "__main__":
    unittest.main()
