import unittest
from pathlib import Path
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.core.constants import BlockOrientation


class TestLevelLoading(unittest.TestCase):
    """Verifies that all packaged stages parse cleanly."""

    def setUp(self):
        self.levels_dir = Path(__file__).parent.parent / "bloxorz" / "levels"

    def test_all_packaged_stages(self):
        for stage_file in sorted(self.levels_dir.glob("stage_*.json")):
            board = load_level_from_file(stage_file)
            self.assertIsNotNone(board.goal_pos, f"Goal missing in {stage_file.name}")
            self.assertGreater(len(board.base_tiles), 0, f"No tiles in {stage_file.name}")
            self.assertIn(board.goal_pos, board.base_tiles, f"Goal {board.goal_pos} not in tiles in {stage_file.name}")
            self.assertEqual(board.spawn_state.orientation, BlockOrientation.STANDING)
