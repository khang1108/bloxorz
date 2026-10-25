from pathlib import Path

from bloxorz.core.block.normal import NormalBlockState
from bloxorz.core.block.split import SingleBlock, SplitBlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import BlockOrientation, Direction, GameStatus, TileType
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file, parse_level_data
from bloxorz.main import BloxorzApp
from bloxorz.solvers.bfs import BFSSolver


def replay_solution(board, moves):
    game = Game(board.clone())
    for move in moves:
        if move in ("_", "SWITCH"):
            assert game.switch_block()
            continue

        outcome, _, _ = game.roll(move)
        assert outcome in ("SAFE", "MERGED", "TELEPORT", "VICTORY")
        if outcome == "VICTORY":
            break

    assert game.status == GameStatus.VICTORY


def test_bfs_solves_teleport_stage_with_split_switching():
    board = load_level_from_file(Path("bloxorz/levels/stage_08.json"))

    result = BFSSolver().solve(board)

    assert result.is_solved
    assert "_" in result.moves
    assert result.expanded_nodes > 0
    assert result.peak_memory_bytes > 0
    replay_solution(board, result.moves)


def test_bfs_solves_normal_stage_with_direction_moves():
    board = load_level_from_file(Path("bloxorz/levels/stage_04.json"))

    result = BFSSolver().solve(board)

    assert result.is_solved
    assert all(isinstance(move, Direction) for move in result.moves)
    replay_solution(board, result.moves)


def test_bfs_solves_from_current_normal_block_state():
    board = load_level_from_file(Path("bloxorz/levels/stage_04.json"))
    solver = BFSSolver()
    initial_result = solver.solve(board)
    assert initial_result.is_solved

    game = Game(board.clone())
    first_outcome, _, _ = game.roll(initial_result.moves[0])
    assert first_outcome in ("SAFE", "MERGED", "TELEPORT")
    assert game.block != board.spawn_state

    moves = solver.solve_from(game.board, game.block)

    assert moves
    for move in moves:
        if move == "_":
            assert game.switch_block()
            continue
        outcome, _, _ = game.roll(move)
        assert outcome in ("SAFE", "MERGED", "TELEPORT", "VICTORY")
        if outcome == "VICTORY":
            break
    assert game.status == GameStatus.VICTORY


def test_bfs_solves_from_current_split_block_state():
    board = load_level_from_file(Path("bloxorz/levels/stage_08.json"))
    solver = BFSSolver()
    initial_result = solver.solve(board)
    assert initial_result.is_solved

    game = Game(board.clone())
    for move in initial_result.moves:
        if move == "_":
            assert game.switch_block()
            continue
        outcome, _, _ = game.roll(move)
        assert outcome in ("SAFE", "MERGED", "TELEPORT", "VICTORY")
        if game.block.is_split:
            break

    assert game.block.is_split
    moves = solver.solve_from(game.board, game.block)

    assert moves
    for move in moves:
        if move == "_":
            assert game.switch_block()
            continue
        outcome, _, _ = game.roll(move)
        assert outcome in ("SAFE", "MERGED", "TELEPORT", "VICTORY")
        if outcome == "VICTORY":
            break
    assert game.status == GameStatus.VICTORY


