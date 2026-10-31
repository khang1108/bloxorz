"""Comprehensive headless tests for Bloxorz BlockView visual appearance and animation lifecycles.

Verifies:
1. Visual Appearance: Modular titanium textured dual subcubes (Bao cyber skin) with
   1:1 UV mapping, no container double-scaling, bright white active split cube and
   dimmed slate titanium passive cube.
2. Animated Pose Endpoints: Accurate start, intermediate, and terminal poses for rolls,
   see-saw cantilever tipping, fragile vertical plunge, and goal vortex sink.
3. Callback Lifecycle: Guarantees that roll, fall, victory, and two-phase teleport
   callbacks fire exactly once without stuck animation states or stale ghosts.
4. Landing Ownership: BlockView does not call board.highlight_tiles; landing feedback
   is owned exclusively by Main and BoardView.
"""

from unittest.mock import MagicMock
import pytest
from ursina import Vec3, destroy, time as u_time

from bloxorz.config import CONFIG
from bloxorz.core.constants import Direction, BlockOrientation
from bloxorz.core.block.normal import NormalBlockState
from bloxorz.core.block.split import SplitBlockState, SingleBlock
from bloxorz.graphics.block_view import BlockView
from bloxorz.graphics.fx_manager import FXManager
from bloxorz.core.level_loader import load_level_from_file


def test_visual_appearance_modular_titanium(engine):
    """Verify BlockView restores Bao's dual modular titanium subcubes without container double-scaling."""
    view = BlockView()
    try:
        # 1. Container entity contract (mesh has no direct model; subcubes provide the geometry)
        assert view.mesh.model is None or not view.mesh.model
        assert hasattr(view, "mesh_cube_1") and view.mesh_cube_1 is not None
        assert hasattr(view, "mesh_cube_2") and view.mesh_cube_2 is not None

        # 2. Both subcubes are unit cubes with titanium texture
        assert view.mesh_cube_1.model is not None and view.mesh_cube_1.model.name == "cube"
        assert view.mesh_cube_2.model is not None and view.mesh_cube_2.model.name == "cube"

        u1 = CONFIG.block.unit_scale_1
        assert tuple(view.mesh_cube_1.scale) == pytest.approx((u1, u1, u1))
        assert tuple(view.mesh_cube_2.scale) == pytest.approx((u1, u1, u1))

        assert view.mesh_cube_1.texture and "cyber_titanium" in str(view.mesh_cube_1.texture)
        assert view.mesh_cube_2.texture and "cyber_titanium" in str(view.mesh_cube_2.texture)

        # 3. Orientation layouts: Standing (1x1x2) - subcubes stacked vertically along Y
        standing = NormalBlockState(x=3, y=3, orientation=BlockOrientation.STANDING)
        view.sync_to_state(standing)
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))
        assert tuple(view.mesh_cube_1.position) == pytest.approx((0.0, -0.5, 0.0))
        assert tuple(view.mesh_cube_2.position) == pytest.approx((0.0, 0.5, 0.0))
        assert tuple(view.pivot.position) == pytest.approx((3.0, 1.0, -3.0))

        # 4. Orientation layouts: Lying X (2x1x1) - subcubes along X axis
        lying_x = NormalBlockState(x=3, y=3, orientation=BlockOrientation.LYING_X)
        view.sync_to_state(lying_x)
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))
        assert tuple(view.mesh_cube_1.position) == pytest.approx((-0.5, 0.0, 0.0))
        assert tuple(view.mesh_cube_2.position) == pytest.approx((0.5, 0.0, 0.0))
        assert tuple(view.pivot.position) == pytest.approx((3.5, 0.5, -3.0))

        # 5. Orientation layouts: Lying Y (1x2x1) - subcubes along Z axis
        lying_y = NormalBlockState(x=3, y=3, orientation=BlockOrientation.LYING_Y)
        view.sync_to_state(lying_y)
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))
        assert tuple(view.mesh_cube_1.position) == pytest.approx((0.0, 0.0, -0.5))
        assert tuple(view.mesh_cube_2.position) == pytest.approx((0.0, 0.0, 0.5))
        assert tuple(view.pivot.position) == pytest.approx((3.0, 0.5, -3.5))
    finally:
        destroy(view)


