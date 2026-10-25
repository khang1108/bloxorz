"""Centralized reusable types, kinematic constants, and spatial vectors for Bloxorz."""

from typing import Tuple, NamedTuple, Dict
from bloxorz.core.constants import Direction, BlockOrientation


# =============================================================================
# SPATIAL & KINEMATIC TYPE ALIASES
# =============================================================================

Coord2D = Tuple[int, int]
"""2D discrete integer grid coordinate (x, y)."""

Vector3D = Tuple[float, float, float]
"""3D continuous floating-point vector (x, y, z)."""

Dimensions3D = Tuple[float, float, float]
"""3D dimensions tuple (width_x, depth_y, height_z)."""


# =============================================================================
# GEOMETRIC & ANGULAR CONSTANTS
# =============================================================================

RIGHT_ANGLE_DEG: float = 90.0
"""Quarter-turn roll rotation angle in degrees."""

STRAIGHT_ANGLE_DEG: float = 180.0
"""Half-turn rotation angle in degrees."""

FULL_TURN_DEG: float = 360.0
"""Complete circular revolution angle in degrees."""

GROUND_ALTITUDE: float = 0.0
"""Contact ground plane Z/Y altitude level in world space."""

CUBE_UNIT_SIZE: float = 1.0
"""Standard edge length of a single 1x1 grid cell / unit cube."""

HALF_CUBE_UNIT: float = 0.5
"""Center altitude or edge-to-center offset of a unit cube (0.5 units)."""

BLOCK_LONG_UNITS: float = 2.0
"""Length of the long axis of the monolithic Bloxorz block (2.0 units)."""


# =============================================================================
# 3D CARTESIAN UNIT AXES
# =============================================================================

AXIS_X_POS: Vector3D = (1.0, 0.0, 0.0)
"""Positive X unit vector (Right / East)."""

AXIS_X_NEG: Vector3D = (-1.0, 0.0, 0.0)
"""Negative X unit vector (Left / West)."""

AXIS_Y_POS: Vector3D = (0.0, 1.0, 0.0)
"""Positive Y unit vector (Forward / North)."""

AXIS_Y_NEG: Vector3D = (0.0, -1.0, 0.0)
"""Negative Y unit vector (Backward / South)."""

AXIS_Z_POS: Vector3D = (0.0, 0.0, 1.0)
"""Positive Z unit vector (Up)."""

AXIS_Z_NEG: Vector3D = (0.0, 0.0, -1.0)
"""Negative Z unit vector (Down)."""


# =============================================================================
# CANONICAL 3D BLOCK DIMENSIONS
# =============================================================================

DIMENSIONS_STANDING: Dimensions3D = (CUBE_UNIT_SIZE, CUBE_UNIT_SIZE, BLOCK_LONG_UNITS)
"""Dimensions when block is standing upright: (1.0, 1.0, 2.0)."""

DIMENSIONS_LYING_X: Dimensions3D = (BLOCK_LONG_UNITS, CUBE_UNIT_SIZE, CUBE_UNIT_SIZE)
"""Dimensions when block is lying horizontally along X: (2.0, 1.0, 1.0)."""

DIMENSIONS_LYING_Y: Dimensions3D = (CUBE_UNIT_SIZE, BLOCK_LONG_UNITS, CUBE_UNIT_SIZE)
"""Dimensions when block is lying horizontally along Y: (1.0, 2.0, 1.0)."""

DIMENSIONS_SINGLE_CUBE: Dimensions3D = (CUBE_UNIT_SIZE, CUBE_UNIT_SIZE, CUBE_UNIT_SIZE)
"""Dimensions for a separated 1x1x1 unit cube: (1.0, 1.0, 1.0)."""

ORIENTATION_DIMENSIONS: Dict[BlockOrientation, Dimensions3D] = {
    BlockOrientation.STANDING: DIMENSIONS_STANDING,
    BlockOrientation.LYING_X: DIMENSIONS_LYING_X,
    BlockOrientation.LYING_Y: DIMENSIONS_LYING_Y,
}
"""Lookup mapping from BlockOrientation enum to canonical 3D dimensions."""


# =============================================================================
# ROLLING CONTACT PIVOT & ROTATION SPECIFICATION
# =============================================================================

class RollPivotSpec(NamedTuple):
    """Encapsulates the mathematical contact edge pivot offset and rotation axis for a roll."""
    axis: Vector3D
    angle: float
    offset_sign_x: float
    offset_sign_y: float


DIRECTION_ROLL_SPECS: Dict[Direction, RollPivotSpec] = {
    Direction.RIGHT: RollPivotSpec(
        axis=AXIS_Y_POS,
        angle=RIGHT_ANGLE_DEG,
        offset_sign_x=1.0,
        offset_sign_y=0.0,
    ),
    Direction.LEFT: RollPivotSpec(
        axis=AXIS_Y_NEG,
        angle=RIGHT_ANGLE_DEG,
        offset_sign_x=-1.0,
        offset_sign_y=0.0,
    ),
    Direction.DOWN: RollPivotSpec(
        axis=AXIS_X_NEG,
        angle=RIGHT_ANGLE_DEG,
        offset_sign_x=0.0,
        offset_sign_y=1.0,
    ),
    Direction.UP: RollPivotSpec(
        axis=AXIS_X_POS,
        angle=RIGHT_ANGLE_DEG,
        offset_sign_x=0.0,
        offset_sign_y=-1.0,
    ),
}
"""Reusable kinematic specifications for 90-degree rolls along contact pivot edges."""
