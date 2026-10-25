"""Split block representation and mechanics for Bloxorz."""

from dataclasses import dataclass
from typing import Set, Tuple, Union
from bloxorz.core.constants import Direction, BlockOrientation
from bloxorz.core.block import BlockState


@dataclass
class Teleport:
    """A split switch that separates the block into two 1x1x1 unit cubes and teleports them."""
    x: int
    y: int
    target_1: Tuple[int, int]
    target_2: Tuple[int, int]
    selected: int = 0


@dataclass(frozen=True)
class SplitBlockState:
    """Immutable state representation of a Bloxorz block split into two 1x1x1 unit cubes.

    When split, the player/solver controls one unit cube at a time.
    Switching active cube is performed via Direction.SWITCH_CUBE.
    When the two cubes become orthogonally adjacent, they automatically
    merge back into a standard 1x1x2 BlockState.
    """
    cube1: Tuple[int, int]
    cube2: Tuple[int, int]
    active_cube: int = 0  # 0 -> cube1, 1 -> cube2

    @property
    def is_split(self) -> bool:
        """Indicates this block is split into two unit cubes."""
        return True

    @property
    def active_coord(self) -> Tuple[int, int]:
        """Returns the 2D coordinate of the currently active unit cube."""
        return self.cube1 if self.active_cube == 0 else self.cube2

    @property
    def inactive_coord(self) -> Tuple[int, int]:
        """Returns the 2D coordinate of the currently inactive unit cube."""
        return self.cube2 if self.active_cube == 0 else self.cube1

    @property
    def occupied_cells(self) -> Set[Tuple[int, int]]:
        """Returns the set of 2D cells occupied by both cubes."""
        return {self.cube1, self.cube2}

    def switch_active(self) -> "SplitBlockState":
        """Returns a new state with control toggled to the other cube."""
        return SplitBlockState(self.cube1, self.cube2, 1 - self.active_cube)

    def roll(self, direction: Direction) -> Union["SplitBlockState", BlockState]:
        """Moves the active cube in the specified direction or toggles control.

        If the move places the active cube directly adjacent to the other cube,
        they immediately merge back into a unified 1x1x2 BlockState.
        """
        if direction == Direction.SWITCH_CUBE:
            return self.switch_active()

        active = self.active_coord
        new_active = (active[0] + direction.dx, active[1] + direction.dy)

        if self.active_cube == 0:
            new_c1 = new_active
            new_c2 = self.cube2
        else:
            new_c1 = self.cube1
            new_c2 = new_active

        x1, y1 = new_c1
        x2, y2 = new_c2

        # Check orthogonal adjacency for merge
        if y1 == y2 and abs(x1 - x2) == 1:
            # Merged horizontally into LYING_X
            min_x = min(x1, x2)
            return BlockState(min_x, y1, BlockOrientation.LYING_X)
        elif x1 == x2 and abs(y1 - y2) == 1:
            # Merged vertically into LYING_Y
            min_y = min(y1, y2)
            return BlockState(x1, min_y, BlockOrientation.LYING_Y)

        return SplitBlockState(new_c1, new_c2, self.active_cube)

    def get_center_3d(self) -> Tuple[float, float, float]:
        """Returns the 3D center coordinate of the active cube."""
        coord = self.active_coord
        return (float(coord[0]), float(coord[1]), 0.5)

    def get_dimensions_3d(self) -> Tuple[float, float, float]:
        """Returns (width_x, depth_y, height_z) of a single unit cube."""
        return (1.0, 1.0, 1.0)
