"""Unit tests for level loading, validation, and ground-truth solution playback."""

import json
import unittest
from pathlib import Path
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.core.constants import BlockOrientation, Direction
from bloxorz.core.game import Game


class TestLevelLoading(unittest.TestCase):
    """Verifies that all 33 packaged stages parse and function cleanly."""

    def setUp(self):
        self.root_dir = Path(__file__).parent.parent
        self.levels_dir = self.root_dir / "bloxorz" / "levels"
        self.solutions_file = self.root_dir / "data" / "solutions.json"

    def test_all_33_packaged_stages(self):
        """Verifies that all 33 stages load with valid spawn, tiles, and goal."""
        stage_files = sorted(self.levels_dir.glob("stage_*.json"))
        self.assertEqual(len(stage_files), 33, "Expected exactly 33 stages")

        for stage_file in stage_files:
            board = load_level_from_file(stage_file)
            self.assertIsNotNone(board.goal_pos, f"Goal missing in {stage_file.name}")
            self.assertGreater(len(board.base_tiles), 0, f"No tiles in {stage_file.name}")
            self.assertIn(board.goal_pos, board.base_tiles, f"Goal not in tiles in {stage_file.name}")
            self.assertEqual(board.spawn_state.orientation, BlockOrientation.STANDING)

    def test_non_teleport_stage_optimal_solutions(self):
        """Validates that non-teleport stages reach VICTORY with optimal move sequences."""
        if not self.solutions_file.is_file():
            self.skipTest("solutions.json not available")

        with open(self.solutions_file, "r", encoding="utf-8") as f:
            solutions = json.load(f)

        dir_map = {
            "U": Direction.UP,
            "D": Direction.DOWN,
            "L": Direction.LEFT,
            "R": Direction.RIGHT,
        }

        # Validate non-teleport stages against ground truth solutions
        for idx in range(1, 34):
            stage_file = self.levels_dir / f"stage_{idx:02d}.json"
            with open(stage_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("teleports"):
                continue  # Split block mechanic reserved for future expansion

            board = load_level_from_file(stage_file)
            game = Game(board)
            sol_entry = solutions.get(f"{idx:02d}")
            self.assertIsNotNone(sol_entry, f"Missing solution entry for stage {idx}")

            final_outcome = None
            for move_char in sol_entry["moves"]:
                if move_char in dir_map:
                    outcome, _, _ = game.roll(dir_map[move_char])
                    final_outcome = outcome
                    self.assertNotIn(outcome, ("FELL_VOID", "FELL_FRAGILE"), f"Stage {idx} failed on move {move_char}")

            self.assertEqual(final_outcome, "VICTORY", f"Stage {idx} did not achieve VICTORY with optimal moves")
