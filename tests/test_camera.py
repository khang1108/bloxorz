"""Unit tests for CameraController 3D orbit, zoom, step rotation, and framing."""

from unittest.mock import MagicMock
from bloxorz.config import CONFIG
from bloxorz.graphics.camera_ctrl import CameraController
from bloxorz.main import BloxorzApp


def test_camera_default_initialization():
    """CameraController should initialize with config defaults and limits."""
    cam = CameraController()
    cfg = CONFIG.camera

    assert cam.default_pitch == cfg.angle_x
    assert cam.default_yaw == cfg.angle_y
    assert cam.current_pitch == cfg.angle_x
    assert cam.current_yaw == cfg.angle_y
    assert cam.min_pitch == cfg.min_pitch
    assert cam.max_pitch == cfg.max_pitch
    assert cam.step_orbit_angle == cfg.step_orbit_angle
    assert cam.enabled_controls is True


def test_camera_orbit_and_pitch_clamping():
    """Orbit should modify target yaw and clamp target pitch within [min_pitch, max_pitch]."""
    cam = CameraController()
    initial_yaw = cam.target_yaw

    # Yaw changes freely
    cam.orbit(delta_x=0.5, delta_y=0.0)
    assert cam.target_yaw == initial_yaw + 0.5 * cam.orbit_speed_x

    # Pitch up beyond max_pitch clamps to max_pitch
    cam.orbit(delta_x=0.0, delta_y=10.0)
    assert cam.target_pitch == cam.max_pitch

    # Pitch down beyond min_pitch clamps to min_pitch
    cam.orbit(delta_x=0.0, delta_y=-20.0)
    assert cam.target_pitch == cam.min_pitch


def test_camera_zoom_and_distance_clamping():
    """Zoom in/out should adjust distance and clamp between min and max zoom distance."""
    cam = CameraController()
    cam.frame_board(min_x=0, max_x=10, min_y=0, max_y=10, animate=False)
    base_dist = cam.base_distance

    # Zoom in (direction < 0) reduces distance
    cam.zoom(-1.0)
    assert cam.target_distance < base_dist

    # Excessive zoom in clamps to min_zoom_distance
    cam.zoom(-50.0)
    assert cam.target_distance == cam.min_zoom_distance

    # Excessive zoom out clamps to max_zoom_distance
    cam.zoom(100.0)
    assert cam.target_distance == cam.max_zoom_distance


def test_camera_step_orbit():
    """Step orbit (Q/E) should rotate target yaw by step_orbit_angle in either direction."""
    cam = CameraController()
    initial_yaw = cam.target_yaw
    step = cam.step_orbit_angle

    cam.step_orbit(1)
    assert cam.target_yaw == initial_yaw + step

    cam.step_orbit(-1)
    assert cam.target_yaw == initial_yaw


def test_camera_reset_view():
    """Reset view should restore canonical angles, base distance, and board center."""
    cam = CameraController()
    cam.frame_board(min_x=0, max_x=10, min_y=0, max_y=10, animate=False)

    # Disturb camera
    cam.orbit(1.5, 0.8)
    cam.zoom(2.0)

    # Reset
    cam.reset_view(animate=False)
    assert cam.target_yaw == cam.default_yaw
    assert cam.target_pitch == cam.default_pitch
    assert cam.target_distance == cam.base_distance
    assert cam.current_yaw == cam.default_yaw
    assert cam.current_pitch == cam.default_pitch


def test_camera_keyboard_and_wheel_shortcuts_in_main():
    """Main input handler should route Q/E, C, scroll, and +/- to CameraController."""
    app = MagicMock(spec=BloxorzApp)
    app._last_input_time = 0.0
    app._last_input_key = ""
    app.camera_ctrl = MagicMock()

    # Reset (C)
    BloxorzApp.handle_input(app, "c")
    app.camera_ctrl.reset_view.assert_called_once()

    # Rotate Left (Q)
    app._last_input_key = ""
    BloxorzApp.handle_input(app, "q")
    app.camera_ctrl.step_orbit.assert_called_with(-1)

    # Rotate Right (E)
    app._last_input_key = ""
    BloxorzApp.handle_input(app, "e")
    app.camera_ctrl.step_orbit.assert_called_with(1)

    # Zoom In (scroll up, +)
    app._last_input_key = ""
    BloxorzApp.handle_input(app, "scroll up")
    app.camera_ctrl.zoom.assert_called_with(-1.0)

    app._last_input_key = ""
    BloxorzApp.handle_input(app, "+")
    app.camera_ctrl.zoom.assert_called_with(-1.0)

    # Zoom Out (scroll down, -)
    app._last_input_key = ""
    BloxorzApp.handle_input(app, "scroll down")
    app.camera_ctrl.zoom.assert_called_with(1.0)

    app._last_input_key = ""
    BloxorzApp.handle_input(app, "-")
    app.camera_ctrl.zoom.assert_called_with(1.0)
