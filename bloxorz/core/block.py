"""Block representation and movement mathematics for Bloxorz."""

from dataclasses import dataclass
from typing import Set, Tuple
from bloxorz.core.constants import Direction, BlockOrientation


@dataclass(frozen=True)
class BlockState:
    """Immutable state representation of the Bloxorz block."""
    x: int
    y: int
    orientation: BlockOrientation

    @property
    def is_split(self) -> bool:
        """Indicates this is a standard unified 1x1x2 block."""
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

    def roll(self, direction: Direction) -> "BlockState":
        """Calculates and returns the new BlockState after rolling in a direction."""
        x, y = self.x, self.y
        ori = self.orientation

        if ori == BlockOrientation.STANDING:
            if direction == Direction.RIGHT:
                return BlockState(x + 1, y, BlockOrientation.LYING_X)
            elif direction == Direction.LEFT:
                return BlockState(x - 2, y, BlockOrientation.LYING_X)
            elif direction == Direction.UP:
                return BlockState(x, y - 2, BlockOrientation.LYING_Y)
            elif direction == Direction.DOWN:
                return BlockState(x, y + 1, BlockOrientation.LYING_Y)

        elif ori == BlockOrientation.LYING_X:
            if direction == Direction.RIGHT:
                return BlockState(x + 2, y, BlockOrientation.STANDING)
            elif direction == Direction.LEFT:
                return BlockState(x - 1, y, BlockOrientation.STANDING)
            elif direction == Direction.UP:
                return BlockState(x, y - 1, BlockOrientation.LYING_X)
            elif direction == Direction.DOWN:
                return BlockState(x, y + 1, BlockOrientation.LYING_X)

        elif ori == BlockOrientation.LYING_Y:
            if direction == Direction.RIGHT:
                return BlockState(x + 1, y, BlockOrientation.LYING_Y)
            elif direction == Direction.LEFT:
                return BlockState(x - 1, y, BlockOrientation.LYING_Y)
            elif direction == Direction.UP:
                return BlockState(x, y - 1, BlockOrientation.STANDING)
            elif direction == Direction.DOWN:
                return BlockState(x, y + 2, BlockOrientation.STANDING)

        raise ValueError(f"Invalid roll combination: {ori}, {direction}")

    def get_center_3d(self) -> Tuple[float, float, float]:
        """Returns the 3D center coordinate (x, y, z) in world units.

        Assumes grid cells have size 1x1, ground is at z=0, and height is along Z.
        """
        if self.orientation == BlockOrientation.STANDING:
            return (float(self.x), float(self.y), 1.0)
        elif self.orientation == BlockOrientation.LYING_X:
            return (self.x + 0.5, float(self.y), 0.5)
        elif self.orientation == BlockOrientation.LYING_Y:
            return (float(self.x), self.y + 0.5, 0.5)
        raise ValueError(f"Unknown orientation: {self.orientation}")

    def get_dimensions_3d(self) -> Tuple[float, float, float]:
        """Returns (width_x, depth_y, height_z) of the block."""
        if self.orientation == BlockOrientation.STANDING:
            return (1.0, 1.0, 2.0)
        elif self.orientation == BlockOrientation.LYING_X:
            return (2.0, 1.0, 1.0)
        elif self.orientation == BlockOrientation.LYING_Y:
            return (1.0, 2.0, 1.0)
        raise ValueError(f"Unknown orientation: {self.orientation}")

    def get_pivot_and_axis(
        self, direction: Direction
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], float]:
        """Computes the pivot point, rotation axis vector, and rotation angle (in degrees).

        Returns:
            ((pivot_x, pivot_y, pivot_z), (axis_x, axis_y, axis_z), angle_degrees)
        """
        center = self.get_center_3d()
        dim = self.get_dimensions_3d()
        half_x, half_y = dim[0] / 2.0, dim[1] / 2.0

        # Ground level is z=0, bottom of block is at z=0.
        pivot_z = 0.0

        if direction == Direction.RIGHT:
            pivot_x = center[0] + half_x
            pivot_y = center[1]
            axis = (0.0, 1.0, 0.0)  # Rotates around Y
            angle = 90.0
        elif direction == Direction.LEFT:
            pivot_x = center[0] - half_x
            pivot_y = center[1]
            axis = (0.0, -1.0, 0.0)
            angle = 90.0
        elif direction == Direction.DOWN:
            pivot_x = center[0]
            pivot_y = center[1] + half_y
            axis = (-1.0, 0.0, 0.0)  # Rotates around X
            angle = 90.0
        elif direction == Direction.UP:
            pivot_x = center[0]
            pivot_y = center[1] - half_y
            axis = (1.0, 0.0, 0.0)
            angle = 90.0
        else:
            raise ValueError(f"Unsupported direction: {direction}")

        return ((pivot_x, pivot_y, pivot_z), axis, angle)
