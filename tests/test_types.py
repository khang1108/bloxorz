"""Unit tests for centralized spatial types and kinematic constants in bloxorz.types."""

from bloxorz.core.constants import Direction, BlockOrientation
from bloxorz.core.block import NormalBlockState
from bloxorz.types import (
    RIGHT_ANGLE_DEG,
    STRAIGHT_ANGLE_DEG,
    FULL_TURN_DEG,
    GROUND_ALTITUDE,
    CUBE_UNIT_SIZE,
    HALF_CUBE_UNIT,
    BLOCK_LONG_UNITS,
    AXIS_X_POS,
    AXIS_X_NEG,
    AXIS_Y_POS,
    AXIS_Y_NEG,
    DIMENSIONS_STANDING,
    DIMENSIONS_LYING_X,
    DIMENSIONS_LYING_Y,
    DIMENSIONS_SINGLE_CUBE,
    ORIENTATION_DIMENSIONS,
    DIRECTION_ROLL_SPECS,
)


def test_geometric_constants():
    assert RIGHT_ANGLE_DEG == 90.0
    assert STRAIGHT_ANGLE_DEG == 180.0
    assert FULL_TURN_DEG == 360.0
    assert GROUND_ALTITUDE == 0.0
    assert CUBE_UNIT_SIZE == 1.0
    assert HALF_CUBE_UNIT == 0.5
    assert BLOCK_LONG_UNITS == 2.0


def test_orientation_dimensions_mapping():
    assert ORIENTATION_DIMENSIONS[BlockOrientation.STANDING] == DIMENSIONS_STANDING
    assert ORIENTATION_DIMENSIONS[BlockOrientation.LYING_X] == DIMENSIONS_LYING_X
    assert ORIENTATION_DIMENSIONS[BlockOrientation.LYING_Y] == DIMENSIONS_LYING_Y
    assert DIMENSIONS_STANDING == (1.0, 1.0, 2.0)
    assert DIMENSIONS_LYING_X == (2.0, 1.0, 1.0)
    assert DIMENSIONS_LYING_Y == (1.0, 2.0, 1.0)
    assert DIMENSIONS_SINGLE_CUBE == (1.0, 1.0, 1.0)


def test_direction_roll_specs():
    # RIGHT: rotates around +Y, contact offset is +half_x
    right_spec = DIRECTION_ROLL_SPECS[Direction.RIGHT]
    assert right_spec.axis == AXIS_Y_POS
    assert right_spec.angle == RIGHT_ANGLE_DEG
    assert right_spec.offset_sign_x == 1.0
    assert right_spec.offset_sign_y == 0.0

    # LEFT: rotates around -Y, contact offset is -half_x
    left_spec = DIRECTION_ROLL_SPECS[Direction.LEFT]
    assert left_spec.axis == AXIS_Y_NEG
    assert left_spec.angle == RIGHT_ANGLE_DEG
    assert left_spec.offset_sign_x == -1.0
    assert left_spec.offset_sign_y == 0.0

    # DOWN: rotates around -X, contact offset is +half_y
    down_spec = DIRECTION_ROLL_SPECS[Direction.DOWN]
    assert down_spec.axis == AXIS_X_NEG
    assert down_spec.angle == RIGHT_ANGLE_DEG
    assert down_spec.offset_sign_x == 0.0
    assert down_spec.offset_sign_y == 1.0

    # UP: rotates around +X, contact offset is -half_y
    up_spec = DIRECTION_ROLL_SPECS[Direction.UP]
    assert up_spec.axis == AXIS_X_POS
    assert up_spec.angle == RIGHT_ANGLE_DEG
    assert up_spec.offset_sign_x == 0.0
    assert up_spec.offset_sign_y == -1.0


def test_normal_block_state_uses_types_correctly():
    block = NormalBlockState(0, 0, BlockOrientation.STANDING)
    center = block.get_center_3d()
    assert center == (0.0, 0.0, 1.0)
    assert block.get_dimensions_3d() == (1.0, 1.0, 2.0)

    # Test pivot and axis calculation using specs
    pivot_r, axis_r, angle_r = block.get_pivot_and_axis(Direction.RIGHT)
    assert pivot_r == (0.5, 0.0, 0.0)
    assert axis_r == AXIS_Y_POS
    assert angle_r == 90.0

    pivot_l, axis_l, angle_l = block.get_pivot_and_axis(Direction.LEFT)
    assert pivot_l == (-0.5, 0.0, 0.0)
    assert axis_l == AXIS_Y_NEG
    assert angle_l == 90.0

    pivot_d, axis_d, angle_d = block.get_pivot_and_axis(Direction.DOWN)
    assert pivot_d == (0.0, 0.5, 0.0)
    assert axis_d == AXIS_X_NEG
    assert angle_d == 90.0

    pivot_u, axis_u, angle_u = block.get_pivot_and_axis(Direction.UP)
    assert pivot_u == (0.0, -0.5, 0.0)
    assert axis_u == AXIS_X_POS
    assert angle_u == 90.0
