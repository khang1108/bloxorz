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


def test_ui_constants_definitions():
    """Verifies that all UI layout constants and anchors are well-formed."""
    from bloxorz.ui.constants import HUDConstants, MenuConstants, UIAnchor

    assert HUDConstants.STAGE_POS == (-0.82, 0.44)
    assert HUDConstants.STAGE_SCALE == 1.35
    assert HUDConstants.STAGE_ORIGIN == UIAnchor.TOP_LEFT

    assert HUDConstants.MOVES_POS == (0.82, 0.44)
    assert HUDConstants.MOVES_SCALE == 1.20
    assert HUDConstants.MOVES_ORIGIN == UIAnchor.TOP_RIGHT

    assert MenuConstants.BACKDROP_SCALE == (2.5, 2.0)
    assert MenuConstants.GRID_COLUMNS == 7
    assert MenuConstants.Z_BACKDROP == 1.0
    assert MenuConstants.Z_FOREGROUND_TEXT == 0.0
    assert MenuConstants.MINIMALIST_BTN_SCALE == (0.45, 0.065)
    assert MenuConstants.STAGE_CARD_SCALE == (0.142, 0.050)
    assert MenuConstants.SETTING_TOGGLE_BTN_SCALE == (0.16, 0.046)


def test_button_text_scale_stability_on_hover():
    """Verifies that hovering over menu buttons does not shrink or distort text world_scale."""
    from ursina import Ursina, application, camera
    from bloxorz.ui.menu import (
        MinimalistButton,
        StageCardButton,
        MenuActionButton,
        SettingToggleButton,
        SettingStepperButton,
    )

    if application.base is None:
        Ursina(headless=True)

    buttons = [
        ("MinimalistButton", MinimalistButton("TEST", parent=camera.ui, y=0)),
        ("StageCardButton", StageCardButton(1, False, camera.ui, 0, 0)),
        ("MenuActionButton", MenuActionButton("CONTINUE", camera.ui, 0, 0)),
        ("SettingToggleButton", SettingToggleButton(True, lambda: True, camera.ui, 0, 0)),
        ("SettingStepperButton", SettingStepperButton("+", lambda: None, camera.ui, 0, 0)),
    ]

    for name, btn in buttons:
        initial_scale = btn.text_entity.world_scale
        btn.on_mouse_enter()
        hover_scale = btn.text_entity.world_scale
        btn.on_mouse_exit()
        exit_scale = btn.text_entity.world_scale

        assert abs(initial_scale.x - hover_scale.x) < 1e-4, f"{name} text shrank or changed on hover!"
        assert abs(initial_scale.x - exit_scale.x) < 1e-4, f"{name} text scale did not persist on exit!"


def test_victory_menu_buttons_scale_stability():
    """Verifies that all 3 action buttons in victory menu retain constant text scale on hover."""
    from ursina import Ursina, application
    from bloxorz.ui.menu import MenuManager

    if application.base is None:
        Ursina(headless=True)

    mm = MenuManager(
        on_resume=MagicMock(),
        on_restart=MagicMock(),
        on_select_stage=MagicMock(),
        on_next_stage=MagicMock(),
        on_toggle_audio=MagicMock(),
        get_audio_status=lambda: True,
    )

    mm.show_victory_menu("Stage 01", 10, 1)
    btns = [c for c in mm.victory_root.children if hasattr(c, "text_entity") and c.text_entity]
    assert len(btns) == 3

    for b in btns:
        s0 = b.text_entity.world_scale.x
        b.on_mouse_enter()
        s1 = b.text_entity.world_scale.x
        b.on_mouse_exit()
        s2 = b.text_entity.world_scale.x

        assert abs(s0 - s1) < 1e-4, f"Victory button '{b.text}' text shrank on hover!"
        assert abs(s0 - s2) < 1e-4, f"Victory button '{b.text}' text scale failed to persist!"


def test_hud_banner_autohide_and_lifecycle(monkeypatch):
    """Verifies that HUD banner shows correctly and automatically dismisses after duration."""
    from ursina import Ursina, application
    from bloxorz.ui.hud import HUD

    if application.base is None:
        Ursina(headless=True)

    invoked_calls = []

    def mock_invoke(fn, *args, **kwargs):
        invoked_calls.append((fn, kwargs.get("delay", 0)))

    monkeypatch.setattr("bloxorz.ui.hud.invoke", mock_invoke)

    hud = HUD()
    assert not hud.banner_text.visible

    # Show banner with default auto-hide
    hud.show_banner("BLOCKS MERGED", duration=1.5)
    assert hud.banner_text.visible
    assert hud.banner_text.text == "BLOCKS MERGED"
    assert len(invoked_calls) == 1
    callback, delay = invoked_calls[0]
    assert delay == 1.5

    # Triggering the callback auto-hides banner
    callback()
    assert not hud.banner_text.visible

    # Race condition test: A second banner should not be dismissed by the first timer
    invoked_calls.clear()
    hud.show_banner("FIRST BANNER", duration=1.0)
    first_cb, _ = invoked_calls[0]

    hud.show_banner("SECOND BANNER", duration=1.5)
    second_cb, _ = invoked_calls[1]
    assert hud.banner_text.text == "SECOND BANNER"
    assert hud.banner_text.visible

    # Trigger old timer - should be ignored because banner_id changed
    first_cb()
    assert hud.banner_text.visible
    assert hud.banner_text.text == "SECOND BANNER"

    # Trigger current timer - dismisses correctly
    second_cb()
    assert not hud.banner_text.visible
