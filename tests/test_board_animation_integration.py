"""Integration tests for board animations, visual feedback, and lifecycle teardown."""

import pytest
from ursina import Vec3, color, destroy, time, application

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


def _create_sample_board() -> Board:
    """Creates a sample multi-tile board with all interactive elements."""
    tiles = {
        (0, 0): TileType.NORMAL,
        (1, 0): TileType.FRAGILE,
        (2, 0): TileType.SWITCH_SOFT,
        (3, 0): TileType.SWITCH_HEAVY,
        (4, 0): TileType.TELEPORT,
        (5, 0): TileType.GOAL,
    }
    bridges = {
        "gold": BridgeGroup(
            group_id="gold",
            tiles=[(6, 0), (7, 0)],
            initially_open=False,
            is_open=False,
        )
    }
    return Board(
        tiles=tiles,
        goal_pos=(5, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
        bridges=bridges,
    )


def test_board_view_singleton_and_permanently_static_surface(game_app):
    """Verify BoardView singleton accessor and permanently static surface/wave APIs."""
    view = BoardView()
    assert BoardView.get_instance() is view
    assert view.get_surface_y(0.0, 0.0) == 0.0
    assert view.get_surface_y(5.0, -3.0) == 0.0

    # Permanently static: compute_wave_y must strictly return 0.0
    assert view.compute_wave_y(1.0, 2.0) == 0.0
    assert view.compute_wave_y(-3.0, 4.0) == 0.0

    # cushion_impact executes safely as a no-op on static floor
    view.cushion_impact(0.0, 0.0, intensity=1.0)
    destroy(view.root)


def test_board_geometry_is_settled_immediately_from_frame_zero(game_app, monkeypatch):
    """Verify board geometry is at settled height immediately on build without vertical displacement."""
    board = _create_sample_board()
    monkeypatch.setattr(CONFIG.animation, "stage_intro_anim", True, raising=False)

    view = BoardView()
    view.build(board)

    normal_slab = view.tile_entities[(0, 0)]
    fragile_slab = view.tile_entities[(1, 0)]
    target_normal_y = CONFIG.board.normal_slab_y
    target_fragile_y = CONFIG.board.fragile_slab_y

    # Immediately at settled height (no -3.6 displacement)
    assert normal_slab.y == pytest.approx(target_normal_y)
    assert fragile_slab.y == pytest.approx(target_fragile_y)

    # Batched crack mesh is at settled height immediately
    assert view.crack_entity is not None
    assert view.crack_entity.y == pytest.approx(0.0)

    view.clear()
    destroy(view.root)


def test_simultaneous_border_lift_entry_and_baseline_restoration(game_app, monkeypatch):
    """Verify borders simultaneously lift brightness on entry and restore exact baseline color after 150ms."""
    board = _create_sample_board()
    monkeypatch.setattr(CONFIG.animation, "stage_intro_anim", True, raising=False)

    view = BoardView()
    view.build(board)

    normal_border = view.get_tile_border((0, 0))
    fragile_border = view.get_tile_border((1, 0))
    assert normal_border is not None
    assert fragile_border is not None

    expected_normal_base = color.rgba(
        Palette.TILE_BORDER.r,
        Palette.TILE_BORDER.g,
        Palette.TILE_BORDER.b,
        0.98,
    )

    # Immediately on build, borders are in lifted state (brighter than baseline)
    assert normal_border.color.r > expected_normal_base.r or normal_border.color.g > expected_normal_base.g

    # Advance time past 150ms entry duration
    _step_time(0.16)

    # Both borders must restore to their exact baseline color and alpha
    assert normal_border.color == expected_normal_base
    expected_fragile_base = color.rgba(
        Palette.TILE_FRAGILE.r,
        Palette.TILE_FRAGILE.g,
        Palette.TILE_FRAGILE.b,
        0.98,
    )
    assert fragile_border.color == expected_fragile_base

    view.clear()
    destroy(view.root)


def test_landing_affects_only_ordinary_tile_border_and_never_recolors_slab_or_spawns_quad(game_app):
    """Verify landing pulses only ordinary tile borders for 120ms without filled quad or slab recolor."""
    board = _create_sample_board()
    view = BoardView()
    view.build(board)

    # Advance past 150ms intro lift so borders settle at baseline
    _step_time(0.16)

    normal_slab = view.tile_entities[(0, 0)]
    fragile_slab = view.tile_entities[(1, 0)]
    normal_border = view.get_tile_border((0, 0))
    fragile_border = view.get_tile_border((1, 0))

    base_normal_slab_color = Vec3(normal_slab.color.r, normal_slab.color.g, normal_slab.color.b)
    base_fragile_slab_color = Vec3(fragile_slab.color.r, fragile_slab.color.g, fragile_slab.color.b)
    base_normal_border_color = normal_border.color
    base_fragile_border_color = fragile_border.color

    # Trigger landing on normal cell (0, 0) and fragile cell (1, 0)
    view.animate_landing([(0, 0), (1, 0)])

    # 1. NO filled quad (tile_landing_flash) spawned
    flash_quads = [e for e in view.root.children if e.name == "tile_landing_flash"]
    assert len(flash_quads) == 0

    # 2. NO slab recoloring
    assert Vec3(normal_slab.color.r, normal_slab.color.g, normal_slab.color.b) == base_normal_slab_color
    assert Vec3(fragile_slab.color.r, fragile_slab.color.g, fragile_slab.color.b) == base_fragile_slab_color

    # 3. ONLY ordinary tile border pulses brighter
    assert normal_border.color != base_normal_border_color
    # Special fragile tile border does NOT pulse
    assert fragile_border.color == base_fragile_border_color

    # 4. Advance time past 120ms landing pulse duration
    _step_time(0.13)

    # 5. Restores to exact original baseline color and alpha
    assert normal_border.color == base_normal_border_color

    view.clear()
    destroy(view.root)


def test_repeat_landing_pulses_and_intro_overlap_restore_exact_baseline(game_app, monkeypatch):
    """Verify rapid repeated landing pulses and overlap during intro always restore true baseline color."""
    board = _create_sample_board()
    monkeypatch.setattr(CONFIG.animation, "stage_intro_anim", True, raising=False)

    view = BoardView()
    view.build(board)

    normal_border = view.get_tile_border((0, 0))
    expected_base = color.rgba(
        Palette.TILE_BORDER.r,
        Palette.TILE_BORDER.g,
        Palette.TILE_BORDER.b,
        0.98,
    )

    # Immediately trigger landing while 150ms intro lift is still active
    view.animate_landing([(0, 0)])
    # Rapid second landing pulse
    _step_time(0.04)
    view.animate_landing([(0, 0)])

    # Advance time to allow all pulses to expire
    _step_time(0.15)
    _step_time(0.15)

    # Border must cleanly return to true baseline without color drift
    assert normal_border.color == expected_base

    view.clear()
    destroy(view.root)


def test_clear_and_rebuild_cancels_active_border_pulses(game_app):
    """Verify clear() / rebuild invalidates pending border restore callbacks."""
    board = _create_sample_board()
    view = BoardView()
    view.build(board)

    view.animate_landing([(0, 0)])
    border_before = view.get_tile_border((0, 0))

    view.clear()
    assert len(view.root.children) == 0

    # Rebuild board
    view.build(board)
    _step_time(0.16)

    new_border = view.get_tile_border((0, 0))
    expected_base = color.rgba(
        Palette.TILE_BORDER.r,
        Palette.TILE_BORDER.g,
        Palette.TILE_BORDER.b,
        0.98,
    )
    assert new_border.color == expected_base
    assert border_before not in view.root.children

    view.clear()
    destroy(view.root)


def test_highlight_tiles_acts_as_compatibility_delegate(game_app):
    """Verify highlight_tiles delegates to animate_landing for compatibility."""
    board = _create_sample_board()
    view = BoardView()
    view.build(board)
    _step_time(0.16)

    normal_border = view.get_tile_border((0, 0))
    base_color = normal_border.color

    view.highlight_tiles([(0, 0)])
    assert normal_border.color != base_color

    _step_time(0.13)
    assert normal_border.color == base_color

    view.clear()
    destroy(view.root)


def test_landing_respects_tile_highlight_enabled_toggle(game_app, monkeypatch):
    """Verify animate_landing and highlight_tiles do nothing when tile_highlight_enabled is False."""
    board = _create_sample_board()
    monkeypatch.setattr(CONFIG.animation, "stage_intro_anim", False, raising=False)
    monkeypatch.setattr(CONFIG.animation, "tile_highlight_enabled", False, raising=False)

    view = BoardView()
    view.build(board)

    normal_border = view.get_tile_border((0, 0))
    assert normal_border is not None
    base_color = normal_border.color

    # Test animate_landing with a set of cells (Iterable[Tuple[int, int]])
    view.animate_landing({(0, 0)})
    assert normal_border.color == base_color
    assert len(normal_border.animations) == 0

    # Test compatibility delegate highlight_tiles with a set of cells
    view.highlight_tiles({(0, 0)})
    assert normal_border.color == base_color
    assert len(normal_border.animations) == 0

    view.clear()
    destroy(view.root)


def test_switch_press_animation(game_app):
    """Verify switch plate depresses to depressed endpoint and recovers to initial height."""
    board = _create_sample_board()
    view = BoardView()
    view.build(board)

    cfg = CONFIG.board
    plate = view.switch_entities[(2, 0)]
    orig_y = plate.y
    depressed_y = orig_y - cfg.switch_press_depth

    view.animate_switch_press(2, 0)
    # Step down animation
    _step_time(cfg.switch_press_down_time + 0.02)
    assert plate.y == pytest.approx(depressed_y, abs=0.01)

    # Step up recovery animation
    _step_time(cfg.switch_press_up_time + 0.06)
    assert plate.y == pytest.approx(orig_y, abs=0.01)

    view.clear()
    destroy(view.root)


def test_bridge_deployment_staggered_easing(game_app):
    """Verify bridge deployment animates open to open endpoint and close to closed endpoint."""
    board = _create_sample_board()
    view = BoardView()
    view.build(board)

    cfg = CONFIG.board
    b1 = view.bridge_entities[(6, 0)]
    b2 = view.bridge_entities[(7, 0)]
    assert not b1.visible
    assert not b2.visible

    # Open bridge
    board.bridges["gold"].open()
    view.update_bridges(board)
    assert b1.visible
    assert b2.visible

    # Advance time to allow both staggered bridge deployments to reach full height
    _step_time(0.1, steps=8)
    assert b1.y == pytest.approx(cfg.bridge_open_y, abs=0.01)
    assert b2.y == pytest.approx(cfg.bridge_open_y, abs=0.01)

    # Close bridge
    board.bridges["gold"].close()
    view.update_bridges(board)

    # Advance time to allow sink animation to complete
    _step_time(0.1, steps=8)
    assert b1.y == pytest.approx(cfg.bridge_closed_y, abs=0.01)
    assert b2.y == pytest.approx(cfg.bridge_closed_y, abs=0.01)
    assert not b1.visible
    assert not b2.visible

    view.clear()
    destroy(view.root)


def test_fragile_crumble_lifecycle_and_callback(game_app):
    """Verify fragile crumble executes shake, fall, and fires on_complete callback upon finish."""
    board = _create_sample_board()
    view = BoardView()
    view.build(board)

    completed = []
    view.animate_fragile_crumble(1, 0, on_complete=lambda: completed.append(True))
    assert (1, 0) in view._crumbling_tiles
    assert len(completed) == 0

    # Advance time through shake (0.12s) and fall (0.85s)
    _step_time(0.1, steps=12)
    assert completed == [True]

    # Test invalid cell triggers on_complete immediately
    invalid_done = []
    view.animate_fragile_crumble(99, 99, on_complete=lambda: invalid_done.append(True))
    assert invalid_done == [True]

    view.clear()
    destroy(view.root)


def test_clear_and_rebuild_cancels_stale_callbacks(game_app):
    """Verify clear() / rebuild invalidates pending crumble callbacks even after time advances."""
    board = _create_sample_board()
    view = BoardView()
    view.build(board)

    stale_done = []
    view.animate_fragile_crumble(1, 0, on_complete=lambda: stale_done.append(True))

    gen_before = view._build_generation
    view.clear()
    assert view._build_generation > gen_before
    assert len(view.tile_entities) == 0
    assert len(view._crumbling_tiles) == 0

    # Rebuilding starts a fresh generation
    view.build(board)
    assert (1, 0) in view.tile_entities
    assert (1, 0) not in view._crumbling_tiles

    # Advance time through what would have been the crumble duration
    _step_time(0.1, steps=15)

    # Stale callback must NEVER fire even after time has elapsed
    assert len(stale_done) == 0

    view.clear()
    destroy(view.root)


def test_fragile_crumble_detaches_cell_cracks_and_preserves_remaining_cells(game_app):
    """Regression test: crumbling a fragile cell detaches its crack geometry and preserves other cells."""
    board = Board(
        tiles={
            (0, 0): TileType.NORMAL,
            (1, 0): TileType.FRAGILE,
            (2, 0): TileType.FRAGILE,
            (3, 0): TileType.GOAL,
        },
        goal_pos=(3, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view = BoardView()
    view.build(board)

    # Initially, both fragile cells are batched into a single mesh (2 * 6 * 4 = 48 vertices)
    assert view.crack_entity is not None
    assert len(view.crack_entity.model.vertices) == 48

    # Crumble cell (1, 0)
    done_1 = []
    view.animate_fragile_crumble(1, 0, on_complete=lambda: done_1.append(True))

    # Cell (1, 0) crack geometry detached from the batched mesh
    # Remaining intact cell (2, 0) retains its 24 vertices in the batched mesh
    assert view.crack_entity is not None
    assert len(view.crack_entity.model.vertices) == 24
    assert (2, 0) in view._fragile_cracks
    assert (1, 0) not in view._fragile_cracks

    # Cell (1, 0) has a detached crack entity among the falling parts
    detached = next(
        (e for e in view.root.children if e.name == "detached_fragile_crack"),
        None,
    )
    assert detached is not None
    assert len(detached.model.vertices) == 24

    # Advance time to complete crumble for cell (1, 0)
    _step_time(0.1, steps=12)
    assert done_1 == [True]

    # Cell (2, 0) cracks are still intact on the batched mesh!
    assert view.crack_entity is not None
    assert len(view.crack_entity.model.vertices) == 24

    # Now crumble the remaining fragile cell (2, 0)
    done_2 = []
    view.animate_fragile_crumble(2, 0, on_complete=lambda: done_2.append(True))
    # When no fragile cells remain, the batched crack entity is cleanly destroyed
    assert view.crack_entity is None
    assert len(view._fragile_cracks) == 0

    _step_time(0.1, steps=12)
    assert done_2 == [True]

    view.clear()
    destroy(view.root)
