"""Split block state representation for dual 1x1x1 cubes created by teleport tiles."""

from dataclasses import dataclass
from typing import Set, Tuple, Optional, Any
from bloxorz.core.constants import Direction, BlockOrientation
from bloxorz.core.block.base import BaseBlockState
from bloxorz.core.block.normal import NormalBlockState
from bloxorz.types import (
    Vector3D,
    Dimensions3D,
    HALF_CUBE_UNIT,
    DIMENSIONS_SINGLE_CUBE,
)


@dataclass(frozen=True)
class SingleBlock:
    """A single 1x1x1 cube resulting from a teleport split."""
    x: int
    y: int

    def move(self, direction: Direction) -> "SingleBlock":
        """Returns a new SingleBlock moved 1 tile in the specified direction."""
        dx, dy = direction.value
        return SingleBlock(self.x + dx, self.y + dy)

    def get_center_3d(self) -> Vector3D:
        """Returns 3D center (x, y, z=0.5) in world units for a 1x1x1 cube resting on ground."""
        return (float(self.x), float(self.y), HALF_CUBE_UNIT)

    def get_dimensions_3d(self) -> Dimensions3D:
        """Returns (1.0, 1.0, 1.0) for a 1x1x1 cube."""
        return DIMENSIONS_SINGLE_CUBE


@dataclass(frozen=True)
class SplitBlockState(BaseBlockState):
    """Immutable state of two separated 1x1x1 cubes with one actively controlled."""
    b1: SingleBlock
    b2: SingleBlock
    active_index: int = 0  # 0 for b1 active, 1 for b2 active

    def __init__(
        self,
        b1: Optional[Any] = None,
        b2: Optional[Any] = None,
        active_index: int = 0,
        cube1: Optional[Tuple[int, int]] = None,
        cube2: Optional[Tuple[int, int]] = None,
        active_cube: Optional[int] = None,
    ):
        actual_b1 = cube1 if cube1 is not None else b1
        actual_b2 = cube2 if cube2 is not None else b2
        actual_idx = active_cube if active_cube is not None else active_index

        if isinstance(actual_b1, (tuple, list)):
            actual_b1 = SingleBlock(actual_b1[0], actual_b1[1])
        if isinstance(actual_b2, (tuple, list)):
            actual_b2 = SingleBlock(actual_b2[0], actual_b2[1])

        object.__setattr__(self, "b1", actual_b1)
        object.__setattr__(self, "b2", actual_b2)
        object.__setattr__(self, "active_index", actual_idx)

    @property
    def cube1(self) -> Tuple[int, int]:
        """Returns 2D tuple (x, y) of b1."""
        return (self.b1.x, self.b1.y)

    @property
    def cube2(self) -> Tuple[int, int]:
        """Returns 2D tuple (x, y) of b2."""
        return (self.b2.x, self.b2.y)

    @property
    def active_cube(self) -> int:
        """Returns the active cube index (alias for active_index)."""
        return self.active_index

    @property
    def is_split(self) -> bool:
        """Indicates whether the block is split into separate cubes (always True for SplitBlockState)."""
        return True

    @property
    def active_block(self) -> SingleBlock:
        """Returns the currently player-controlled 1x1x1 cube."""
        return self.b1 if self.active_index == 0 else self.b2

    @property
    def passive_block(self) -> SingleBlock:
        """Returns the stationary/inactive 1x1x1 cube."""
        return self.b2 if self.active_index == 0 else self.b1

    @property
    def active_coord(self) -> Tuple[int, int]:
        """Returns 2D (x, y) coordinates of the active cube."""
        return (self.active_block.x, self.active_block.y)

    @property
    def inactive_coord(self) -> Tuple[int, int]:
        """Returns 2D (x, y) coordinates of the inactive cube."""
        return (self.passive_block.x, self.passive_block.y)

    @property
    def occupied_cells(self) -> Set[Tuple[int, int]]:
        """Returns the set of grid cells occupied by both cubes."""
        return {(self.b1.x, self.b1.y), (self.b2.x, self.b2.y)}

    def get_center_3d(self) -> Vector3D:
        """Returns the 3D center of the currently active 1x1x1 cube."""
        return self.active_block.get_center_3d()

    def get_dimensions_3d(self) -> Dimensions3D:
        """Returns (1.0, 1.0, 1.0) for the active 1x1x1 cube."""
        return self.active_block.get_dimensions_3d()

    def roll(self, direction: Direction) -> BaseBlockState:
        """Polymorphic alias for move_active to conform to BaseBlockState."""
        if direction == Direction.SWITCH_CUBE:
            return self.switch_active()
        next_state = self.move_active(direction)
        merged = next_state.check_merge()
        if merged is not None:
            return merged
        return next_state

    def move_active(self, direction: Direction) -> "SplitBlockState":
        """Moves the currently active 1x1x1 cube one cell in the given direction."""
        new_active = self.active_block.move(direction)
        if self.active_index == 0:
            return SplitBlockState(new_active, self.b2, 0)
        return SplitBlockState(self.b1, new_active, 1)

    def switch_active(self) -> "SplitBlockState":
        """Toggles active control between b1 and b2 (invoked by SPACE key)."""
        return SplitBlockState(self.b1, self.b2, 1 - self.active_index)

    def check_merge(self) -> Optional[NormalBlockState]:
        """Checks if the two blocks are adjacent and recombines them if so.

        Recombination occurs when Manhattan distance == 1:
        |x1 - x2| + |y1 - y2| == 1.
        - If x1 != x2 (adjacent horizontally): merges into LYING_X.
        - If y1 != y2 (adjacent vertically): merges into LYING_Y.
        """
        dx = abs(self.b1.x - self.b2.x)
        dy = abs(self.b1.y - self.b2.y)
        if dx + dy == 1:
            if dx == 1:
                min_x = min(self.b1.x, self.b2.x)
                return NormalBlockState(min_x, self.b1.y, BlockOrientation.LYING_X)
            else:
                min_y = min(self.b1.y, self.b2.y)
                return NormalBlockState(self.b1.x, min_y, BlockOrientation.LYING_Y)
        return None

    def canonical_key(self) -> tuple:
        """Returns an order-independent canonical key for state deduplication in search algorithms.

        Since (b1 at A, b2 at B with active=0) is functionally identical to
        (b1 at B, b2 at A with active=1), we sort the two coordinates and track
        the coordinate of the currently active block.
        """
        c1 = (self.b1.x, self.b1.y)
        c2 = (self.b2.x, self.b2.y)
        active_coord = c1 if self.active_index == 0 else c2
        sorted_coords = tuple(sorted([c1, c2]))
        return (True, sorted_coords, active_coord)

    @classmethod
    def from_targets(
        cls,
        target_1: Tuple[int, int],
        target_2: Tuple[int, int],
        selected: int = 0,
    ) -> "SplitBlockState":
        """Constructs a SplitBlockState directly from teleport destination coordinates."""
        return cls(
            b1=SingleBlock(target_1[0], target_1[1]),
            b2=SingleBlock(target_2[0], target_2[1]),
            active_index=selected,
        )
