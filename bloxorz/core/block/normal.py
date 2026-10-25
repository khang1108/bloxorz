"""Normal (monolithic 1x1x2) block state representation and movement mathematics."""

from dataclasses import dataclass
from typing import Set, Tuple
from bloxorz.core.constants import Direction, BlockOrientation
from bloxorz.core.block.base import BaseBlockState
from bloxorz.types import (
    Vector3D,
    Dimensions3D,
    CUBE_UNIT_SIZE,
    HALF_CUBE_UNIT,
    GROUND_ALTITUDE,
    ORIENTATION_DIMENSIONS,
    DIRECTION_ROLL_SPECS,
)


@dataclass(frozen=True)
class NormalBlockState(BaseBlockState):
    """Immutable state representation of the monolithic 1x1x2 Bloxorz block."""
    x: int
    y: int
    orientation: BlockOrientation

    @property
    def is_split(self) -> bool:
        """Indicates whether the block is split into separate cubes (always False for NormalBlockState)."""
        return False

    @property
    def occupied_cells(self) -> Set[Tuple[int, int]]:
        """Returns the set of 2D grid cells currently covered by the block."""
        if self.orientation == BlockOrientation.STANDING:
            return {(self.x, self.y)}
        elif self.orientation == BlockOrientation.LYING_X:
            return {(self.x, self.y), (self.x + 1, self.y)}
        elif self.orientation == BlockOrientation.LYING_Y:
            return {(self.x, self.y), (self.x, self.y + 1)}
        raise ValueError(f"Unknown orientation: {self.orientation}")

    def roll(self, direction: Direction) -> "NormalBlockState":
        """Calculates and returns the new NormalBlockState after rolling in a direction."""
        x, y = self.x, self.y
        ori = self.orientation

        if ori == BlockOrientation.STANDING:
            if direction == Direction.RIGHT:
                return NormalBlockState(x + 1, y, BlockOrientation.LYING_X)
            elif direction == Direction.LEFT:
                return NormalBlockState(x - 2, y, BlockOrientation.LYING_X)
            elif direction == Direction.UP:
                return NormalBlockState(x, y - 2, BlockOrientation.LYING_Y)
            elif direction == Direction.DOWN:
                return NormalBlockState(x, y + 1, BlockOrientation.LYING_Y)

        elif ori == BlockOrientation.LYING_X:
            if direction == Direction.RIGHT:
                return NormalBlockState(x + 2, y, BlockOrientation.STANDING)
            elif direction == Direction.LEFT:
                return NormalBlockState(x - 1, y, BlockOrientation.STANDING)
            elif direction == Direction.UP:
                return NormalBlockState(x, y - 1, BlockOrientation.LYING_X)
            elif direction == Direction.DOWN:
                return NormalBlockState(x, y + 1, BlockOrientation.LYING_X)

        elif ori == BlockOrientation.LYING_Y:
            if direction == Direction.RIGHT:
                return NormalBlockState(x + 1, y, BlockOrientation.LYING_Y)
            elif direction == Direction.LEFT:
                return NormalBlockState(x - 1, y, BlockOrientation.LYING_Y)
            elif direction == Direction.UP:
                return NormalBlockState(x, y - 1, BlockOrientation.STANDING)
            elif direction == Direction.DOWN:
                return NormalBlockState(x, y + 2, BlockOrientation.STANDING)

        raise ValueError(f"Invalid roll combination: {ori}, {direction}")

    def get_center_3d(self) -> Vector3D:
        """Returns the 3D center coordinate (x, y, z) in world units.

        Assumes grid cells have size 1x1, ground is at z=0, and height is along Z.
        """
        if self.orientation == BlockOrientation.STANDING:
            return (float(self.x), float(self.y), CUBE_UNIT_SIZE)
        elif self.orientation == BlockOrientation.LYING_X:
            return (self.x + HALF_CUBE_UNIT, float(self.y), HALF_CUBE_UNIT)
        elif self.orientation == BlockOrientation.LYING_Y:
            return (float(self.x), self.y + HALF_CUBE_UNIT, HALF_CUBE_UNIT)
        raise ValueError(f"Unknown orientation: {self.orientation}")

    def get_dimensions_3d(self) -> Dimensions3D:
        """Returns (width_x, depth_y, height_z) of the block."""
        dim = ORIENTATION_DIMENSIONS.get(self.orientation)
        if dim is not None:
            return dim
        raise ValueError(f"Unknown orientation: {self.orientation}")

    def get_pivot_and_axis(
        self, direction: Direction
    ) -> Tuple[Vector3D, Vector3D, float]:
        """Computes the pivot point, rotation axis vector, and rotation angle (in degrees).

        Returns:
            ((pivot_x, pivot_y, pivot_z), (axis_x, axis_y, axis_z), angle_degrees)
        """
        spec = DIRECTION_ROLL_SPECS.get(direction)
        if not spec:
            raise ValueError(f"Unsupported direction: {direction}")

        center = self.get_center_3d()
        dim = self.get_dimensions_3d()
        half_x, half_y = dim[0] / 2.0, dim[1] / 2.0

        pivot = (
            center[0] + spec.offset_sign_x * half_x,
            center[1] + spec.offset_sign_y * half_y,
            GROUND_ALTITUDE,
        )
        return (pivot, spec.axis, spec.angle)

    def canonical_key(self) -> tuple:
        """Returns an immutable hashable tuple uniquely identifying the state."""
        return (False, self.x, self.y, self.orientation)
