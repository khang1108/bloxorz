"""UCS correctness tests independent of graphics and other solver implementations."""

from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from bloxorz.core.block import BlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import BlockOrientation, Direction, GameStatus
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file, parse_level_data
from bloxorz.solvers import SolverResult, Successor, UCSSolver, fragile_cost


LEVELS_DIR = Path(__file__).resolve().parents[1] / "bloxorz" / "levels"


def replay(board: Board, moves: List[Direction]) -> float:
    """Validate a solution through Game rather than the solver's successor helper."""
    game = Game(deepcopy(board))
    cost = 0.0
    for direction in moves:
        before_block = game.block
        before_board = deepcopy(game.board)
        outcome, block, _ = game.roll(direction)
        assert outcome in ("SAFE", "VICTORY")
        cost += fragile_cost(before_block, before_board, Successor(direction, block, game.board, outcome))
    assert game.status == GameStatus.VICTORY
    return cost


class GraphSolver(UCSSolver):
    """Exercise priority-queue behavior on tiny graphs with hand-calculated costs.

    Only successor generation and costs are replaced; state keys and goal tests
    still use real Board/BlockState values. Physical rolling is tested separately.
    """

    def __init__(self, edges: Dict[str, List[Tuple[str, float]]]) -> None:
        names = list(dict.fromkeys(["S", "G"] + list(edges) + [dst for row in edges.values() for dst, _ in row]))
        self.blocks = {name: BlockState(i, 0, BlockOrientation.STANDING) for i, name in enumerate(names)}
        self.names = {block: name for name, block in self.blocks.items()}
        self.edges = edges
        self.weights = {(src, dst): cost for src, row in edges.items() for dst, cost in row}
        self.expansion_order: List[str] = []
        goal_x = self.blocks["G"].x
        layout = "1" * goal_x + "2" + "1" * (len(names) - goal_x - 1)
        self.board = parse_level_data({"layout": [layout], "spawn": {"x": 0, "y": 0}})
        super().__init__(cost_fn=self.edge_cost)

    def edge_cost(self, block: BlockState, board: Board, successor: Successor) -> float:
        return self.weights[(self.names[block], self.names[successor.block])]

    def get_successors(self, block: BlockState, board: Board) -> List[Successor]:
        name = self.names[block]
        self.expansion_order.append(name)
        return [
            Successor(direction, self.blocks[dst], board, "VICTORY" if dst == "G" else "SAFE")
            for direction, (dst, _) in zip(Direction, self.edges.get(name, []))
        ]


def test_goal_is_checked_on_pop_and_cheaper_route_replaces_parent() -> None:
    solver = GraphSolver({"S": [("G", 10), ("A", 1)], "A": [("G", 2)]})
    result = solver.solve(solver.board)
    assert result.is_solved
    assert result.solution_cost == 3
    assert result.moves == [Direction.DOWN, Direction.UP]
    assert result.visited_count == 3
    assert result.expanded_nodes == 2
    assert result.max_depth == 1


def test_stale_entries_are_not_expanded() -> None:
    solver = GraphSolver({
        "S": [("A", 5), ("B", 1)], "B": [("A", 1)],
        "A": [("C", 1)], "C": [("G", 10)],
    })
    result = solver.solve(solver.board)
    assert result.solution_cost == 13
    assert len(result.moves) == 4
    assert solver.expansion_order == ["S", "B", "A", "C"]
    assert result.expanded_nodes == 4
    assert result.visited_count == 5
    assert result.max_depth == 3


def test_equal_costs_are_stable_without_comparing_nodes() -> None:
    solver = GraphSolver({"S": [("A", 1), ("B", 1)], "A": [("G", 1)], "B": [("G", 1)]})
    result = solver.solve(solver.board)
    assert result.solution_cost == 2
    assert result.moves == [Direction.UP, Direction.UP]
    assert solver.expansion_order == ["S", "A", "B"]


def test_zero_cost_cycle_terminates() -> None:
    solver = GraphSolver({"S": [("A", 0)], "A": [("S", 0), ("G", 1)]})
    result = solver.solve(solver.board)
    assert result.is_solved
    assert result.solution_cost == 1
    assert result.expanded_nodes == 2


@pytest.mark.parametrize("cost", [-1, float("nan"), float("inf"), -float("inf"), None, "invalid"])
def test_invalid_custom_cost_is_rejected(cost: float) -> None:
    board = parse_level_data({"layout": ["1112"], "spawn": {"x": 0, "y": 0}})
    with pytest.raises(ValueError, match="finite and non-negative"):
        UCSSolver(cost_fn=lambda block, board, successor: cost).solve(board)


def test_accumulated_cost_overflow_is_rejected() -> None:
    solver = GraphSolver({"S": [("A", 1e308)], "A": [("G", 1e308)]})
    with pytest.raises(ValueError, match="Accumulated path cost"):
        solver.solve(solver.board)


def test_simple_corridor_and_callback() -> None:
    board = parse_level_data({"layout": ["1112"], "spawn": {"x": 0, "y": 0}})
    solver = UCSSolver()
    result = solver.solve(board)
    assert result.moves == [Direction.RIGHT, Direction.RIGHT]
    assert result.solution_cost == replay(board, result.moves) == 2
    assert result.visited_count == 3
    assert result.expanded_nodes == 2
    assert result.max_depth == 1
    assert result.execution_time_ms >= 0
    assert solver(board) == result.moves