def test_visual_appearance_split_cubes(engine):
    """Verify split cubes use titanium texture, 1x1x1 scale, bright white active and dimmed slate passive."""
    view = BlockView()
    try:
        u1 = CONFIG.block.unit_scale_1

        # Check split cube models and titanium texture
        assert view.split_mesh_1.model is not None and view.split_mesh_1.model.name == "cube"
        assert view.split_mesh_2.model is not None and view.split_mesh_2.model.name == "cube"
        assert view.split_mesh_1.texture and "cyber_titanium" in str(view.split_mesh_1.texture)
        assert view.split_mesh_2.texture and "cyber_titanium" in str(view.split_mesh_2.texture)

        # Case A: active_index == 0
        state_0 = SplitBlockState(b1=SingleBlock(2, 2), b2=SingleBlock(6, 6), active_index=0)
        view.sync_to_state(state_0)
        assert view.split_mesh_1.visible is True
        assert view.split_mesh_2.visible is True
        assert tuple(view.split_mesh_1.scale) == pytest.approx((u1, u1, u1))
        assert tuple(view.split_mesh_2.scale) == pytest.approx((u1, u1, u1))

        # Active is bright white titanium (1, 1, 1), passive is dimmed slate titanium (~0.48, ~0.54, ~0.62)
        assert view.split_mesh_1.color.r >= 0.95
        assert view.split_mesh_1.color.g >= 0.95
        assert view.split_mesh_1.color.b >= 0.95
        assert tuple(view.split_mesh_2.color)[:3] == pytest.approx((0.48, 0.54, 0.62), abs=0.03)

        # Case B: active_index == 1
        state_1 = SplitBlockState(b1=SingleBlock(2, 2), b2=SingleBlock(6, 6), active_index=1)
        view.sync_to_state(state_1)
        assert tuple(view.split_mesh_1.color)[:3] == pytest.approx((0.48, 0.54, 0.62), abs=0.03)
        assert view.split_mesh_2.color.r >= 0.95
        assert view.split_mesh_2.color.g >= 0.95
        assert view.split_mesh_2.color.b >= 0.95
    finally:
        destroy(view)


def test_container_scale_preservation_and_no_double_scaling(engine):
    """Verify container view.mesh.scale remains (1, 1, 1) through normal poses, falls, and reset cycles."""
    board = load_level_from_file('bloxorz/levels/stage_01.json')
    view = BlockView()
    try:
        # Upright and lying states keep container scale (1, 1, 1)
        standing = NormalBlockState(x=2, y=2, orientation=BlockOrientation.STANDING)
        view.sync_to_state(standing)
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))

        lying_x = NormalBlockState(x=2, y=2, orientation=BlockOrientation.LYING_X)
        view.sync_to_state(lying_x)
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))

        # Roll initiation does not double-scale container
        next_standing = NormalBlockState(x=4, y=2, orientation=BlockOrientation.STANDING)
        view.roll_animated(lying_x, next_standing, Direction.RIGHT)
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))
        u_time.dt = CONFIG.motion.roll_duration * 1.1
        view.update()
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))

        # Cantilever see-saw fall keeps container scale (1, 1, 1)
        cantilever_state = NormalBlockState(x=-1, y=1, orientation=BlockOrientation.LYING_X)
        view.sync_to_state(cantilever_state)
        view.animate_fall(board=board, direction=Direction.LEFT)
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))

        # Victory sink shrinks container, but reset cleanly restores (1, 1, 1)
        view.sync_to_state(standing)
        view.animate_victory()
        u_time.dt = 1.0
        view.update()
        assert view.mesh.scale.x < 1.0  # shrinking during vortex
        view.sync_to_state(standing)
        assert tuple(view.mesh.scale) == pytest.approx((1.0, 1.0, 1.0))
    finally:
        destroy(view)


