"""Integration tests for the cyberpunk machined platform board visual redesign."""

import pytest
from ursina import Vec3, application, destroy, time

from bloxorz.config import CONFIG
from bloxorz.core.block.normal import NormalBlockState
from bloxorz.core.board import Board, BridgeGroup
from bloxorz.core.constants import BlockOrientation, TileType
from bloxorz.graphics.board_view import BoardView
from bloxorz.ui.theme import Palette


def _step_time(dt: float = 0.1, steps: int = 1) -> None:
    """Advances Ursina engine time and steps all active sequences and tweens."""
    for _ in range(steps):
        time.dt = dt
        for seq in list(application.sequences):
            seq.update()


def test_cyberpunk_palette_slate_normal_tile():
    """Verify Palette.TILE_NORMAL uses slate #293647 for brighter machined titanium deck look."""
    assert Palette.TILE_NORMAL.hex_code.upper() == "#293647"
    # Verify RGB components match slate #293647
    assert Palette.TILE_NORMAL.r == pytest.approx(0x29 / 255.0, abs=0.01)
    assert Palette.TILE_NORMAL.g == pytest.approx(0x36 / 255.0, abs=0.01)
    assert Palette.TILE_NORMAL.b == pytest.approx(0x47 / 255.0, abs=0.01)