def test_spawn_already_on_goal() -> None:
    board = parse_level_data({"layout": ["2"], "spawn": {"x": 0, "y": 0}})
    result = UCSSolver().solve(board)
    assert result.is_solved
    assert result.moves == []
    assert result.solution_cost == 0
    assert result.visited_count == 1
    assert result.expanded_nodes == result.max_depth == 0


def test_invalid_spawn_is_not_reported_as_unsolvable() -> None:
    board = parse_level_data({"layout": ["32"], "spawn": {"x": 0, "y": 0}})
    with pytest.raises(ValueError, match="Invalid spawn state"):
        UCSSolver().solve(board)


def test_teleport_without_target_configuration_is_invalid() -> None:
    board = parse_level_data({
        "layout": ["1112"], "tiles": {"1,0": 8}, "spawn": {"x": 0, "y": 0},
    })
    with pytest.raises(ValueError, match="teleport.*targets"):
        UCSSolver().solve(board)


@pytest.mark.parametrize("stage", [1, 2, 3])
def test_packaged_solutions_replay_without_mutating_input(stage: int) -> None:
    board = load_level_from_file(LEVELS_DIR / f"stage_{stage:02d}.json")
    original = deepcopy(board)
    result = UCSSolver().solve(board)
    assert result.is_solved
    assert result.solution_cost == replay(board, result.moves)
    assert board.base_tiles == original.base_tiles
    assert board.current_tiles == original.current_tiles
    assert board.get_bridge_state_key() == original.get_bridge_state_key()
    assert board.spawn_state == original.spawn_state


def test_stage_three_prefers_lower_cost_over_fewer_moves() -> None:
    board = parse_level_data({
        "layout": [
            "...111111...",
            "111111111111",
            "111333333111",
            "111333333111",
            "111111111211",
            "...111111...",
        ],
        "spawn": {"x": 1, "y": 1, "orientation": "STANDING"},
    })
    shorter_path = [
        Direction.DOWN, Direction.RIGHT, Direction.RIGHT, Direction.DOWN,
        Direction.RIGHT, Direction.RIGHT, Direction.RIGHT, Direction.RIGHT,
    ]
    assert len(shorter_path) == 8
    assert replay(board, shorter_path) == 10
    result = UCSSolver().solve(board)
    assert len(result.moves) == 9
    assert result.solution_cost == replay(board, result.moves) == 9


def test_unsolvable_level_returns_no_solution_and_callback_is_empty() -> None:
    board = parse_level_data({
        "layout": [
            "1111........",
            "..1111......",
            "....1111....",
            "......1111..",
            "........1111",
            "..........12",
        ],
        "spawn": {"x": 0, "y": 0, "orientation": "STANDING"},
    })
    solver = UCSSolver()
    result = solver.solve(board)
    assert not result.is_solved
    assert result.moves == []
    assert result.solution_cost is None
    assert result.visited_count == result.expanded_nodes == 3
    assert "No solution" in result.message
    assert solver(board) == []


def test_bridge_configurations_have_distinct_state_keys() -> None:
    board = load_level_from_file(LEVELS_DIR / "stage_02.json")
    changed = deepcopy(board)
    changed.trigger_switches(BlockState(2, 2, BlockOrientation.STANDING))
    assert UCSSolver.get_state_key(board.spawn_state, board) != UCSSolver.get_state_key(board.spawn_state, changed)


@pytest.mark.parametrize("switch_type", ["SOFT", "HEAVY"])
@pytest.mark.parametrize("action", ["TOGGLE", "OPEN"])
def test_switch_route_revisits_spawn_with_changed_bridge_state(
    monkeypatch: pytest.MonkeyPatch, switch_type: str, action: str,
) -> None:
    # Isolate UCS from the tracked clone defect without changing production core.
    # The switch is left of spawn, while the goal is beyond the bridge to its right.
    monkeypatch.setattr(Board, "clone", deepcopy)
    board = parse_level_data({
        "layout": ["S11111B112"],
        "spawn": {"x": 3, "y": 0},
        "bridges": [{"id": "b1", "tiles": [[6, 0]], "initially_open": False}],
        "switches": [{"x": 0, "y": 0, "type": switch_type, "targets": ["b1"], "action": action}],
    })
    result = UCSSolver().solve(board)
    assert result.is_solved
    assert result.moves == [Direction.LEFT] * 2 + [Direction.RIGHT] * 6
    assert result.solution_cost == replay(board, result.moves) == 8
    assert board.get_bridge_state_key() == (("b1", False),)


def test_bridge_clone_preserves_dynamic_state() -> None:
    board = load_level_from_file(LEVELS_DIR / "stage_02.json")
    board.trigger_switches(BlockState(2, 2, BlockOrientation.STANDING))
    cloned = board.clone()
    assert cloned.get_bridge_state_key() == board.get_bridge_state_key()
    assert cloned.current_tiles == board.current_tiles


def test_stage_four_solution() -> None:
    board = load_level_from_file(LEVELS_DIR / "stage_04.json")
    result = UCSSolver().solve(board)
    assert result.is_solved
    assert result.solution_cost == replay(board, result.moves) == 56


def test_solver_result_remains_compatible_with_old_positional_arguments() -> None:
    result = SolverResult([], False, 4, 1.5, 2, "Existing caller")
    assert result.message == "Existing caller"
    assert result.expanded_nodes == 0
    assert result.solution_cost is None
    assert "FAILED" in result.summary()