def test_no_highlight_tiles_called_from_block_view(engine):
    """Verify BlockView does not call board.highlight_tiles; landing feedback is owned by Main/BoardView."""
    view = BlockView()
    try:
        mock_board_view = MagicMock()
        mock_board_view.get_surface_y.return_value = 0.0
        mock_board = MagicMock()
        mock_board.is_tile_walkable.return_value = True
        mock_board.get_tile.return_value = "o"

        view.board_view = mock_board_view

        # 1. Normal block roll completion
        s1 = NormalBlockState(x=2, y=2, orientation=BlockOrientation.STANDING)
        s2 = NormalBlockState(x=3, y=2, orientation=BlockOrientation.LYING_X)
        view.sync_to_state(s1)
        view.roll_animated(s1, s2, Direction.RIGHT, board=mock_board)
        u_time.dt = CONFIG.motion.roll_duration * 1.1
        view.update()
        assert not view.is_animating
        assert mock_board_view.highlight_tiles.call_count == 0

        # 2. Split cube roll completion
        split_prev = SplitBlockState(b1=SingleBlock(2, 2), b2=SingleBlock(5, 2), active_index=0)
        split_next = SplitBlockState(b1=SingleBlock(3, 2), b2=SingleBlock(5, 2), active_index=0)
        view.sync_to_state(split_prev)
        view.roll_animated(split_prev, split_next, Direction.RIGHT, board=mock_board)
        u_time.dt = CONFIG.motion.roll_duration * 1.1
        view.update()
        assert not view.is_animating
        assert mock_board_view.highlight_tiles.call_count == 0
    finally:
        destroy(view)


def test_roll_animation_pose_endpoints_and_callback(engine):
    """Verify roll animation progresses to exact terminal pose and fires callback exactly once."""
    view = BlockView()
    try:
        start_state = NormalBlockState(x=2, y=2, orientation=BlockOrientation.STANDING)
        next_state = NormalBlockState(x=3, y=2, orientation=BlockOrientation.LYING_X)
        view.sync_to_state(start_state)

        callbacks = []
        view.roll_animated(
            start_state,
            next_state,
            Direction.RIGHT,
            on_complete=lambda: callbacks.append("roll_done"),
        )

        assert view.is_animating is True
        assert view._is_rolling is True
        assert view._roll_progress == 0.0

        # Step time through 50% of roll duration
        dur = CONFIG.motion.roll_duration
        u_time.dt = dur * 0.50
        view.update()
        assert 0.45 <= view._roll_progress <= 0.55
        assert len(callbacks) == 0

        # Step time to complete roll
        u_time.dt = dur * 0.60
        view.update()
        assert view._is_rolling is False
        assert view.is_animating is False
        assert len(callbacks) == 1
        assert callbacks[0] == "roll_done"

        # Verify terminal pose endpoint
        assert tuple(view.pivot.position) == pytest.approx((3.5, 0.5, -2.0))
        assert tuple(view.pivot.rotation) == pytest.approx((0.0, 0.0, 0.0))
    finally:
        destroy(view)


