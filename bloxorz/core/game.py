"""Game session controller managing turns, moves, undo, and state transitions."""

from typing import List, Tuple, Dict, Any
from bloxorz.core.constants import Direction, GameStatus
from bloxorz.core.block.base import BaseBlockState
from bloxorz.core.block.split import SplitBlockState
from bloxorz.core.board import Board


class Game:
    """High-level game controller managing a single level session."""

    def __init__(self, board: Board):
        self.board: Board = board
        self.block: BaseBlockState = board.spawn_state
        self.move_count: int = 0
        self.status: GameStatus = GameStatus.PLAYING

        # History stack for full Undo support: (block_state, bridge_states_dict, move_count)
        self.history: List[Tuple[BaseBlockState, Dict[str, bool], int]] = []

    def restart(self):
        """Restarts the level to its initial spawn configuration."""
        self.board.reset()
        self.block = self.board.spawn_state
        self.move_count = 0
        self.status = GameStatus.PLAYING
        self.history.clear()

    def snapshot_state(self) -> Tuple[BaseBlockState, Dict[str, bool], int]:
        """Takes a snapshot of current block, bridge configurations, and move count."""
        bridge_states = {
            b_id: bridge.is_open for b_id, bridge in self.board.bridges.items()
        }
        return (self.block, bridge_states, self.move_count)

    def switch_block(self) -> bool:
        """Toggles active control between the two 1x1x1 cubes when in split state."""
        if self.status != GameStatus.PLAYING or not getattr(self.block, "is_split", False):
            return False

        self.history.append(self.snapshot_state())
        self.block = self.block.switch_active()
        return True

    def roll(self, direction: Direction) -> Tuple[str, BaseBlockState, Any]:
        """Attempts to roll or move the block in the given direction.

        Returns:
            (outcome, new_block_state, detail)
            where outcome is one of:
            - 'SAFE': successfully moved, detail is list of toggled bridges
            - 'TELEPORT': triggered teleport split, detail is (target_1, target_2)
            - 'MERGED': dual cubes re-merged into monolithic block, detail is toggled bridges
            - 'VICTORY': reached goal
            - 'FELL_VOID', 'FELL_FRAGILE': block falls, detail is cause coordinate
            - 'IGNORED': move cannot be performed in current state
        """
        if self.status != GameStatus.PLAYING:
            return ("IGNORED", self.block, None)

        # Snapshot for undo BEFORE applying the move
        pre_move_snapshot = self.snapshot_state()

        # Handle switch cube direction from AI solver
        if direction == Direction.SWITCH_CUBE:
            if getattr(self.block, "is_split", False):
                self.history.append(pre_move_snapshot)
                self.block = self.block.switch_active()
                return ("SAFE", self.block, None)
            return ("IGNORED", self.block, None)

        # Compute new geometric state
        next_block = self.block.roll(direction)

        # Evaluate against board
        outcome, cause_coord = self.board.evaluate_block_state(next_block)

        if outcome == "SAFE":
            self.history.append(pre_move_snapshot)
            self.block = next_block
            self.move_count += 1
            toggled_bridges = self.board.trigger_switches(next_block)

            # Check if dual cubes re-merge
            if getattr(next_block, "is_split", False):
                merged = next_block.check_merge()
                if merged is not None:
                    self.block = merged
                    merged_bridges = self.board.trigger_switches(merged)
                    toggled_bridges = list(set(toggled_bridges + merged_bridges))

                    # Check if merged block lands on goal or teleport
                    m_outcome, m_cause = self.board.evaluate_block_state(merged)
                    if m_outcome == "VICTORY":
                        self.status = GameStatus.VICTORY
                        return ("VICTORY", merged, None)
                    elif m_outcome == "TELEPORT":
                        tp = self.board.teleports.get(m_cause)
                        if tp:
                            self.block = SplitBlockState.from_targets(
                                tp.target_1, tp.target_2, tp.selected
                            )
                            return ("TELEPORT", self.block, (tp.target_1, tp.target_2))

                    return ("MERGED", merged, toggled_bridges)

            return ("SAFE", next_block, toggled_bridges)

        elif outcome == "TELEPORT":
            self.history.append(pre_move_snapshot)
            self.move_count += 1
            tp = self.board.teleports.get(cause_coord)
            if tp:
                self.block = SplitBlockState.from_targets(
                    tp.target_1, tp.target_2, tp.selected
                )
                return ("TELEPORT", self.block, (tp.target_1, tp.target_2))
            else:
                self.block = next_block
                return ("SAFE", next_block, None)

        elif outcome == "VICTORY":
            self.history.append(pre_move_snapshot)
            self.block = next_block
            self.move_count += 1
            self.status = GameStatus.VICTORY
            return ("VICTORY", next_block, None)

        else:
            # Fall outcomes
            self.status = GameStatus.FALLING
            self.move_count += 1
            return (outcome, next_block, cause_coord)

    def undo(self) -> bool:
        """Restores the previous turn state if available.

        Returns True if undo was successful.
        """
        if not self.history:
            return False

        prev_block, prev_bridges, prev_move_count = self.history.pop()
        self.block = prev_block

        # Restore bridge states
        for b_id, is_open in prev_bridges.items():
            bridge = self.board.bridges.get(b_id)
            if bridge:
                bridge.is_open = is_open
                self.board._sync_bridge_tiles(bridge)

        self.move_count = prev_move_count
        self.status = GameStatus.PLAYING
        return True
