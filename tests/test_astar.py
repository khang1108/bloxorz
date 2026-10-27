"""Unit and regression tests for A* Search algorithm (AstarSolver)."""

import unittest
from pathlib import Path

from bloxorz.core.constants import BlockOrientation, TileType, Direction
from bloxorz.core.block import BlockState
from bloxorz.core.block.split import SplitBlockState
from bloxorz.core.board import Board
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.solvers.astar import AstarSolver
from bloxorz.solvers.bfs import BFSSolver


class TestAstarSolver(unittest.TestCase):
    """Verifies that A* search finds optimal solutions and behaves correctly."""

    def setUp(self):
        self.levels_dir = Path(__file__).parent.parent / "bloxorz" / "levels"

    def test_astar_solves_stage_01_optimally(self):
        stage_file = self.levels_dir / "stage_01.json"
        board = load_level_from_file(stage_file)
        solver = AstarSolver()

        result = solver.solve(board)
        self.assertTrue(result.is_solved, "A* must solve Stage 01")
        # Optimal solution for Stage 01 is 7 moves
        self.assertEqual(len(result.moves), 7, "A* must find optimal 7-move solution for Stage 01")
        self.assertGreater(result.expanded_nodes, 0)
        self.assertGreater(result.visited_count, 0)
        self.assertGreaterEqual(result.peak_memory_kb, 0.0)
        self.assertGreaterEqual(result.execution_time_ms, 0.0)

        # Replay solution in Game to verify victory
        game = Game(board)
        final_outcome = None
        for move in result.moves:
            outcome, _, _ = game.roll(move)
            final_outcome = outcome

        self.assertEqual(final_outcome, "VICTORY")

    def test_astar_solves_stage_02_bridges(self):
        stage_file = self.levels_dir / "stage_02.json"
        board = load_level_from_file(stage_file)
        solver = AstarSolver()

        result = solver.solve(board)
        self.assertTrue(result.is_solved, "A* must solve Stage 02")
        self.assertGreater(len(result.moves), 0)

        # Replay solution in Game
        game = Game(board)
        final_outcome = None
        for move in result.moves:
            outcome, _, _ = game.roll(move)
            final_outcome = outcome

        self.assertEqual(final_outcome, "VICTORY")

    def test_astar_solves_split_stage_08(self):
        stage_file = self.levels_dir / "stage_08.json"
        board = load_level_from_file(stage_file)
        solver = AstarSolver()

        result = solver.solve(board)
        self.assertTrue(result.is_solved, "A* must solve Stage 08")

        # Replay solution in Game
        game = Game(board)
        final_outcome = None
        for move in result.moves:
            if move == "SWITCH" or move == Direction.SWITCH_CUBE:
                game.switch_block()
            else:
                outcome, _, _ = game.roll(move)
                final_outcome = outcome

        self.assertEqual(final_outcome, "VICTORY")

    def test_astar_heuristic_values(self):
        tiles = {
            (0, 0): TileType.NORMAL,
            (5, 5): TileType.GOAL,
        }
        board = Board(
            tiles=tiles,
            goal_pos=(5, 5),
            spawn_state=BlockState(0, 0, BlockOrientation.STANDING),
        )

        # 1. Standing on goal hole: h == 0.0
        standing_on_goal = BlockState(5, 5, BlockOrientation.STANDING)
        self.assertEqual(AstarSolver.heuristic(standing_on_goal, board), 0.0)

        # 2. Lying on goal hole: min_d == 0 but not standing -> h == 2.0
        lying_on_goal = BlockState(5, 5, BlockOrientation.LYING_X)
        self.assertEqual(AstarSolver.heuristic(lying_on_goal, board), 2.0)

        # 3. Distance 2 away: ceil(2/2) = 1.0
        standing_at_3_5 = BlockState(3, 5, BlockOrientation.STANDING)
        self.assertEqual(AstarSolver.heuristic(standing_at_3_5, board), 1.0)

        # 4. Distance 5 away: ceil(5/2) = 3.0
        standing_at_0_5 = BlockState(0, 5, BlockOrientation.STANDING)
        self.assertEqual(AstarSolver.heuristic(standing_at_0_5, board), 3.0)

        # 5. Split block:
        # cube1 at (0, 0), cube2 at (2, 0). dist_between = 2, merge_cost = max(0, 2-1) = 1
        # d1_to_goal = |0-5| + |0-5| = 10, d2_to_goal = |2-5| + |0-5| = 8
        # min_d = 8, goal_cost = ceil(8/2) = 4
        # total h = 1 + 4 = 5.0
        split_block = SplitBlockState(cube1=(0, 0), cube2=(2, 0), active_cube=0)
        self.assertEqual(AstarSolver.heuristic(split_block, board), 5.0)

    def test_astar_expands_fewer_or_equal_nodes_than_bfs(self):
        stage_file = self.levels_dir / "stage_01.json"
        board = load_level_from_file(stage_file)

        astar_result = AstarSolver().solve(board)
        bfs_result = BFSSolver().solve(board)

        self.assertTrue(astar_result.is_solved)
        self.assertTrue(bfs_result.is_solved)
        # Both find the optimal 7-step solution
        self.assertEqual(len(astar_result.moves), len(bfs_result.moves))
        # A* with heuristic guidance should expand fewer or equal nodes than uninformed BFS
        self.assertLessEqual(astar_result.expanded_nodes, bfs_result.expanded_nodes)

    def test_astar_spawn_already_on_goal(self):
        tiles = {
            (2, 2): TileType.GOAL,
        }
        board = Board(
            tiles=tiles,
            goal_pos=(2, 2),
            spawn_state=BlockState(2, 2, BlockOrientation.STANDING),
        )

        result = AstarSolver().solve(board)
        self.assertTrue(result.is_solved)
        self.assertEqual(len(result.moves), 0)
        self.assertEqual(result.expanded_nodes, 0)

    def test_astar_unsolvable_board(self):
        tiles = {
            (0, 0): TileType.NORMAL,
            (0, 1): TileType.NORMAL,
        }
        board = Board(
            tiles=tiles,
            goal_pos=(99, 99),
            spawn_state=BlockState(0, 0, BlockOrientation.STANDING),
        )

        result = AstarSolver().solve(board)
        self.assertFalse(result.is_solved)
        self.assertEqual(len(result.moves), 0)
        self.assertGreater(result.expanded_nodes, 0)

    def test_astar_custom_heuristic(self):
        stage_file = self.levels_dir / "stage_01.json"
        board = load_level_from_file(stage_file)

        # Zero heuristic degenerates to Dijkstra / UCS
        zero_heuristic = lambda block, b: 0.0
        solver = AstarSolver(heuristic_fn=zero_heuristic)
        result = solver.solve(board)

        self.assertTrue(result.is_solved)
        self.assertEqual(len(result.moves), 7)


if __name__ == "__main__":
    unittest.main()
