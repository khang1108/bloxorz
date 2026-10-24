"""Unit tests for Settings overlay, volume gauge formatting, and menu navigation."""

from unittest.mock import MagicMock
from bloxorz.ui.menu import format_volume_gauge, MenuManager
from bloxorz.main import BloxorzApp


def test_format_volume_gauge():
    """Verifies that format_volume_gauge produces expected percentages and VU-meter characters."""
    gauge_0 = format_volume_gauge(0.0)
    assert "  0%" in gauge_0
    assert "[ ---------- ]" in gauge_0

    gauge_50 = format_volume_gauge(0.5)
    assert " 50%" in gauge_50
    assert "[ |||||----- ]" in gauge_50

    gauge_80 = format_volume_gauge(0.8)
    assert " 80%" in gauge_80
    assert "[ ||||||||-- ]" in gauge_80

    gauge_100 = format_volume_gauge(1.0)
    assert "100%" in gauge_100
    assert "[ |||||||||| ]" in gauge_100


def test_menu_manager_settings_overlay_lifecycle():
    """Tests opening and closing the Settings modal overlay in MenuManager."""
    mock_sound_mgr = MagicMock()
    mock_sound_mgr.bgm_enabled = True
    mock_sound_mgr.bgm_volume = 0.5
    mock_sound_mgr.sfx_enabled = True
    mock_sound_mgr.sfx_volume = 0.8
    mock_sound_mgr.theme_track = "background.mp3"

    mm = MenuManager(
        on_resume=MagicMock(),
        on_restart=MagicMock(),
        on_select_stage=MagicMock(),
        on_next_stage=MagicMock(),
        on_toggle_audio=mock_sound_mgr.toggle_audio,
        get_audio_status=lambda: True,
        stages_count=33,
        sound_mgr=mock_sound_mgr,
    )

    assert mm.is_settings_open() is False
    assert mm.is_any_menu_open() is False

    # Mock Ursina camera.ui and Entity creation to avoid GUI requirements
    mm.settings_root = MagicMock()
    assert mm.is_settings_open() is True
    assert mm.is_any_menu_open() is True

    mm.close_all()
    assert mm.is_settings_open() is False
    assert mm.is_any_menu_open() is False


def test_o_key_toggles_settings_menu():
    """Pressing 'o' or 'raw-o' should toggle the settings menu."""
    app = MagicMock(spec=BloxorzApp)
    app.current_stage_idx = 5
    app._last_input_time = 0.0
    app._last_input_key = ""
    app.menu_mgr = MagicMock()
    app.camera_ctrl = MagicMock()

    # Case 1: Settings is closed -> opens settings menu
    app.menu_mgr.is_settings_open.return_value = False
    BloxorzApp.handle_input(app, "o")
    app.menu_mgr.show_settings_menu.assert_called_with(5)
    app.menu_mgr.close_all.assert_not_called()

    # Case 2: Settings is open -> closes settings
    app._last_input_key = ""  # reset debounce
    app.menu_mgr.reset_mock()
    app.menu_mgr.is_settings_open.return_value = True
    BloxorzApp.handle_input(app, "raw-o")
    app.menu_mgr.close_all.assert_called_once()
    app.menu_mgr.show_settings_menu.assert_not_called()
