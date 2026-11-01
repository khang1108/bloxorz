"""Automated unit and integration tests for Bloxorz 3D Animation & VFX Subsystem."""

import math
from bloxorz.config import get_config
from bloxorz.ui.theme import Palette, Motion
from bloxorz.core.constants import Direction, BlockOrientation
from bloxorz.core.block.normal import NormalBlockState
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.core.game import Game
from bloxorz.graphics.fx_manager import FXManager
from bloxorz.graphics.board_view import BoardView
from bloxorz.graphics.block_view import BlockView
from bloxorz.graphics.camera_ctrl import CameraController


def test_animation_config_defaults():
    """Verify AnimationConfig parameters conform to Bloxpath specifications."""
    cfg = get_config()
    assert hasattr(cfg, "animation")
    anim = cfg.animation
    assert anim.wave_enabled is True
    assert anim.wave_amplitude > 0.0
    assert anim.stage_intro_anim is True
    assert anim.tile_highlight_enabled is True
    assert anim.cushion_depth == 0.0
    assert anim.roll_squash_y == 1.0
    assert anim.ghost_trail_enabled is True
    assert anim.screen_shake_enabled is False


def test_palette_vfx_tokens():
    """Verify design system color tokens exist and are valid hex colors."""
    assert Palette.GHOST_TRAIL.hex_code == "#38BDF8"
    assert Palette.SHOCKWAVE_RING.hex_code == "#38BDF8"
    assert Palette.VICTORY_GOLD.hex_code == "#F59E0B"
    assert Palette.CRUMBLE_FRAGMENT.hex_code == "#E06D28"
    assert Palette.TELEPORT_ENERGY.hex_code == "#818CF8"


def test_fx_manager_pool_lifecycle():
    """Verify object pool allocation, activation, and clear_all lifecycle."""
    fx = FXManager.get_instance()
    assert fx is not None
    assert len(fx._ghosts) == FXManager.POOL_GHOSTS
    assert len(fx._rings) == FXManager.POOL_RINGS
    assert len(fx._particles) == FXManager.POOL_PARTICLES
    assert len(fx._ambient) == FXManager.POOL_AMBIENT

    # Reset all
    fx.clear_all()
    for g in fx._ghosts:
        assert g.active is False
        assert g.entity.enabled is False
    for r in fx._rings:
        assert r.active is False
        assert r.entity.enabled is False
    for p in fx._particles:
        assert p.active is False
        assert p.entity.enabled is False


def test_board_dual_sine_wave_computation():
    """Verify dual sine wave formula elevation bounds and periodicity."""
    bv = BoardView()
    cfg = get_config().animation

    for x in (-3.0, 0.0, 3.0):
        for z in (-3.0, 0.0, 3.0):
            for t in (0.0, 1.0, 2.5):
                bv._wave_time = t
                yw = bv.compute_wave_y(x, z)
                max_bound = cfg.wave_amplitude * 1.5
                assert abs(yw) <= max_bound
                assert isinstance(yw, float)


def test_board_tile_highlight():
    """Verify Bloxpath tile step highlight pulses normal tiles and preserves fragile tiles."""
    from bloxorz.core.constants import TileType
    from ursina import Entity, color
    bv = BoardView()
    normal_ent = Entity(color=color.hex(Palette.TILE_NORMAL.hex_code))
    fragile_ent = Entity(color=color.hex(Palette.TILE_FRAGILE.hex_code))
    bv.tile_entities[(0, 0)] = normal_ent
    bv.tile_entities[(1, 0)] = fragile_ent
    bv.tile_types[(0, 0)] = TileType.NORMAL
    bv.tile_types[(1, 0)] = TileType.FRAGILE

    bv.highlight_tiles([(0, 0), (1, 0)])

    # Normal tile receives highlight pulse
    assert normal_ent.color != color.hex(Palette.TILE_NORMAL.hex_code)
    # Fragile tile MUST strictly maintain its original vibrant orange color
    assert fragile_ent.color == color.hex(Palette.TILE_FRAGILE.hex_code)



def test_camera_serenity():
    """Verify camera shake is completely disabled for a 100% steady, serene view."""
    cam = CameraController()
    cam.shake_camera(intensity=0.15)
    # Under screen_shake_enabled = False, shake is strictly ignored
    assert cam._shake_intensity == 0.0
    assert cam._shake_offset == (0, 0, 0)


def test_block_view_ground_anchor():
    """Verify BlockView connects to BoardView and queries surface elevation."""
    bv = BoardView()
    block_view = BlockView()
    block_view.set_board_view(bv)

    surf_y = block_view._get_surface_y(0.0, 0.0)
    assert isinstance(surf_y, float)