def test_normal_tile_uses_beveled_box_and_deck_panel(game_app):
    """Verify normal tile slab uses beveled box and top surface uses deck panel mesh."""
    board = Board(
        tiles={(0, 0): TileType.NORMAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view = BoardView()
    view.build(board)

    slab = view.tile_entities[(0, 0)]
    assert slab.model is not None
    # Model name should indicate beveled box mesh (not generic unit 'cube')
    assert slab.model.name != "cube"

    surf = next(part for part in view.tile_parts[(0, 0)] if part.name == "tile_gradient_surface")
    assert surf.model is not None
    assert surf.model.name != "quad"

    view.clear()
    destroy(view.root)


def test_edge_aware_borders_distinguish_exposed_from_interior(game_app):
    """Verify neighbor-aware border mesh has exposed edges brighter and interior edges subdued."""
    # Board with two adjacent normal tiles at (0, 0) and (1, 0)
    # For (0, 0):
    # x_pos (1, 0) is adjacent (interior)
    # x_neg, z_neg, z_pos are exposed to void
    board = Board(
        tiles={(0, 0): TileType.NORMAL, (1, 0): TileType.NORMAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view = BoardView()
    view.build(board)

    border_0 = view.get_tile_border((0, 0))
    assert border_0 is not None
    mesh_0 = border_0.model
    assert mesh_0 is not None

    # Mesh colors must contain both exposed (bright, multipliers near 1.0)
    # and interior/subdued (dim, multipliers approx RGB 0.16, alpha 0.40)
    color_tuples = [tuple(c) for c in mesh_0.colors]
    has_exposed = any(c[0] > 0.8 and c[1] > 0.8 and c[2] > 0.8 for c in color_tuples)
    has_subdued = any(c[0] < 0.3 and c[1] < 0.3 and c[2] < 0.3 for c in color_tuples)
    assert has_exposed, "Expected exposed edges with bright multipliers"
    assert has_subdued, "Expected interior edges with subdued multipliers"

    view.clear()
    destroy(view.root)


def test_bridge_state_change_refreshes_neighbor_edge_hierarchy(game_app):
    """Verify when a bridge opens/closes, neighboring normal tile border updates edge exposure."""
    # Normal tile at (0, 0), bridge at (1, 0)
    board = Board(
        tiles={(0, 0): TileType.NORMAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
        bridges={
            "b1": BridgeGroup(
                group_id="b1",
                tiles=[(1, 0)],
                initially_open=False,
                is_open=False,
            )
        },
    )
    view = BoardView()
    view.build(board)

    border_0 = view.get_tile_border((0, 0))
    # When bridge is closed, (1, 0) is closed/void, so all 4 edges of (0, 0) are exposed
    closed_colors = [tuple(c) for c in border_0.model.colors]
    assert all(c[0] > 0.8 for c in closed_colors), "Closed bridge must leave neighbor edge exposed"

    # Open bridge
    board.bridges["b1"].open()
    board._sync_bridge_tiles(board.bridges["b1"])
    view.update_bridges(board)

    # After bridge opens, border_0 edge toward (1, 0) (x_pos) must become subdued
    opened_colors = [tuple(c) for c in border_0.model.colors]
    has_subdued_now = any(c[0] < 0.3 for c in opened_colors)
    assert has_subdued_now, "Opened bridge must make adjacent neighbor edge subdued"

    # Close bridge again
    board.bridges["b1"].close()
    board._sync_bridge_tiles(board.bridges["b1"])
    view.update_bridges(board)

    reclosed_colors = [tuple(c) for c in border_0.model.colors]
    assert all(c[0] > 0.8 for c in reclosed_colors), "Re-closing bridge must return edge to exposed"

    view.clear()
    destroy(view.root)


def test_goal_well_and_halo_are_genuinely_hollow(game_app):
    """Verify goal halo and well are genuinely hollow with aperture > block width and no center cover."""
    board = Board(
        tiles={(0, 0): TileType.GOAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view = BoardView()
    view.build(board)

    goal_well = view.goal_entity
    assert goal_well is not None
    assert goal_well.model is not None
    assert goal_well.model.name != "cube"

    halo = next(
        part for part in view.tile_parts[(0, 0)]
        if part.model is not None and part is not goal_well
        and abs(part.y - CONFIG.board.goal_rim_y) < 1e-6
    )
    assert halo.model is not None
    assert halo.model.name != "cube"

    half_block_with_clearance = CONFIG.block.unit_scale_1 / 2 + 0.01
    aperture_points = [
        (0.0, 0.0),
        (half_block_with_clearance, 0.0),
        (-half_block_with_clearance, 0.0),
        (0.0, half_block_with_clearance),
        (0.0, -half_block_with_clearance),
        (half_block_with_clearance, half_block_with_clearance),
    ]

    def projected_triangle_contains(point, a, b, c):
        def signed_area(p, q, r):
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        if abs(signed_area(a, b, c)) < 1e-8:
            return False
        signs = [signed_area(a, b, point), signed_area(b, c, point), signed_area(c, a, point)]
        return min(signs) >= -1e-8 or max(signs) <= 1e-8

    for part in (halo, goal_well):
        vertices = [view.root.get_relative_point(part, Vec3(vertex)) for vertex in part.model.vertices]
        for triangle in part.model.triangles:
            points = [(vertices[index].x, vertices[index].z) for index in triangle]
            for pt in aperture_points:
                assert not projected_triangle_contains(pt, *points), f"Aperture point {pt} is covered by {part.name}"

    view.clear()
    destroy(view.root)


def test_update_bridges_never_mutates_core_board_or_current_tiles(game_app):
    """Regression: graphics update_bridges must never mutate core Board or current_tiles."""
    board = Board(
        tiles={(0, 0): TileType.NORMAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
        bridges={
            "b1": BridgeGroup(
                group_id="b1",
                tiles=[(1, 0)],
                initially_open=False,
                is_open=False,
            )
        },
    )
    view = BoardView()
    view.build(board)

    # Snapshot current_tiles and bridge state
    tiles_snapshot = dict(board.current_tiles)
    bridge_states_snapshot = [(b.group_id, b.is_open, list(b.tiles)) for b in board.bridges.values()]

    # Calling update_bridges must NOT mutate current_tiles or bridge states
    view.update_bridges(board)

    assert board.current_tiles == tiles_snapshot
    assert [(b.group_id, b.is_open, list(b.tiles)) for b in board.bridges.values()] == bridge_states_snapshot

    view.clear()
    destroy(view.root)


def test_update_bridges_unchanged_state_preserves_model_identity(game_app):
    """Regression: calling update_bridges with unchanged state must skip mesh rebuild."""
    board = Board(
        tiles={(0, 0): TileType.NORMAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
        bridges={
            "b1": BridgeGroup(
                group_id="b1",
                tiles=[(1, 0)],
                initially_open=False,
                is_open=False,
            )
        },
    )
    view = BoardView()
    view.build(board)

    border_0 = view.get_tile_border((0, 0))
    assert border_0 is not None
    original_model = border_0.model

    # Call update_bridges with identical bridge state
    view.update_bridges(board)
    assert border_0.model is original_model, "Model instance must not be recreated when bridge state is unchanged"

    view.clear()
    destroy(view.root)


def test_bridge_open_close_preserves_active_pulse_color_and_switch_width_factor(game_app):
    """Regression: bridge state transition preserves Entity.color during active pulse and switch width factor."""
    board = Board(
        tiles={(0, 0): TileType.NORMAL, (2, 0): TileType.SWITCH_SOFT},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
        bridges={
            "b1": BridgeGroup(
                group_id="b1",
                tiles=[(1, 0)],
                initially_open=False,
                is_open=False,
            )
        },
    )
    view = BoardView()
    view.build(board)

    # Verify switch retains width factor 0.065
    assert view._border_width_factors.get((2, 0)) == 0.065

    # Trigger landing pulse on normal cell (0, 0)
    view.animate_landing([(0, 0)])
    border_0 = view.get_tile_border((0, 0))
    pulsed_color = border_0.color

    # Open bridge while pulse is active
    board.bridges["b1"].open()
    board._sync_bridge_tiles(board.bridges["b1"])
    view.update_bridges(board)

    # Entity.color must be preserved despite mesh rebuild
    assert border_0.color == pulsed_color

    # Colors on new model must include subdued interior edge facing opened bridge
    opened_colors = [tuple(c) for c in border_0.model.colors]
    assert any(c[0] < 0.3 for c in opened_colors)

    view.clear()
    destroy(view.root)


def test_goal_aperture_clamping_for_wide_blocks(game_app, monkeypatch):
    """Regression: goal aperture ratio must safely clamp strictly below 1.0 even with wide 0.94 block."""
    monkeypatch.setattr(CONFIG.block, "unit_scale_1", 0.94, raising=False)
    board = Board(
        tiles={(0, 0): TileType.GOAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view = BoardView()
    # Building board with 0.94 block width must not raise ValueError in hollow_box_mesh
    view.build(board)
    assert view.goal_entity is not None
    assert view.goal_entity.model is not None

    view.clear()
    destroy(view.root)
