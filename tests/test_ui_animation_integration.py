"""Keep Khoa's world coordinates consistent with Bao's motion and effects."""

import pytest
from ursina import Vec3, application, scene, time

from bloxorz.config import CONFIG
from bloxorz.core.constants import GameStatus, TileType
from bloxorz.solvers import UCSSolver
import bloxorz.graphics.board_view as board_module


def test_restart_keeps_camera_in_the_board_world_frame(game_app):
    game_app.load_stage_by_index(8, animate_camera=False)
    expected = Vec3(game_app.camera_ctrl.default_center)

    game_app.restart_stage()

    assert tuple(game_app.camera_ctrl.target_center) == pytest.approx(tuple(expected))
    assert tuple(game_app.camera_ctrl._board_world_offset) == pytest.approx(game_app.BOARD_WORLD_OFFSET)


def test_victory_focus_targets_the_actual_goal_world_position(game_app):
    board = game_app.game.board
    goal_x, goal_y = board.goal_pos
    expected = scene.get_relative_point(
        game_app.board_view.root, Vec3(goal_x, -0.2, -goal_y)
    )

    game_app.camera_ctrl.animate_victory_focus(goal_x, goal_y)

    assert tuple(game_app.camera_ctrl._victory_target_center) == pytest.approx(tuple(expected))


def test_restart_clears_motion_effects_in_the_board_world_frame(game_app):
    fx = game_app.fx_manager
    local_position = Vec3(2, 0, -3)
    fx.spawn_ghost(local_position, Vec3(0, 0, 0), Vec3(1, 2, 1))
    ghost = next(item for item in fx._ghosts if item.active)
    expected = Vec3(*game_app.BOARD_WORLD_OFFSET) + local_position
    assert tuple(ghost.entity.world_position) == pytest.approx(tuple(expected))

    game_app.restart_stage()

    assert all(not item.active and not item.entity.enabled for item in fx._ghosts)


def test_restart_during_landing_restores_the_new_board_border(game_app, monkeypatch):
    monkeypatch.setattr(CONFIG.animation, 'stage_intro_anim', False)
    app = game_app
    app.restart_stage()
    view = app.board_view
    cell = next(cell for cell, kind in view.tile_types.items() if kind == TileType.NORMAL)

    def border_at_cell():
        return next(part for part in view.tile_parts[cell] if part.name == 'tile_neon_border')

    baseline = tuple(border_at_cell().color)
    generation = view._build_generation
    view.animate_landing([cell])
    assert tuple(border_at_cell().color) != baseline

    app.restart_stage()
    assert view._build_generation > generation
    replacement = border_at_cell()
    for _ in range(5):
        monkeypatch.setattr(time, 'dt', 0.05, raising=False)
        for sequence in list(application.sequences):
            sequence.update()
        view.update()

    assert tuple(replacement.color) == pytest.approx(baseline)
    assert view.tile_entities[cell].y == pytest.approx(CONFIG.board.normal_slab_y)


def test_reopening_bridge_ignores_an_older_close_callback(game_app, monkeypatch):
    game_app.load_stage_by_index(2, animate_camera=False)
    board = game_app.game.board
    group = next(iter(board.bridges.values()))
    view = game_app.board_view
    group.open()
    view.update_bridges(board)

    callbacks = []
    monkeypatch.setattr(board_module, 'invoke', lambda callback, delay: callbacks.append(callback))
    group.close()
    view.update_bridges(board)
    group.open()
    view.update_bridges(board)

    for callback in callbacks:
        callback()

    assert all(view.bridge_entities[cell].visible for cell in group.tiles)


def test_repeated_switch_press_returns_to_its_resting_height(game_app, monkeypatch):
    monkeypatch.setattr(CONFIG.animation, 'stage_intro_anim', False)
    game_app.load_stage_by_index(2, animate_camera=False)
    view = game_app.board_view
    cell, plate = next(iter(view.switch_entities.items()))
    resting_y = plate.y
    callbacks = []
    monkeypatch.setattr(board_module, 'invoke', lambda callback, delay: callbacks.append(callback))

    view.animate_switch_press(*cell)
    plate.y = resting_y - CONFIG.board.switch_press_depth / 2
    view.animate_switch_press(*cell)
    active_animation = plate.y_animator
    callbacks[0]()
    assert plate.y_animator is active_animation, 'An old release interrupted the latest press'
    callbacks[-1]()
    plate.y_animator.finish()

    assert plate.y == pytest.approx(resting_y)


@pytest.mark.parametrize('stage', [1, 8])
def test_solver_route_finishes_through_real_animation_callbacks(game_app, monkeypatch, stage):
    app = game_app
    app.load_stage_by_index(stage, animate_camera=False)
    result = UCSSolver().solve(app.game.board)
    assert result.is_solved
    monkeypatch.setattr(time, 'dt', 0.05, raising=False)

    # Both public feedback entry points are traced, while nested compatibility
    # delegation counts as the same event. A BlockView-triggered pulse is extra.
    feedback_events = []
    inside_landing = False
    original_landing = app.board_view.animate_landing
    original_highlight = app.board_view.highlight_tiles

    def landing(cells):
        nonlocal inside_landing
        feedback_events.append(tuple(cells))
        inside_landing = True
        try:
            original_landing(cells)
        finally:
            inside_landing = False

    def highlight(cells):
        if not inside_landing:
            feedback_events.append(tuple(cells))
        original_highlight(cells)

    monkeypatch.setattr(app.board_view, 'animate_landing', landing)
    monkeypatch.setattr(app.board_view, 'highlight_tiles', highlight)

    for action in result.moves:
        feedback_events.clear()
        previous = app.game.block
        if action == 'SWITCH':
            app.handle_input('space')
        else:
            app.handle_move(action)
        for _ in range(400):
            app.block_view.update()
            app.fx_manager.update()
            if not app.block_view.is_animating:
                break
        assert not app.block_view.is_animating, f'Animation did not complete for {action}'
        if action == 'SWITCH':
            assert feedback_events == [], 'Selecting a split cube must not simulate a landing'
        else:
            assert len(feedback_events) == 1, f'Duplicate landing feedback for {action}: {feedback_events}'
            expected_cells = set(app.game.block.occupied_cells)
            if previous.is_split and app.game.block.is_split:
                expected_cells -= set(previous.occupied_cells)
            assert set(feedback_events[0]) == expected_cells

    assert app.game.status == GameStatus.VICTORY
    assert app.game.move_count == result.solution_length
