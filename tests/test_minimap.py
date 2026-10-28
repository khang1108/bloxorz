"""Verify live map geometry and state changes with real boards and UI entities."""

import importlib

import pytest
from ursina import destroy, scene, window

from bloxorz.core.block import BlockState, SplitBlockState
from bloxorz.core.constants import BlockOrientation
from bloxorz.core.level_loader import parse_level_data


def make_map():
    module = importlib.import_module('bloxorz.ui.minimap')
    return module.MiniMap()


def board_fixture():
    return parse_level_data({
        'layout': ['11B2', 'S311'],
        'spawn': {'x': 0, 'y': 0},
        'bridges': [{'id': 'b1', 'tiles': [[2, 0]], 'initially_open': False}],
        'switches': [{'x': 0, 'y': 1, 'targets': ['b1']}],
    })


def test_projection_keeps_square_cells_and_board_north_at_the_top(engine):
    minimap = make_map()
    board = board_fixture()
    minimap.sync(board, board.spawn_state)
    left = minimap.project(0, 0)
    right = minimap.project(1, 0)
    below = minimap.project(0, 1)
    assert right[0] - left[0] == pytest.approx(left[1] - below[1])
    assert right[0] > left[0]
    assert below[1] < left[1]
    assert len(minimap.tile_entities) == 8
    destroy(minimap.root)


def test_bridge_colors_follow_switch_and_reset_without_rebuilding(engine):
    minimap = make_map()
    board = board_fixture()
    minimap.sync(board, board.spawn_state)
    bridge = minimap.tile_entities[(2, 0)]
    closed_color = tuple(bridge.color)
    board.trigger_switches(BlockState(0, 1, BlockOrientation.STANDING))
    minimap.sync(board, board.spawn_state)
    assert minimap.tile_entities[(2, 0)] is bridge
    assert tuple(bridge.color) != closed_color
    board.reset()
    minimap.sync(board, board.spawn_state)
    assert tuple(bridge.color) == pytest.approx(closed_color)
    destroy(minimap.root)


def test_split_markers_distinguish_controlled_cube_and_switch_focus(engine):
    minimap = make_map()
    board = board_fixture()
    block = SplitBlockState.from_targets((0, 0), (3, 1))
    minimap.sync(board, block)
    first, second = minimap.block_markers
    assert first.enabled and second.enabled
    assert tuple(first.color) != tuple(second.color)
    first_color = tuple(first.color)
    second_color = tuple(second.color)
    first_position = tuple(first.position)
    minimap.sync(board, block.switch_active())
    assert tuple(first.color) == pytest.approx(second_color)
    assert tuple(second.color) == pytest.approx(first_color)
    assert tuple(first.position) == first_position
    destroy(minimap.root)


def test_lying_block_is_one_continuous_shape_centered_over_its_cells(engine):
    minimap = make_map()
    board = board_fixture()
    minimap.sync(board, board.spawn_state)
    assert [marker.enabled for marker in minimap.block_markers] == [True, False]
    minimap.sync(board, BlockState(0, 0, BlockOrientation.LYING_X))
    assert [marker.enabled for marker in minimap.block_markers] == [True, False]
    marker = minimap.block_markers[0]
    assert (marker.x, marker.y) == pytest.approx(minimap.project(.5, 0))
    assert marker.body.scale_x > marker.body.scale_y * 1.5
    minimap.sync(board, BlockState(0, 0, BlockOrientation.LYING_Y))
    assert (marker.x, marker.y) == pytest.approx(minimap.project(0, .5))
    assert marker.body.scale_y > marker.body.scale_x * 1.5
    destroy(minimap.root)


def test_movement_and_shape_changes_reuse_existing_marker_geometry(engine):
    minimap = make_map()
    board = board_fixture()
    minimap.sync(board, board.spawn_state)
    entities = len(scene.entities)
    standing_body = minimap.block_markers[0].body
    for _ in range(20):
        minimap.sync(board, BlockState(0, 0, BlockOrientation.LYING_X))
        minimap.sync(board, BlockState(0, 0, BlockOrientation.LYING_Y))
        minimap.sync(board, SplitBlockState.from_targets((0, 0), (3, 1)))
        minimap.sync(board, board.spawn_state)
        minimap.root.update()
    assert len(scene.entities) == entities
    assert minimap.block_markers[0].body is standing_body
    destroy(minimap.root)


def test_repeated_sync_reuses_tiles_and_stage_change_replaces_old_geometry(engine):
    minimap = make_map()
    board = board_fixture()
    minimap.sync(board, board.spawn_state)
    originals = dict(minimap.tile_entities)
    markers = list(minimap.block_markers)
    for _ in range(100):
        minimap.sync(board, board.spawn_state)
    assert all(minimap.tile_entities[key] is value for key, value in originals.items())
    assert minimap.block_markers == markers
    other = parse_level_data({'layout': ['112'], 'spawn': {'x': 0, 'y': 0}})
    minimap.sync(other, other.spawn_state)
    assert set(minimap.tile_entities) == {(0, 0), (1, 0), (2, 0)}
    assert all(tile.isEmpty() for tile in originals.values())
    destroy(minimap.root)


def test_hiding_map_disables_its_entire_panel(engine):
    minimap = make_map()
    minimap.set_visible(False)
    assert not minimap.root.enabled
    minimap.set_visible(True)
    assert minimap.root.enabled
    destroy(minimap.root)


@pytest.mark.parametrize('ratio', [16 / 9, 4 / 3])
def test_panels_stay_inside_viewport_and_above_keyboard_hints(engine, monkeypatch, ratio):
    from bloxorz.ui.solver_widget import SolverWidget
    from bloxorz.ui.constants import SolverWidgetConstants

    monkeypatch.setattr(type(window), 'aspect_ratio', property(lambda self: ratio))
    minimap = make_map()
    controls = SolverWidget()
    minimap.root.update()
    controls.root.update()
    for root, width, height in (
        (minimap.root, minimap.WIDTH, minimap.HEIGHT),
        (controls.root, *SolverWidgetConstants.PANEL_SIZE),
    ):
        assert root.x - width / 2 >= -ratio / 2
        assert root.x + width / 2 <= ratio / 2
        assert root.y - height / 2 > -.45
    assert controls.root.x == pytest.approx(minimap.root.x)
    assert controls.root.x > 0
    assert controls.root.y - SolverWidgetConstants.PANEL_SIZE[1] / 2 > minimap.root.y + minimap.HEIGHT / 2 + .015
    destroy(minimap.root)
    destroy(controls.root)