def test_split_cube_roll_and_merge_lifecycle(engine):
    """Verify single 1x1x1 cube edge-pivot roll and merging sequence."""
    view = BlockView()
    try:
        # Active cube at (2, 2), passive at (5, 2)
        split_prev = SplitBlockState(b1=SingleBlock(2, 2), b2=SingleBlock(5, 2), active_index=0)
        split_next = SplitBlockState(b1=SingleBlock(3, 2), b2=SingleBlock(5, 2), active_index=0)
        view.sync_to_state(split_prev)

        cube_callbacks = []
        view.roll_animated(
            split_prev,
            split_next,
            Direction.RIGHT,
            on_complete=lambda: cube_callbacks.append("cube_done"),
        )
        assert view.is_animating is True
        assert view._is_cube_rolling is True

        # Advance through roll
        u_time.dt = CONFIG.motion.roll_duration * 1.1
        view.update()
        assert view._is_cube_rolling is False
        assert view.is_animating is False
        assert len(cube_callbacks) == 1

        # Test merge into standing block at (4, 2)
        standing_merged = NormalBlockState(x=4, y=2, orientation=BlockOrientation.STANDING)
        split_merge_prev = SplitBlockState(b1=SingleBlock(3, 2), b2=SingleBlock(4, 2), active_index=0)
        merge_callbacks = []
        view.roll_animated(
            split_merge_prev,
            standing_merged,
            Direction.RIGHT,
            on_complete=lambda: merge_callbacks.append("merge_done"),
        )
        assert view.is_animating is True

        u_time.dt = CONFIG.motion.roll_duration * 1.1
        view.update()
        assert view.is_animating is False
        assert len(merge_callbacks) == 1
        assert view.split_mesh_1.visible is False
        assert view.split_mesh_2.visible is False
        assert view.mesh.visible is True
    finally:
        destroy(view)


def test_teleport_two_phase_flight_and_callback_exactly_once(engine):
    """Verify teleport split executes two-phase sequence and triggers callback exactly once."""
    view = BlockView()
    try:
        standing = NormalBlockState(x=4, y=4, orientation=BlockOrientation.STANDING)
        split_dst = SplitBlockState(b1=SingleBlock(8, 2), b2=SingleBlock(8, 6), active_index=0)

        tp_callbacks = []
        view.animate_teleport_split(
            standing,
            split_dst,
            on_complete=lambda: tp_callbacks.append("teleport_done"),
        )

        assert view.is_animating is True
        assert view._is_teleporting is True
        assert view._teleport_pad_src.visible is True
        assert view._teleport_ring_1.visible is True

        # Phase 1: Advance to 20% duration (plunge into source event horizon)
        dur = view._teleport_duration
        u_time.dt = dur * 0.20
        view.update()
        assert view._is_teleporting is True
        assert view.mesh.visible is True
        assert view.split_mesh_1.visible is False
        assert len(tp_callbacks) == 0

        # Phase 2: Advance past source cutoff (split cubes launch into aerial flight)
        u_time.dt = dur * 0.35
        view.update()
        assert view._is_teleporting is True
        assert view.mesh.visible is False
        assert view.split_mesh_1.visible is True
        assert view.split_mesh_2.visible is True
        assert len(tp_callbacks) == 0

        # Final Touchdown: Advance past completion
        u_time.dt = dur * 0.60
        view.update()
        assert view._is_teleporting is False
        assert view.is_animating is False
        assert len(tp_callbacks) == 1
        assert tp_callbacks[0] == "teleport_done"

        # Verify pads and rings are hidden after completion
        assert view._teleport_pad_src.visible is False
        assert view._teleport_beam_src.visible is False

        # Additional update does not trigger callback a second time
        u_time.dt = 0.1
        view.update()
        assert len(tp_callbacks) == 1
    finally:
        destroy(view)


