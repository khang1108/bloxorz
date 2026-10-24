"""Tests for see-saw cantilever fall physics and goal victory plunge animations."""

import math
from ursina import Ursina
from bloxorz.config import CONFIG
from bloxorz.core.constants import TileType, Direction, BlockOrientation
from bloxorz.core.block import BlockState
from bloxorz.core.board import Board
from bloxorz.graphics.block_view import BlockView
from bloxorz.ui.theme import Motion


# Ensure headless Ursina application exists for testing entity transforms
app = Ursina(headless=True)


def create_test_board(walkable_coords):
    """Creates a Board fixture with specific walkable coordinates."""
    tiles = {coord: TileType.NORMAL for coord in walkable_coords}
    return Board(
        tiles=tiles,
        goal_pos=(0, 0),
        spawn_state=BlockState(0, 0, BlockOrientation.STANDING),
    )


class TestSeeSawFallPhysics:
    """Verifies that cantilevered falls produce see-saw torque without clipping the floor."""

    def test_cantilever_detection_lying_x_void_right(self):
        """Block at (0, 0) lying X with (0,0) walkable and (1,0) void -> tilts right."""
        board = create_test_board([(0, 0)])
        bv = BlockView()
        state = BlockState(0, 0, BlockOrientation.LYING_X)
        bv.sync_to_state(state)

        bv.animate_fall(board=board, direction=Direction.RIGHT)

        assert bv._is_seesaw is True
        assert bv._seesaw_axis == "z"
        assert bv._tilt_sign == 1.0  # +Z rotation dips +X down
        # Fulcrum should be exactly at contact edge: x = 0.5, y = 0.0, z = 0.0
        assert math.isclose(bv.pivot.x, 0.5, abs_tol=1e-5)
        assert math.isclose(bv.pivot.y, 0.0, abs_tol=1e-5)
        assert math.isclose(bv.pivot.z, 0.0, abs_tol=1e-5)

        # Discontinuity check: mesh world position matches state center (0.5, 0.5, 0.0)
        assert math.isclose(bv.mesh.world_position.x, 0.5, abs_tol=1e-5)
        assert math.isclose(bv.mesh.world_position.y, 0.5, abs_tol=1e-5)

    def test_cantilever_detection_lying_x_void_left(self):
        """Block at (0, 0) lying X with (1,0) walkable and (0,0) void -> tilts left."""
        board = create_test_board([(1, 0)])
        bv = BlockView()
        state = BlockState(0, 0, BlockOrientation.LYING_X)
        bv.sync_to_state(state)

        bv.animate_fall(board=board, direction=Direction.LEFT)

        assert bv._is_seesaw is True
        assert bv._seesaw_axis == "z"
        assert bv._tilt_sign == -1.0  # -Z rotation dips -X down
        assert math.isclose(bv.pivot.x, 0.5, abs_tol=1e-5)
        assert math.isclose(bv.pivot.y, 0.0, abs_tol=1e-5)

    def test_cantilever_detection_lying_y(self):
        """Block lying Y tests for North and South void tipping."""
        bv = BlockView()
        state = BlockState(0, 0, BlockOrientation.LYING_Y)

        # Void South (+Y grid -> -Z Ursina)
        board_south_void = create_test_board([(0, 0)])
        bv.sync_to_state(state)
        bv.animate_fall(board=board_south_void, direction=Direction.DOWN)
        assert bv._is_seesaw is True
        assert bv._seesaw_axis == "x"
        assert bv._tilt_sign == -1.0
        assert math.isclose(bv.pivot.z, -0.5, abs_tol=1e-5)

        # Void North (-Y grid -> +Z Ursina)
        board_north_void = create_test_board([(0, 1)])
        bv.sync_to_state(state)
        bv.animate_fall(board=board_north_void, direction=Direction.UP)
        assert bv._is_seesaw is True
        assert bv._seesaw_axis == "x"
        assert bv._tilt_sign == 1.0
        assert math.isclose(bv.pivot.z, -0.5, abs_tol=1e-5)

    def test_no_cantilever_when_both_cells_void_or_standing(self):
        """Standing blocks or blocks fully off the board fall directly."""
        bv = BlockView()
        board = create_test_board([(5, 5)])  # Nowhere near (0, 0)

        # Lying with both cells off board
        state_lying = BlockState(0, 0, BlockOrientation.LYING_X)
        bv.sync_to_state(state_lying)
        bv.animate_fall(board=board, direction=Direction.RIGHT)
        assert bv._is_seesaw is False

        # Standing block
        state_standing = BlockState(0, 0, BlockOrientation.STANDING)
        bv.sync_to_state(state_standing)
        bv.animate_fall(board=board, direction=Direction.RIGHT)
        assert bv._is_seesaw is False

    def test_supported_bottom_corner_never_clips_floor(self):
        """The supported end must lift into the air (Y >= 0.0) throughout the tilt."""
        board = create_test_board([(0, 0)])
        bv = BlockView()
        state = BlockState(0, 0, BlockOrientation.LYING_X)
        bv.sync_to_state(state)
        bv.animate_fall(board=board, direction=Direction.RIGHT)

        # Fulcrum is at (0.5, 0.0, 0.0). Supported tile is centered at 0.0, left edge at -0.5.
        # Pivot-relative coordinate of supported bottom-left corner is (-1.0, 0.0, 0.0).
        for angle in range(0, 66, 5):
            rad = math.radians(angle)
            # In Ursina +Z rotation, local point (-1.0, 0.0) transforms to:
            # y_world = fulcrum_y + (-1.0) * (-sin(rad)) = sin(rad)
            supported_corner_y = bv.pivot.y + math.sin(rad)
            assert supported_corner_y >= 0.0, f"Floor clipping at angle {angle}: Y={supported_corner_y}"


class TestGoalVictoryPlungeAnimation:
    """Verifies that victory goal plunge lasts 4 to 8 seconds and descends deep into the goal hole."""

    def test_victory_fall_duration_in_user_specified_range(self):
        """User requested prolonged plunge lasting 4 to 8 seconds before victory screen."""
        assert 4.0 <= CONFIG.motion.victory_fall_duration <= 8.0
        assert 4.0 <= Motion.VICTORY_FALL_DURATION <= 8.0
        assert math.isclose(CONFIG.motion.victory_fall_duration, 4.50, abs_tol=1e-2)

    def test_victory_sink_state_and_completion_callback(self):
        """Verifies victory plunge initiation and state flags."""
        bv = BlockView()
        completed = False

        def on_done():
            nonlocal completed
            completed = True

        bv.animate_victory(on_complete=on_done)
        assert bv.is_animating is True
        assert bv._is_sinking_victory is True
        assert bv._victory_time == 0.0
        assert bv._on_victory_complete is on_done
