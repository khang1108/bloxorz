"""Shared transition costs for UCS and other cost-aware solvers."""

from typing import Callable

from bloxorz.core.block import BlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import TileType
from bloxorz.solvers.base import Successor


CostFunction = Callable[[BlockState, Board, Successor], float]


def fragile_cost(block: BlockState, board: Board, successor: Successor) -> float:
    """Charge 1 per legal roll, plus 2 if its destination touches fragile tiles.

    Contact with two fragile cells incurs the same surcharge as contact with one.
    Remaining on fragile tiles on consecutive rolls incurs the surcharge each time.
    This is a deterministic route preference, not a probability of falling.

    Args:
        block: Source block state; available for interchangeable cost functions.
        board: Source board; available for interchangeable cost functions.
        successor: Legal destination, including the board after switch activation.

    Callers must filter illegal moves before evaluating a cost. Split cubes are
    not supported by the current core state/action interface.
    """
    touches_fragile = any(
        successor.board.get_tile(x, y) == TileType.FRAGILE
        for x, y in successor.block.occupied_cells
    )
    return 3.0 if touches_fragile else 1.0
