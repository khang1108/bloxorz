"""Unit and regression tests for DFSSolver."""

import unittest
from pathlib import Path
from bloxorz.core.constants import BlockOrientation, TileType
from bloxorz.core.block import BlockState
from bloxorz.core.board import Board
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.solvers.dfs import DFSSolver


class TestDFSSolver(unittest.TestCase):
    """Verifies that DFS solver finds correct and valid solutions."""

    def setUp(self):
        self.levels_dir = Path(__file__).parent.parent / "bloxorz" / "levels"

    def test_dfs_solves_stage_01(self):
        stage_file = self.levels_dir / "stage_01.json"
        board = load_level_from_file(stage_file)
        solver = DFSSolver()

        result = solver.solve(board)
        self.assertTrue(result.is_solved, "DFS must solve Stage 01")
        self.assertGreater(len(result.moves), 0)
        self.assertGreater(result.expanded_nodes, 0)
        self.assertGreater(result.visited_count, 0)
        self.assertGreaterEqual(result.peak_memory_kb, 0.0)
        self.assertGreaterEqual(result.execution_time_ms, 0.0)

        # Replay solution in Game
        game = Game(board)
        final_outcome = None
        for move in result.moves:
            outcome, _, _ = game.roll(move)
            final_outcome = outcome

        self.assertEqual(final_outcome, "VICTORY")

    def test_dfs_solves_bridge_stage_02(self):
        stage_file = self.levels_dir / "stage_02.json"
        board = load_level_from_file(stage_file)
        solver = DFSSolver(max_depth=3000)

        result = solver.solve(board)
        self.assertTrue(result.is_solved, "DFS must solve Stage 02 with bridges and switches")

        game = Game(board)
        final_outcome = None
        for move in result.moves:
            outcome, _, _ = game.roll(move)
            final_outcome = outcome

        self.assertEqual(final_outcome, "VICTORY")

    def test_dfs_solves_split_stage_08(self):
        stage_file = self.levels_dir / "stage_08.json"
        board = load_level_from_file(stage_file)
        solver = DFSSolver(max_depth=3000)

        result = solver.solve(board)
        self.assertTrue(result.is_solved, "DFS must solve Stage 08 with split switch")

        # Replay solution in Game
        game = Game(board)
        final_outcome = None
        for move in result.moves:
            outcome, _, _ = game.roll(move)
            final_outcome = outcome

        self.assertEqual(final_outcome, "VICTORY")

    def test_dfs_cycle_prevention(self):
        # A tiny cyclic board with no goal
        tiles = {
            (0, 0): TileType.NORMAL,
            (1, 0): TileType.NORMAL,
            (0, 1): TileType.NORMAL,
            (1, 1): TileType.NORMAL,
        }
        board = Board(
            tiles=tiles,
            goal_pos=(99, 99),  # Unreachable
            spawn_state=BlockState(0, 0, BlockOrientation.STANDING),
        )

        solver = DFSSolver(max_depth=50)
        result = solver.solve(board)
        self.assertFalse(result.is_solved)
        self.assertGreater(result.expanded_nodes, 0)


if __name__ == "__main__":
    unittest.main()