def test_cantilever_see_saw_no_origin_jump(engine):
    """Verify cantilever see-saw starts with 0 origin jump and settles callback exactly once."""
    board = load_level_from_file('bloxorz/levels/stage_01.json')
    view = BlockView()
    try:
        # Lying block with (0, 1) supported and (-1, 1) over void
        cantilever_state = NormalBlockState(x=-1, y=1, orientation=BlockOrientation.LYING_X)
        view.sync_to_state(cantilever_state)

        # Record world position of mesh before fall
        mesh_pos_before = Vec3(view.mesh.world_position)

        fall_callbacks = []
        view.animate_fall(
            board=board,
            direction=Direction.LEFT,
            on_complete=lambda: fall_callbacks.append("fall_done"),
        )

        assert view.is_animating is True
        assert view._is_falling is True
        assert view._is_seesaw is True

        # Continuous pivot: initial mesh world position must exactly equal resting position (0 origin jump)
        mesh_pos_after_init = Vec3(view.mesh.world_position)
        assert tuple(mesh_pos_after_init) == pytest.approx(tuple(mesh_pos_before), abs=1e-4)

        # Advance into tipping Phase 1
        u_time.dt = 0.20
        view.update()
        assert view._is_seesaw is True
        assert len(fall_callbacks) == 0

        # Advance past 65 degrees into Phase 2 free fall
        u_time.dt = 0.40
        view.update()
        assert view._seesaw_phase == 2
        assert len(fall_callbacks) == 0

        # Advance to completion
        u_time.dt = 1.20
        view.update()
        assert view._is_falling is False
        assert view.is_animating is False
        assert len(fall_callbacks) == 1
    finally:
        destroy(view)


def test_fragile_straight_vertical_plunge(engine):
    """Verify fragile tile collapse executes straight vertical descent."""
    view = BlockView()
    try:
        standing = NormalBlockState(x=2, y=2, orientation=BlockOrientation.STANDING)
        view.sync_to_state(standing)

        fragile_callbacks = []
        view.animate_fall(
            outcome="FELL_FRAGILE",
            on_complete=lambda: fragile_callbacks.append("fragile_done"),
        )

        assert view.is_animating is True
        assert view._is_falling is True
        assert view._is_seesaw is False
        assert view._fall_mode == "FRAGILE"

        u_time.dt = 0.30
        view.update()
        # Straight vertical drop (horizontal displacement is 0)
        assert view.pivot.x == pytest.approx(2.0, abs=1e-4)
        assert view.pivot.z == pytest.approx(-2.0, abs=1e-4)
        assert view.pivot.y < 1.0

        # Advance to completion
        u_time.dt = 1.20
        view.update()
        assert view.is_animating is False
        assert len(fragile_callbacks) == 1
    finally:
        destroy(view)


def test_victory_vortex_shrink_and_callback(engine):
    """Verify victory descent shrinks into goal well and completes callback exactly once."""
    view = BlockView()
    try:
        goal_state = NormalBlockState(x=5, y=5, orientation=BlockOrientation.STANDING)
        view.sync_to_state(goal_state)

        victory_callbacks = []
        view.animate_victory(on_complete=lambda: victory_callbacks.append("victory_done"))

        assert view.is_animating is True
        assert view._is_sinking_victory is True

        u_time.dt = 1.0
        view.update()
        assert view.pivot.y < 1.0
        assert len(victory_callbacks) == 0

        # Advance past duration
        sink_dur = getattr(CONFIG.motion, "victory_fall_duration", 3.50)
        u_time.dt = sink_dur
        view.update()
        assert view._is_sinking_victory is False
        assert view.is_animating is False
        assert len(victory_callbacks) == 1
    finally:
        destroy(view)


def test_sync_to_state_clears_stale_ghosts_and_resets_state(engine):
    """Verify sync_to_state (stage restart) purges active VFX pools and stops animations."""
    fx = FXManager.get_instance()
    fx.spawn_ghost(Vec3(1, 0, 1), Vec3(0, 0, 0), Vec3(1, 1, 2))
    assert any(g.active for g in fx._ghosts)

    view = BlockView()
    try:
        view.is_animating = True
        view._is_rolling = True

        state = NormalBlockState(x=1, y=1, orientation=BlockOrientation.STANDING)
        view.sync_to_state(state, clear_fx=True)

        assert view.is_animating is False
        assert view._is_rolling is False
        assert not any(g.active for g in fx._ghosts)
    finally:
        destroy(view)
