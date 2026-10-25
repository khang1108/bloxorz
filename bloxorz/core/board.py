"""Board representation and tile interactions for Bloxorz."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Tuple, Optional, Union
from bloxorz.core.constants import TileType, BlockOrientation
from bloxorz.core.block import BlockState
from bloxorz.core.split import Teleport, SplitBlockState


class SwitchAction(Enum):
    """Behavior of a switch when triggered."""
    TOGGLE = auto()
    OPEN = auto()
    CLOSE = auto()


@dataclass
class BridgeGroup:
    """A collection of bridge tiles controlled by switches."""
    group_id: str
    tiles: List[Tuple[int, int]]
    initially_open: bool = False
    is_open: bool = False

    def reset(self):
        self.is_open = self.initially_open

    def toggle(self):
        self.is_open = not self.is_open

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False


@dataclass
class Switch:
    """A board switch linked to one or more bridge groups."""
    x: int
    y: int
    switch_type: TileType  # SWITCH_SOFT or SWITCH_HEAVY
    target_bridge_ids: List[str]
    action: SwitchAction = SwitchAction.TOGGLE
    target_actions: Optional[Dict[str, SwitchAction]] = None


class Board:
    """Represents the puzzle grid, bridges, switches, and goal."""

    def __init__(
        self,
        tiles: Dict[Tuple[int, int], TileType],
        goal_pos: Tuple[int, int],
        spawn_state: BlockState,
        switches: Optional[List[Switch]] = None,
        bridges: Optional[Dict[str, BridgeGroup]] = None,
        teleports: Optional[List[Teleport]] = None,
        level_name: str = "Level",
        auto_reset: bool = True,
    ):
        self.base_tiles: Dict[Tuple[int, int], TileType] = dict(tiles)
        self.current_tiles: Dict[Tuple[int, int], TileType] = dict(tiles)
        self.goal_pos: Tuple[int, int] = goal_pos
        self.spawn_state: BlockState = spawn_state
        self.level_name: str = level_name

        self.switches: Dict[Tuple[int, int], Switch] = {
            (s.x, s.y): s for s in (switches or [])
        }
        self.bridges: Dict[str, BridgeGroup] = bridges or {}
        self.teleports: Dict[Tuple[int, int], Teleport] = {
            (t.x, t.y): t for t in (teleports or [])
        }

        # Precompute bounding box for camera placement
        all_coords = list(self.base_tiles.keys())
        if all_coords:
            self.min_x = min(x for x, y in all_coords)
            self.max_x = max(x for x, y in all_coords)
            self.min_y = min(y for x, y in all_coords)
            self.max_y = max(y for x, y in all_coords)
        else:
            self.min_x = self.max_x = self.min_y = self.max_y = 0

        if auto_reset:
            self.reset()

    @property
    def center_2d(self) -> Tuple[float, float]:
        """Calculates center of the board in 2D coordinates."""
        return ((self.min_x + self.max_x) / 2.0, (self.min_y + self.max_y) / 2.0)

    @property
    def has_teleports(self) -> bool:
        """Indicates if this stage contains teleport/splitter tiles."""
        return any(tile == TileType.TELEPORT for tile in self.base_tiles.values())

    def reset(self):
        """Resets dynamic board elements (bridges, fragile states)."""
        self.current_tiles = dict(self.base_tiles)
        for bridge in self.bridges.values():
            bridge.reset()
            self._sync_bridge_tiles(bridge)

    def get_bridge_state_key(self) -> Tuple[Tuple[str, bool], ...]:
        """Returns a hashable tuple of bridge states for solver visited sets."""
        return tuple(sorted((b_id, b.is_open) for b_id, b in self.bridges.items()))

    def clone(self) -> "Board":
        """Returns a deep copy of the board for solver state-space branching."""
        cloned_switches = [
            Switch(
                s.x,
                s.y,
                s.switch_type,
                list(s.target_bridge_ids),
                s.action,
                dict(s.target_actions) if s.target_actions else None,
            )
            for s in self.switches.values()
        ]
        cloned_bridges = {
            b_id: BridgeGroup(b.group_id, list(b.tiles), b.initially_open, b.is_open)
            for b_id, b in self.bridges.items()
        }
        cloned_teleports = [
            Teleport(t.x, t.y, t.target_1, t.target_2, t.selected)
            for t in self.teleports.values()
        ]
        new_board = Board(
            tiles=dict(self.base_tiles),
            goal_pos=self.goal_pos,
            spawn_state=self.spawn_state,
            switches=cloned_switches,
            bridges=cloned_bridges,
            teleports=cloned_teleports,
            level_name=self.level_name,
            auto_reset=False,
        )
        # Restore dynamic bridge states so clone preserves open/closed bridges
        for b_id, bridge in self.bridges.items():
            new_board.bridges[b_id].is_open = bridge.is_open
            new_board._sync_bridge_tiles(new_board.bridges[b_id])

        new_board.current_tiles = dict(self.current_tiles)
        return new_board

    def _sync_bridge_tiles(self, bridge: BridgeGroup):
        """Syncs bridge state into current_tiles."""
        for tile in bridge.tiles:
            if bridge.is_open:
                self.current_tiles[tile] = TileType.BRIDGE_OPEN
            else:
                self.current_tiles[tile] = TileType.BRIDGE_CLOSED

    def get_tile(self, x: int, y: int) -> TileType:
        """Returns the tile type at (x, y), default to VOID."""
        return self.current_tiles.get((x, y), TileType.VOID)

    def is_tile_walkable(self, tile: TileType) -> bool:
        """Determines if a tile supports the block."""
        return tile in (
            TileType.NORMAL,
            TileType.FRAGILE,
            TileType.SWITCH_SOFT,
            TileType.SWITCH_HEAVY,
            TileType.BRIDGE_OPEN,
            TileType.GOAL,
            TileType.TELEPORT,
        )

    def evaluate_block_state(
        self, block: Union[BlockState, SplitBlockState]
    ) -> Tuple[str, Optional[Tuple[int, int]]]:
        """Evaluates whether the block is safe, falls off, breaks fragile, or wins.

        Returns:
            (outcome, cause_coord):
            outcome is one of: 'SAFE', 'VICTORY', 'FELL_VOID', 'FELL_FRAGILE'
        """
        cells = block.occupied_cells

        # 1. Check if any cell is off the board or on a closed bridge
        for cell in cells:
            tile = self.get_tile(cell[0], cell[1])
            if not self.is_tile_walkable(tile):
                return ("FELL_VOID", cell)

        # 2. Split block rules
        if block.is_split:
            # A 1x1x1 unit cube cannot complete the stage alone; stepping into goal hole causes fall
            for cell in cells:
                tile = self.get_tile(cell[0], cell[1])
                if tile == TileType.GOAL:
                    return ("FELL_VOID", cell)
            # A 1x1x1 unit cube on a fragile tile is safe (does not collapse)
            return ("SAFE", None)

        # 3. Standard block standing tests
        if block.orientation == BlockOrientation.STANDING:
            cell = next(iter(cells))
            tile = self.get_tile(cell[0], cell[1])

            if tile == TileType.GOAL:
                return ("VICTORY", cell)
            if tile == TileType.FRAGILE:
                return ("FELL_FRAGILE", cell)

        # 4. Standard block lying tests: all occupied cells are walkable (including GOAL) -> SAFE
        return ("SAFE", None)

    def trigger_switches(self, block: Union[BlockState, SplitBlockState]) -> List[str]:
        """Triggers switches beneath the block if conditions are met.

        Returns list of modified bridge group IDs.
        """
        modified_bridges: List[str] = []
        cells = block.occupied_cells

        for cell in cells:
            switch = self.switches.get(cell)
            if not switch:
                continue

            can_trigger = False
            if switch.switch_type == TileType.SWITCH_SOFT:
                # Any contact triggers soft switch (including split 1x1x1 cube)
                can_trigger = True
            elif switch.switch_type == TileType.SWITCH_HEAVY:
                # Heavy switch only triggers when full block is standing upright
                can_trigger = not block.is_split and (block.orientation == BlockOrientation.STANDING)

            if can_trigger:
                for bridge_id in switch.target_bridge_ids:
                    bridge = self.bridges.get(bridge_id)
                    if bridge:
                        act = (
                            switch.target_actions.get(bridge_id, switch.action)
                            if switch.target_actions
                            else switch.action
                        )
                        if act == SwitchAction.TOGGLE:
                            bridge.toggle()
                        elif act == SwitchAction.OPEN:
                            bridge.open()
                        elif act == SwitchAction.CLOSE:
                            bridge.close()
                        self._sync_bridge_tiles(bridge)
                        modified_bridges.append(bridge_id)

        return modified_bridges

    def trigger_teleport(
        self, block: Union[BlockState, SplitBlockState]
    ) -> Union[BlockState, SplitBlockState]:
        """Splits and teleports the block if standing upright on a teleport switch."""
        if not block.is_split and block.orientation == BlockOrientation.STANDING:
            teleport = self.teleports.get((block.x, block.y))
            if teleport:
                return SplitBlockState(
                    cube1=teleport.target_1,
                    cube2=teleport.target_2,
                    active_cube=teleport.selected,
                )
        return block
