"""Abstract base class for Bloxorz block state representations."""

from abc import ABC, abstractmethod
from typing import Set, Tuple
from bloxorz.core.constants import Direction


class BaseBlockState(ABC):
    """Abstract base class representing an immutable configuration of the player block(s)."""

    @property
    @abstractmethod
    def is_split(self) -> bool:
        """Indicates whether the block is currently divided into two separate 1x1x1 cubes."""
        pass

    @property
    @abstractmethod
    def occupied_cells(self) -> Set[Tuple[int, int]]:
        """Returns the set of 2D grid coordinates (x, y) occupied on the board."""
        pass

    @abstractmethod
    def roll(self, direction: Direction) -> "BaseBlockState":
        """Calculates and returns the new block state after moving in the given direction."""
        pass

    @abstractmethod
    def canonical_key(self) -> tuple:
        """Returns an immutable hashable tuple uniquely identifying the state for solver visited sets."""
        pass
