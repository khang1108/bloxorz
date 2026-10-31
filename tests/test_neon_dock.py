"""The tactical HUD owns screen space instead of covering the 3D board."""

import pytest
from panda3d.core import Point2, Point3
from ursina import camera, scene, window


def test_world_rendering_ends_left_of_both_panels_while_ui_remains_fullscreen(game_app):
    app = game_app
    world_right = (camera.display_region.get_right() - .5) * window.aspect_ratio
    assert world_right < app.minimap.root.x - app.minimap.WIDTH / 2 - .01
    assert world_right < app.solver_widget.root.x - .36 / 2 - .01
    assert camera.display_region.get_bottom() == 0
    assert tuple(camera.ui_display_region.get_dimensions()) == pytest.approx((0, 1, 0, 1))


@pytest.mark.parametrize('ratio', [16 / 9, 4 / 3])
def test_reserved_viewport_keeps_perspective_proportions_after_resize(game_app, monkeypatch, ratio):
    monkeypatch.setattr(type(window), 'aspect_ratio', property(lambda self: ratio))
    game_app.dock.update()
    right = camera.display_region.get_right()
    assert 0 < right < 1
    assert camera.perspective_lens.get_aspect_ratio() == pytest.approx(ratio * right)


def test_menu_releases_reserved_space_and_resume_reinstates_it(game_app):
    game_app.handle_input('escape')
    assert tuple(camera.display_region.get_dimensions()) == pytest.approx((0, 1, 0, 1))
    game_app.resume_game()
    assert camera.display_region.get_right() < 1


def test_resizing_in_a_menu_realigns_sidebar_background_on_resume(game_app, monkeypatch):
    game_app.handle_input('escape')
    monkeypatch.setattr(type(window), 'aspect_ratio', property(lambda self: 4 / 3))
    game_app.resume_game()
    game_app.dock.update()
    world_right = (camera.display_region.get_right() - .5) * window.aspect_ratio
    assert game_app.dock.seam.x == pytest.approx(world_right)
    assert game_app.dock.backplate.x - game_app.dock.WIDTH / 2 == pytest.approx(world_right)


def test_hover_feedback_reuses_entities_and_lights_the_selected_button(game_app):
    widget = game_app.solver_widget
    button = widget.option_buttons['DFS']
    frame = widget.button_frames['DFS']
    idle_alpha = frame.glow.alpha
    count = len(scene.entities)
    button.on_mouse_enter()
    widget.root.update()
    assert frame.glow.alpha > idle_alpha
    for _ in range(100):
        button.on_mouse_exit()
        button.on_mouse_enter()
        widget.root.update()
    assert len(scene.entities) == count
    button.on_mouse_exit()


@pytest.mark.parametrize('stage', [2, 33, 69, 83])
def test_wide_boards_fit_left_of_the_sidebar_at_default_camera_position(game_app, stage):
    game_app.load_stage_by_index(stage, animate_camera=False)
    for x, y in game_app.game.board.base_tiles:
        for dx, dy in ((-.43, -.43), (-.43, .43), (.43, -.43), (.43, .43)):
            relative = camera._cam.get_relative_point(
                game_app.board_view.root, Point3(x + dx, 0, -y - dy)
            )
            projected = Point2()
            assert camera.perspective_lens.project(relative, projected)
            assert -1 <= projected.x <= 1
            assert -1 <= projected.y <= 1


def test_panda_lens_reset_is_corrected_without_rebuilding_the_dock(game_app):
    before = len(scene.entities)
    camera.perspective_lens.set_aspect_ratio(window.aspect_ratio)
    game_app.dock.update()
    right = camera.display_region.get_right()
    assert camera.perspective_lens.get_aspect_ratio() == pytest.approx(window.aspect_ratio * right)
    assert len(scene.entities) == before
