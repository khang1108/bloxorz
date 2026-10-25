"""Exercise launcher binding and P/restart/stage playback without a GUI window."""

from functools import partial
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple
from unittest.mock import Mock

import pytest

import bloxorz.main as app_module
import run as launcher
from bloxorz.core.block import BlockState
from bloxorz.core.constants import Direction, GameStatus
from bloxorz.core.game import Game
from bloxorz.core.level_loader import load_level_from_file, parse_level_data
from bloxorz.main import BloxorzApp
from bloxorz.solvers import UCSSolver


LEVELS_DIR = Path(__file__).resolve().parents[1] / "bloxorz" / "levels"


@pytest.fixture
def runtime(monkeypatch: pytest.MonkeyPatch) -> Tuple[BloxorzApp, List[Callable[[], None]]]:
    """Use the actual controller/core, replacing rendering and delayed scheduling."""
    app = BloxorzApp.__new__(BloxorzApp)
    app.game = Game(parse_level_data({"layout": ["1112"], "spawn": {"x": 0, "y": 0}}))
    app.registered_solver = UCSSolver()
    app._is_playing_solution = False
    app._active_solution = []
    app._solution_idx = 0
    app._solution_delay = 0.08
    app._on_solution_complete = None
    app._solution_generation = 0
    app.stage_files = [LEVELS_DIR / "stage_01.json"]
    app.current_stage_idx = 1
    app.hud = Mock()
    app.sound_mgr = Mock()
    app.menu_mgr = Mock()
    app.board_view = Mock()
    app.camera_ctrl = Mock()
    app.block_view = Mock(is_animating=False)

    def roll_animated(
        prev_state: BlockState, next_state: BlockState, direction: Direction,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_complete:
            on_complete()

    app.block_view.roll_animated.side_effect = roll_animated
    pending: List[Callable[[], None]] = []

    def schedule(callback: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        pending.append(partial(callback, *args))

    monkeypatch.setattr(app_module, "invoke", schedule)
    return app, pending


def drain(pending: List[Callable[[], None]]) -> None:
    """Run scheduled events while guarding against accidental infinite playback."""
    for _ in range(50):
        if not pending:
            return
        pending.pop(0)()
    pytest.fail("Playback did not finish within 50 scheduled callbacks.")


def test_standard_launcher_registers_ucs(monkeypatch: pytest.MonkeyPatch) -> None:
    launch = Mock()
    monkeypatch.setattr(launcher, "launch", launch)
    launcher.main()
    solver = launch.call_args.kwargs["solver"]
    assert isinstance(solver, UCSSolver)
    board = load_level_from_file(LEVELS_DIR / "stage_03.json")
    assert len(solver(board)) == 9


def test_module_launcher_registers_ucs(
    runtime: Tuple[BloxorzApp, List[Callable[[], None]]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _ = runtime
    engine = Mock()
    app.registered_solver = None
    monkeypatch.setattr(app_module, "Ursina", lambda: engine)
    monkeypatch.setattr(app_module, "BloxorzApp", lambda: app)
    monkeypatch.setattr(app_module, "InputHandler", Mock())
    app_module.main()
    assert isinstance(app.registered_solver, UCSSolver)
    engine.run.assert_called_once_with()


def test_p_restarts_partial_game_and_replays_to_victory(
    runtime: Tuple[BloxorzApp, List[Callable[[], None]]],
) -> None:
    app, pending = runtime
    app.game.roll(Direction.RIGHT)
    app.handle_input("p")
    drain(pending)
    assert app.game.status == GameStatus.VICTORY
    assert app.game.move_count == 2
    assert not app._is_playing_solution


def test_missing_solver_is_visible(runtime: Tuple[BloxorzApp, List[Callable[[], None]]]) -> None:
    app, pending = runtime
    app.registered_solver = None
    app.handle_input("p")
    app.hud.show_banner.assert_called_once_with("NO SOLVER REGISTERED")
    assert not pending


def test_failed_search_is_visible(runtime: Tuple[BloxorzApp, List[Callable[[], None]]]) -> None:
    app, pending = runtime
    app.game = Game(load_level_from_file(LEVELS_DIR / "stage_05.json"))
    app.handle_input("p")
    app.hud.show_banner.assert_called_once_with("SOLVER FOUND NO SOLUTION")
    assert not app._is_playing_solution
    assert not pending


def test_unsupported_stage_is_visible(runtime: Tuple[BloxorzApp, List[Callable[[], None]]]) -> None:
    app, pending = runtime
    app.game = Game(parse_level_data({
        "layout": ["1112"], "spawn": {"x": 0, "y": 0}, "tiles": {"1,0": 8},
    }))
    app.handle_input("p")
    app.hud.show_banner.assert_called_once_with("SOLVER DOES NOT SUPPORT THIS STAGE")
    assert not pending


def test_zero_move_solution_is_not_reported_as_failure(
    runtime: Tuple[BloxorzApp, List[Callable[[], None]]],
) -> None:
    app, pending = runtime
    app.game = Game(parse_level_data({"layout": ["2"], "spawn": {"x": 0, "y": 0}}))
    app.handle_input("p")
    app.hud.show_banner.assert_called_once_with("ALREADY AT GOAL")
    assert not pending


def test_restart_cancels_pending_solver_moves(runtime: Tuple[BloxorzApp, List[Callable[[], None]]]) -> None:
    app, pending = runtime
    app.handle_input("p")
    assert app._is_playing_solution
    app.handle_input("r")
    drain(pending)
    assert app.game.block == app.game.board.spawn_state
    assert app.game.move_count == 0
    assert not app._is_playing_solution


def test_old_callback_cannot_advance_new_solution(runtime: Tuple[BloxorzApp, List[Callable[[], None]]]) -> None:
    app, pending = runtime
    app.handle_input("p")
    app.handle_input("r")
    app.handle_input("p")
    drain(pending)
    assert app.game.status == GameStatus.VICTORY
    assert app.game.move_count == 2
    assert not app._is_playing_solution


def test_stage_change_cancels_playback_and_allows_p_again(
    runtime: Tuple[BloxorzApp, List[Callable[[], None]]],
) -> None:
    app, pending = runtime
    app.handle_input("p")
    app.load_stage_by_index(1)
    drain(pending)
    assert app.game.move_count == 0
    assert not app._is_playing_solution
    app.handle_input("p")
    drain(pending)
    assert app.game.status == GameStatus.VICTORY
