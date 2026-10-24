"""Split block state representation for dual 1x1x1 cubes created by teleport tiles."""

from dataclasses import dataclass
from typing import Set, Tuple, Optional
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
    def occupied_cells(self) -> Set[Tuple[int, int]]:
        """Returns the set of grid cells occupied by both cubes."""
        return {(self.b1.x, self.b1.y), (self.b2.x, self.b2.y)}

    def roll(self, direction: Direction) -> "SplitBlockState":
        """Polymorphic alias for move_active to conform to BaseBlockState."""
        return self.move_active(direction)

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
