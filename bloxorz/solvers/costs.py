"""Shared transition costs for UCS and other cost-aware solvers."""

from typing import Callable

from bloxorz.core.block import BaseBlockState, SplitBlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import TileType
from bloxorz.solvers.base import Successor, SWITCH_ACTION


CostFunction = Callable[[BaseBlockState, Board, Successor], float]


def fragile_cost(block: BaseBlockState, board: Board, successor: Successor) -> float:
    """Charge 1 per legal roll, plus 2 if its destination touches fragile tiles.

    Switching control costs zero. For split movement, only the moving cube's
    destination matters; a passive cube resting on fragile incurs no surcharge.
    Contact with two fragile cells by a normal block incurs the same surcharge as one.
    Remaining on fragile tiles on consecutive rolls incurs the surcharge each time.
    This is a deterministic route preference, not a probability of falling.

    Args:
        block: Source block state, including the active cube before a split move.
        board: Source board; available for interchangeable cost functions.
        successor: Legal destination, including the board after switch activation.

    Callers must filter illegal moves before evaluating a cost.
    """
    if successor.direction == SWITCH_ACTION:
        return 0.0
    if isinstance(block, SplitBlockState):
        active = block.active_block
        destination = (active.x + successor.direction.dx, active.y + successor.direction.dy)
        return 3.0 if successor.board.get_tile(*destination) == TileType.FRAGILE else 1.0

    touches_fragile = any(
        successor.board.get_tile(x, y) == TileType.FRAGILE
        for x, y in successor.block.occupied_cells
    )
    return 3.0 if touches_fragile else 1.0