def test_column_sea_lifecycle_and_wave():
    """Verify ColumnSea generates columns around board and animates harmonic waves."""
    from bloxorz.config import CONFIG
    from bloxorz.graphics.background_matrix import ColumnSea
    board = load_level_from_file('bloxorz/levels/stage_01.json')
    prev_state = getattr(CONFIG.animation, "column_sea_enabled", False)
    CONFIG.animation.column_sea_enabled = True
    try:
        sea = ColumnSea()
        sea.build_around_board(board, padding=3)

        assert len(sea.columns) > 0
        # Occupied board tiles must NOT have background columns
        occupied = set(board.base_tiles.keys())
        for col, _, px, pz in sea.columns:
            gx = int(round(px))
            gy = int(round(-pz))
            assert (gx, gy) not in occupied

        # Test wave update computation
        sea._time = 1.5
        sea.update()
        col0, base_h0, _, _ = sea.columns[0]
        assert isinstance(col0.y, float)

        sea.clear()
        assert len(sea.columns) == 0
    finally:
        CONFIG.animation.column_sea_enabled = prev_state


def test_block_view_animate_fall_cantilever_and_direct():
    """Verify BlockView.animate_fall obeys rigid-body physics: tilt direction down into void, tumble momentum."""
    board = load_level_from_file('bloxorz/levels/stage_01.json')
    block_view = BlockView()

    # 1. Cantilever fall: lying block with 1 supported tile at (0, 1) and 1 overhanging tile at (-1, 1)
    lying_cantilever = NormalBlockState(x=-1, y=1, orientation=BlockOrientation.LYING_X)
    block_view.sync_to_state(lying_cantilever)
    done_called = []
    block_view.animate_fall(board=board, direction=Direction.LEFT, on_complete=lambda: done_called.append(True))
    assert block_view._is_falling is True
    assert block_view._is_seesaw is True
    assert block_view._fall_mode == "CANTILEVER"
    # Overhang is at -X, so tilt_sign must be negative to tilt the overhanging side DOWN into the void
    assert block_view._tilt_sign == -1.0

    # 2. Direct tumble fall: standing block over void (0 supported tiles)
    standing_void = NormalBlockState(x=-5, y=-5, orientation=BlockOrientation.STANDING)
    block_view.sync_to_state(standing_void)
    block_view.animate_fall(board=board, direction=Direction.LEFT, on_complete=lambda: done_called.append(True))
    assert block_view._is_falling is True
    assert block_view._is_seesaw is False
    assert block_view._fall_mode == "TUMBLE"
    # Tumble rolling left: forward horizontal velocity is negative, angular velocity is negative (smooth continuation)
    assert block_view._fall_velocity_horiz.x < 0.0
    assert block_view._angular_velocity < 0.0


def test_landing_solidity_and_gentle_dust():
    """Verify rock-solid floor stability on impact and gentle dust particle emission upon landing."""
    bv = BoardView()
    # cushion_impact is a serene no-op ensuring a rock-solid floor without seismic deformation
    bv.cushion_impact(2.0, 2.0, intensity=1.0)
    assert not hasattr(bv, "_seismic_ripples")
    yw = bv.compute_wave_y(2.0, -2.0)
    assert isinstance(yw, float)

    # Verify BlockView emits gentle dust motes on landing
    fx = FXManager.get_instance()
    fx.clear_all()
    block_view = BlockView()
    block_view.set_board_view(bv)
    block_view._spawn_landing_dust([(1, 1)])

    active_dust = [p for p in fx._particles if p.active]
    assert len(active_dust) == 6
    ash_r_vals = {Palette.EMBER_ASH.r, Palette.EMBER_ASH_GLOW.r, Palette.EMBER_ASH_SPARK.r}
    for p in active_dust:
        assert any(abs(p.r - target_r) < 0.01 for target_r in ash_r_vals)


def test_sci_fi_teleport_recall_lifecycle():
    """Verify 4-phase sci-fi teleport & recall sequence initialization and cleanup."""
    from bloxorz.core.block.split import SplitBlockState, SingleBlock
    block_view = BlockView()

    standing = NormalBlockState(x=4, y=4, orientation=BlockOrientation.STANDING)
    split_state = SplitBlockState(
        b1=SingleBlock(10, 1),
        b2=SingleBlock(10, 7),
        active_index=0,
    )

    block_view.animate_teleport_split(standing, split_state)
    assert block_view._is_teleporting is True
    assert block_view._teleport_pad_src.visible is True
    assert block_view._teleport_ring_1.visible is True

    # Advance time through Phase 2 & 3
    from ursina import time as u_time
    u_time.dt = 0.35
    block_view.update()
    assert block_view.split_mesh_1 is not None

    # Complete teleportation
    u_time.dt = 0.80
    block_view.update()
    assert block_view._is_teleporting is False
    assert block_view._teleport_pad_src.visible is False
    assert block_view._teleport_beam_src.visible is False
    assert block_view._teleport_beam_dst1.visible is False