def test_bfs_reports_no_path_from_softlocked_split_state():
    board = Board(
        tiles={
            (0, 0): TileType.NORMAL,
            (4, 0): TileType.NORMAL,
            (8, 0): TileType.GOAL,
        },
        goal_pos=(8, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    split_block = SplitBlockState(SingleBlock(0, 0), SingleBlock(4, 0))

    moves = BFSSolver().solve_from(board, split_block)

    assert moves == []


def test_bfs_preserves_current_bridge_configuration():
    board = parse_level_data({
        "layout": ["1SB"],
        "spawn": {"x": 0, "y": 0, "orientation": "STANDING"},
        "bridges": [{"id": "b1", "tiles": [[2, 0]], "initially_open": False}],
        "switches": [{"x": 1, "y": 0, "type": "SOFT", "targets": ["b1"]}],
    })
    bridge = board.bridges["b1"]
    bridge.open()
    board._sync_bridge_tiles(bridge)

    cloned_board = board.clone()

    assert cloned_board.get_bridge_state_key() == board.get_bridge_state_key()
    assert cloned_board.get_tile(*bridge.tiles[0]) == board.get_tile(*bridge.tiles[0])


def test_restart_cancels_queued_solver_playback():
    app = BloxorzApp.__new__(BloxorzApp)
    app._is_playing_solution = True
    app._active_solution = [Direction.RIGHT, Direction.LEFT]
    app._solution_idx = 1
    app._solution_generation = 2
    app.game = type(
        "FakeGame",
        (),
        {
            "board": type("FakeBoard", (), {"spawn_state": object()})(),
            "block": object(),
            "restart": lambda self: None,
        },
    )()
    app.block_view = type(
        "FakeBlockView",
        (),
        {"sync_to_state": lambda self, state: None},
    )()
    app.board_view = type("FakeBoardView", (), {"update_bridges": lambda self, board: None})()
    app.hud = type(
        "FakeHUD",
        (),
        {
            "update_moves": lambda self, moves: None,
            "hide_banner": lambda self: None,
            "set_split_mode": lambda self, is_split: None,
        },
    )()
    app.menu_mgr = type("FakeMenu", (), {"close_all": lambda self: None})()
    app.camera_ctrl = type(
        "FakeCamera",
        (),
        {"reset_view": lambda self, animate: None, "enabled_controls": True},
    )()

    app.restart_stage()

    assert app._is_playing_solution is False
    assert app._active_solution == []
    assert app._solution_idx == 0
    assert app._solution_generation == 3


def test_stale_solver_callback_cannot_advance_new_solution():
    app = BloxorzApp.__new__(BloxorzApp)
    app._solution_generation = 3
    app._is_playing_solution = True
    app._solution_idx = 0
    app._active_solution = [Direction.DOWN]

    app._play_next_solver_step(generation=2)

    assert app._solution_idx == 0


def test_app_playback_keeps_teleporter_selected_cube(monkeypatch):
    board = load_level_from_file(Path("bloxorz/levels/stage_09.json"))
    solver = BFSSolver()
    initial_solution = solver.solve(board)
    assert initial_solution.is_solved
    app = BloxorzApp.__new__(BloxorzApp)
    app.registered_solver = solver
    app.game = Game(board.clone())
    first_outcome, _, _ = app.game.roll(initial_solution.moves[0])
    assert first_outcome in ("SAFE", "MERGED", "TELEPORT")
    app._is_playing_solution = False
    app._active_solution = []
    app._solution_idx = 0
    app._solution_delay = 0
    app._on_solution_complete = None
    app._solution_generation = 0
    app.hud = type(
        "FakeHUD",
        (),
        {
            "show_banner": lambda self, *args, **kwargs: None,
            "update_moves": lambda self, moves: None,
            "set_split_mode": lambda self, is_split: None,
        },
    )()
    app.sound_mgr = type("FakeSound", (), {"play": lambda self, sound: None})()
    app.camera_ctrl = type(
        "FakeCamera",
        (),
        {"animate_victory_focus": lambda self, x, y: None},
    )()
    app.menu_mgr = type(
        "FakeMenu",
        (),
        {"show_victory_menu": lambda self, *args: None},
    )()

    class ImmediateBlockView:
        is_animating = False

        def roll_animated(self, prev_state, next_state, direction, on_complete, **kwargs):
            if not prev_state.is_split and next_state.is_split:
                self.teleport_active_index = next_state.active_index
            on_complete()

        def animate_victory(self, on_complete=None):
            pass

        def sync_to_state(self, state):
            pass

    app.block_view = ImmediateBlockView()
    monkeypatch.setattr(
        "bloxorz.main.invoke",
        lambda callback, *args, **kwargs: callback(*args),
    )

    app.trigger_solver()

    assert app.block_view.teleport_active_index == 1
    assert app.game.status == GameStatus.VICTORY
    assert app._is_playing_solution is False
