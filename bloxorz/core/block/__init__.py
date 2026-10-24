"""Block representations and kinematic models for Bloxorz."""

from bloxorz.core.block.base import BaseBlockState
from bloxorz.core.block.normal import NormalBlockState
from bloxorz.core.block.split import SplitBlockState, SingleBlock

# Backward-compatible alias for existing codebase
BlockState = NormalBlockState

__all__ = [
    "BaseBlockState",
    "NormalBlockState",
    "SplitBlockState",
    "SingleBlock",
    "BlockState",
]
