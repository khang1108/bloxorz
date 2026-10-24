"""Unit tests for keyboard input handling, normalization, and arrow schemes."""

import time
from unittest.mock import MagicMock, patch
from bloxorz.config import AppConfig, ControlsConfig
from bloxorz.core.constants import Direction
from bloxorz.main import BloxorzApp


def test_classic_arrow_key_directions():
    """In classic mode, arrows map to grid cardinals: Right=+X, Left=-X, Up=-Y, Down=+Y."""
    app = MagicMock(spec=BloxorzApp)
    app.handle_move = MagicMock()
    app._last_input_time = 0.0
    app._last_input_key = ""

    classic_cfg = AppConfig(controls=ControlsConfig(arrow_scheme="classic"))
    with patch("bloxorz.main.CONFIG", classic_cfg):
        # Test right arrow variations
        for key in ("right", "right arrow", "arrow_right", "raw-arrow_right"):
            BloxorzApp.handle_input(app, key)
            app.handle_move.assert_called_with(Direction.RIGHT)
            app.handle_move.reset_mock()
            app._last_input_key = ""  # reset debounce

        # Test left arrow variations
        for key in ("left", "left arrow", "arrow_left", "raw-arrow_left"):
            BloxorzApp.handle_input(app, key)
            app.handle_move.assert_called_with(Direction.LEFT)
            app.handle_move.reset_mock()
            app._last_input_key = ""

        # Test up arrow variations
        for key in ("up", "up arrow", "arrow_up", "raw-arrow_up"):
            BloxorzApp.handle_input(app, key)
            app.handle_move.assert_called_with(Direction.UP)
            app.handle_move.reset_mock()
            app._last_input_key = ""

        # Test down arrow variations
        for key in ("down", "down arrow", "arrow_down", "raw-arrow_down"):
            BloxorzApp.handle_input(app, key)
            app.handle_move.assert_called_with(Direction.DOWN)
            app.handle_move.reset_mock()
            app._last_input_key = ""


def test_classic_wasd_directions():
    """In classic mode, WASD remains mapped to isometric screen diagonals."""
    app = MagicMock(spec=BloxorzApp)
    app.handle_move = MagicMock()
    app._last_input_time = 0.0
    app._last_input_key = ""

    classic_cfg = AppConfig(controls=ControlsConfig(arrow_scheme="classic"))
    with patch("bloxorz.main.CONFIG", classic_cfg):
        BloxorzApp.handle_input(app, "w")
        app.handle_move.assert_called_with(Direction.RIGHT)
        app._last_input_key = ""

        BloxorzApp.handle_input(app, "s")
        app.handle_move.assert_called_with(Direction.LEFT)
        app._last_input_key = ""

        BloxorzApp.handle_input(app, "a")
        app.handle_move.assert_called_with(Direction.UP)
        app._last_input_key = ""

        BloxorzApp.handle_input(app, "d")
        app.handle_move.assert_called_with(Direction.DOWN)


def test_isometric_scheme():
    """In default isometric mode: Up/W=+X, Down/S=-X, Left/A=-Y, Right/D=+Y."""
    app = MagicMock(spec=BloxorzApp)
    app.handle_move = MagicMock()
    app._last_input_time = 0.0
    app._last_input_key = ""

    iso_cfg = AppConfig(controls=ControlsConfig(arrow_scheme="isometric"))
    with patch("bloxorz.main.CONFIG", iso_cfg):
        # Up Arrow & W -> +X (Direction.RIGHT)
        for key in ("up arrow", "arrow_up", "w"):
            BloxorzApp.handle_input(app, key)
            app.handle_move.assert_called_with(Direction.RIGHT)
            app.handle_move.reset_mock()
            app._last_input_key = ""

        # Down Arrow & S -> -X (Direction.LEFT)
        for key in ("down arrow", "arrow_down", "s"):
            BloxorzApp.handle_input(app, key)
            app.handle_move.assert_called_with(Direction.LEFT)
            app.handle_move.reset_mock()
            app._last_input_key = ""

        # Left Arrow & A -> -Y (Direction.UP)
        for key in ("left arrow", "arrow_left", "a"):
            BloxorzApp.handle_input(app, key)
            app.handle_move.assert_called_with(Direction.UP)
            app.handle_move.reset_mock()
            app._last_input_key = ""

        # Right Arrow & D -> +Y (Direction.DOWN)
        for key in ("right arrow", "arrow_right", "d"):
            BloxorzApp.handle_input(app, key)
            app.handle_move.assert_called_with(Direction.DOWN)
            app.handle_move.reset_mock()
            app._last_input_key = ""


def test_input_debouncing():
    """Identical key presses within 50ms should be debounced to prevent double rolls."""
    app = MagicMock(spec=BloxorzApp)
    app.handle_move = MagicMock()
    app._last_input_time = 0.0
    app._last_input_key = ""

    # First event
    BloxorzApp.handle_input(app, "up arrow")
    assert app.handle_move.call_count == 1

    # Second identical event immediately after (< 0.05s) is debounced
    BloxorzApp.handle_input(app, "up arrow")
    assert app.handle_move.call_count == 1

    # Wait past debounce window
    time.sleep(0.06)
    BloxorzApp.handle_input(app, "up arrow")
    assert app.handle_move.call_count == 2


def test_escape_key_toggles_stage_select_menu():
    """Pressing Escape or raw-escape should open the stage select menu if closed, or close it if open."""
    app = MagicMock(spec=BloxorzApp)
    app.current_stage_idx = 3
    app._last_input_time = 0.0
    app._last_input_key = ""
    app.menu_mgr = MagicMock()

    # Case 1: Menu is closed -> opens stage select menu
    app.menu_mgr.is_any_menu_open.return_value = False
    BloxorzApp.handle_input(app, "escape")
    app.menu_mgr.show_stage_select_menu.assert_called_with(3)
    app.menu_mgr.close_all.assert_not_called()

    # Case 2: Menu is open -> closes menu
    app._last_input_key = ""  # reset debounce
    app.menu_mgr.reset_mock()
    app.menu_mgr.is_any_menu_open.return_value = True
    BloxorzApp.handle_input(app, "raw-escape")
    app.menu_mgr.close_all.assert_called_once()
    app.menu_mgr.show_stage_select_menu.assert_not_called()


def test_raw_key_normalization():
    """Linux raw-prefixed keys (raw-u, raw-r, raw-m, raw-p) should trigger their actions."""
    app = MagicMock(spec=BloxorzApp)
    app._last_input_time = 0.0
    app._last_input_key = ""
    app.handle_undo = MagicMock()
    app.restart_stage = MagicMock()
    app.sound_mgr = MagicMock()
    app.trigger_solver = MagicMock()

    # raw-u -> undo
    BloxorzApp.handle_input(app, "raw-u")
    app.handle_undo.assert_called_once()

    # raw-r -> restart
    app._last_input_key = ""
    BloxorzApp.handle_input(app, "raw-r")
    app.restart_stage.assert_called_once()

    # raw-m -> audio
    app._last_input_key = ""
    BloxorzApp.handle_input(app, "raw-m")
    app.sound_mgr.toggle_audio.assert_called_once()

    # raw-p -> solver
    app._last_input_key = ""
    BloxorzApp.handle_input(app, "raw-p")
    app.trigger_solver.assert_called_once()
