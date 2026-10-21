"""Core constants, enums, and data definitions for Bloxorz."""

from enum import Enum, auto


class Direction(Enum):
    """Movement directions on the grid."""
    UP = (0, -1)     # -Y (North in 2D grid)
    DOWN = (0, 1)    # +Y (South in 2D grid)
    LEFT = (-1, 0)   # -X (West in 2D grid)
    RIGHT = (1, 0)   # +X (East in 2D grid)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]


class BlockOrientation(Enum):
    """Spatial orientation of the 1x1x2 block."""
    STANDING = auto()     # Occupies 1 cell: (x, y), height = 2
    LYING_X = auto()      # Occupies 2 cells: (x, y) and (x + 1, y), height = 1
    LYING_Y = auto()      # Occupies 2 cells: (x, y) and (x, y + 1), height = 1


class TileType(Enum):
    """Board tile types conforming to classic Bloxorz rules."""
    VOID = 0             # Empty space / fall off
    NORMAL = 1           # Standard durable stone tile
    GOAL = 2             # The exit hole
    FRAGILE = 3          # Orange tile: supports lying, breaks if standing upright
    SWITCH_SOFT = 4      # Circle switch: activates on any touch (lying or standing)
    SWITCH_HEAVY = 5     # Cross switch (X): activates ONLY on full upright standing
    BRIDGE_CLOSED = 6    # Inactive bridge tile (acts like void)
    BRIDGE_OPEN = 7      # Active bridge tile (acts like normal tile)
    TELEPORT = 8         # Special teleport/splitter tile (optional expansion)


class GameStatus(Enum):
    """Current state of the game loop."""
    PLAYING = auto()
    ROLLING = auto()
    FALLING = auto()
    VICTORY = auto()
    PAUSED = auto()
