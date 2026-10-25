from typing import List, Tuple, Dict, Any, Union
from bloxorz.core.constants import Direction, GameStatus
from bloxorz.core.block import BlockState
from bloxorz.core.board import Board
from bloxorz.core.split import SplitBlockState


class Game:
    """High-level game controller managing a single level session."""

    def __init__(self, board: Board):
        self.board: Board = board
        self.block: Union[BlockState, SplitBlockState] = board.spawn_state
        self.move_count: int = 0
        self.status: GameStatus = GameStatus.PLAYING

        # History stack for full Undo support: (block_state, bridge_states_dict)
        self.history: List[Tuple[Union[BlockState, SplitBlockState], Dict[str, bool]]] = []

    def restart(self):
        """Restarts the level to its initial spawn configuration."""
        self.board.reset()
        self.block = self.board.spawn_state
        self.move_count = 0
        self.status = GameStatus.PLAYING
        self.history.clear()

    def snapshot_state(self) -> Tuple[Union[BlockState, SplitBlockState], Dict[str, bool]]:
        """Takes a snapshot of current block and bridge configurations."""
        bridge_states = {
            b_id: bridge.is_open for b_id, bridge in self.board.bridges.items()
        }
        return (self.block, bridge_states)

    def roll(self, direction: Direction) -> Tuple[str, Union[BlockState, SplitBlockState], Any]:
        """Attempts to roll the block in the given direction.

        Returns:
            (outcome, new_block_state, detail)
            where outcome is one of:
            - 'SAFE': successfully moved, detail is list of toggled bridges
            - 'VICTORY': reached goal
            - 'FELL_VOID', 'FELL_FRAGILE': block falls, detail is cause coordinate
            - 'IGNORED': move cannot be performed in current state
        """
        if self.status != GameStatus.PLAYING:
            return ("IGNORED", self.block, None)

        # Snapshot for undo BEFORE applying the move
        pre_move_snapshot = self.snapshot_state()

        # Compute new geometric state
        next_block = self.block.roll(direction)

        # Evaluate against board
        outcome, cause_coord = self.board.evaluate_block_state(next_block)

        if outcome == "SAFE":
            # Apply move
            self.history.append(pre_move_snapshot)
            if direction != Direction.SWITCH_CUBE:
                self.move_count += 1
            toggled_bridges = self.board.trigger_switches(next_block)
            next_block = self.board.trigger_teleport(next_block)
            self.block = next_block
            return ("SAFE", next_block, toggled_bridges)

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

        prev_block, prev_bridges = self.history.pop()
        self.block = prev_block

        # Restore bridge states
        for b_id, is_open in prev_bridges.items():
            bridge = self.board.bridges.get(b_id)
            if bridge:
                bridge.is_open = is_open
                self.board._sync_bridge_tiles(bridge)

        self.move_count = max(0, self.move_count - 1)
        self.status = GameStatus.PLAYING
        return True
