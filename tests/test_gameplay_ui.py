"""Cover solver worker boundaries and map synchronization through the real app."""

import threading

import pytest
from ursina import time as ursina_time

from bloxorz.config import CONFIG
from bloxorz.core.block import SplitBlockState
from bloxorz.core.constants import Direction
from bloxorz.core.game import Game


@pytest.fixture
def deferred_workers(monkeypatch):
    workers = []

    class DeferredThread:
        def __init__(self, target, daemon):
            self.target = target
            self.alive = False
            workers.append(self)

        def start(self):
            self.alive = True

        def is_alive(self):
            return self.alive

        def finish(self):
            self.target()
            self.alive = False

    monkeypatch.setattr(threading, 'Thread', DeferredThread)
    return workers


def test_search_starts_once_and_holds_busy_state_until_main_thread_delivery(game_app, deferred_workers):
    app = game_app
    calls = []
    app.register_solver(lambda board: calls.append(board) or [Direction.RIGHT])
    app.trigger_solver()
    assert calls == []
    assert app.solver_widget.is_running
    app.trigger_solver()
    deferred_workers[0].finish()
    app.input_handler.update()
    assert len(calls) == 1
    assert app._is_playing_solution
    assert app._active_solution == [Direction.RIGHT]


@pytest.mark.parametrize('reset', ['restart_stage', 'next_stage', 'stop_solution'])
def test_reset_or_stop_discards_a_late_worker_result(game_app, deferred_workers, reset):
    app = game_app
    app.register_solver(lambda board: [Direction.RIGHT])
    app.trigger_solver()
    getattr(app, reset)()
    deferred_workers[0].finish()
    app.input_handler.update()
    assert not app._is_playing_solution
    assert not app.block_view.is_animating
    assert app.game.block == app.game.board.spawn_state
    assert not app.solver_widget.is_running


def test_stopped_search_cannot_overlap_a_second_worker(game_app, deferred_workers):
    app = game_app
    app.register_solver(lambda board: [Direction.RIGHT])
    app.trigger_solver()
    app.stop_solution()
    app.trigger_solver()
    assert len(deferred_workers) == 1
    deferred_workers[0].finish()
    app.input_handler.update()
    app.trigger_solver()
    assert len(deferred_workers) == 2


def test_stopping_a_search_clears_its_persistent_computing_message(game_app, deferred_workers):
    app = game_app
    app.register_solver(lambda board: [Direction.RIGHT])
    app.trigger_solver()
    assert app.hud.banner_text.visible
    app.toggle_solver()
    assert not app.hud.banner_text.visible
    assert not app.solver_widget.is_running


def test_worker_error_releases_controls_and_cannot_mutate_the_live_board(game_app, deferred_workers):
    app = game_app
    app.load_stage_by_index(2, animate_camera=False)
    original_key = app.game.board.get_bridge_state_key()

    def failing_solver(board):
        next(iter(board.bridges.values())).toggle()
        raise ValueError('bad solver result')

    app.register_solver(failing_solver)
    app.trigger_solver()
    deferred_workers[0].finish()
    app.input_handler.update()
    assert app.game.board.get_bridge_state_key() == original_key
    assert not app.solver_widget.is_running
    assert not app._is_playing_solution
    assert app.hud.banner_text.text == 'SOLVER ERROR'


def test_real_moves_undo_and_restart_keep_minimap_on_the_game_state(game_app, monkeypatch):
    app = game_app
    monkeypatch.setattr(ursina_time, 'dt', .3, raising=False)
    spawn_position = tuple(app.minimap.block_markers[0].position)
    app.handle_move(Direction.RIGHT)
    app.block_view.update()
    assert len(app.game.block.occupied_cells) == 2
    assert [marker.enabled for marker in app.minimap.block_markers] == [True, False]
    assert app.minimap.block_markers[0].body.scale_x > app.minimap.block_markers[0].body.scale_y
    app.handle_undo()
    assert tuple(app.minimap.block_markers[0].position) == spawn_position
    assert not app.minimap.block_markers[1].enabled
    app.handle_move(Direction.RIGHT)
    app.block_view.update()
    app.restart_stage()
    assert tuple(app.minimap.block_markers[0].position) == spawn_position


def test_completed_roll_pulses_only_the_landing_borders(game_app, monkeypatch):
    app = game_app
    monkeypatch.setattr(CONFIG.animation, 'stage_intro_anim', False)
    app.restart_stage()
    borders = {
        cell: next(part for part in parts if part.name == 'tile_neon_border')
        for cell, parts in app.board_view.tile_parts.items()
        if any(part.name == 'tile_neon_border' for part in parts)
    }
    original_colors = {cell: tuple(border.color) for cell, border in borders.items()}
    app.handle_move(Direction.RIGHT)
    monkeypatch.setattr(ursina_time, 'dt', .3, raising=False)
    app.block_view.update()

    pulsing_cells = {
        cell for cell, border in borders.items() if tuple(border.color) != original_colors[cell]
    }
    assert pulsing_cells == app.game.block.occupied_cells
    assert not any(entity.name == 'tile_landing_flash' for entity in app.board_view.root.children)


def test_undo_between_solver_steps_cancels_the_remaining_playback(game_app, monkeypatch):
    app = game_app
    monkeypatch.setattr(ursina_time, 'dt', .3, raising=False)
    app.play_solution([Direction.RIGHT, Direction.RIGHT])
    app.block_view.update()
    generation = app._solution_generation
    assert app._is_playing_solution
    app.handle_input('u')
    assert not app._is_playing_solution
    assert app.game.block == app.game.board.spawn_state
    app._play_next_solver_step(generation=generation)
    assert app.game.block == app.game.board.spawn_state
    assert not app.solver_widget.is_running


def test_space_switch_and_stage_change_update_the_map(game_app):
    app = game_app
    app.game.block = SplitBlockState.from_targets((1, 1), (4, 4))
    app.block_view.sync_to_state(app.game.block)
    app.minimap.sync(app.game.board, app.game.block)
    first_color = tuple(app.minimap.block_markers[0].color)
    app.handle_input('space')
    assert tuple(app.minimap.block_markers[1].color) == pytest.approx(first_color)
    app.load_stage_by_index(54, animate_camera=False)
    assert set(app.minimap.tile_entities) == set(app.game.board.current_tiles)


def test_menu_hides_map_and_buttons_and_resume_restores_them(game_app):
    app = game_app
    app.handle_input('escape')
    assert not app.minimap.root.enabled
    assert not app.solver_widget.root.enabled
    app.resume_game()
    assert app.minimap.root.enabled
    assert app.solver_widget.root.enabled


@pytest.mark.parametrize('algorithm', ['BFS', 'DFS', 'UCS', 'A*'])
def test_each_real_button_runs_its_real_solver_and_returns_a_winning_path(game_app, algorithm):
    app = game_app
    app.solver_widget.option_buttons[algorithm].on_click()
    app._solver_thread.join(timeout=5)
    assert not app._solver_thread.is_alive()
    app.input_handler.update()
    assert app.active_solver_name == algorithm
    assert app._is_playing_solution
    replay = Game(app.game.board.clone())
    for action in app._active_solution:
        outcome, _, _ = replay.roll(action)
        assert outcome in ('SAFE', 'VICTORY')
    assert replay.board.evaluate_block_state(replay.block)[0] == 'VICTORY'
