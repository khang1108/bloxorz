"""Level loading and parsing utilities for Bloxorz."""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

from bloxorz.core.constants import TileType, BlockOrientation
from bloxorz.core.block import BlockState
from bloxorz.core.board import Board, Switch, BridgeGroup, SwitchAction


CHAR_TO_TILE = {
    ".": TileType.VOID,
    " ": TileType.VOID,
    "1": TileType.NORMAL,
    "2": TileType.GOAL,
    "G": TileType.GOAL,
    "3": TileType.FRAGILE,
    "O": TileType.FRAGILE,
    "S": TileType.SWITCH_SOFT,
    "H": TileType.SWITCH_HEAVY,
    "B": TileType.BRIDGE_CLOSED,
}


def parse_level_data(data: Dict[str, Any]) -> Board:
    """Parses a dictionary into a Board instance."""
    tiles: Dict[Tuple[int, int], TileType] = {}
    goal_pos: Optional[Tuple[int, int]] = None

    # Parse layout lines if present
    layout = data.get("layout", [])
    for y, line in enumerate(layout):
        for x, char in enumerate(line):
            tile_type = CHAR_TO_TILE.get(char, TileType.VOID)
            if tile_type != TileType.VOID:
                tiles[(x, y)] = tile_type
            if tile_type == TileType.GOAL:
                goal_pos = (x, y)

    # Allow explicit tile overrides or dictionary coordinates
    explicit_tiles = data.get("tiles", {})
    for coord_str, t_val in explicit_tiles.items():
        coords = tuple(map(int, coord_str.split(",")))
        tiles[coords] = TileType(t_val)
        if TileType(t_val) == TileType.GOAL:
            goal_pos = coords

    # Parse bridges
    bridges: Dict[str, BridgeGroup] = {}
    for b_data in data.get("bridges", []):
        group_id = b_data["id"]
        bridge_coords = [tuple(c) for c in b_data["tiles"]]
        initially_open = b_data.get("initially_open", False)
        bridge = BridgeGroup(
            group_id=group_id,
            tiles=bridge_coords,
            initially_open=initially_open,
        )
        bridges[group_id] = bridge
        # Initialize bridge tile types
        for bc in bridge_coords:
            tiles[bc] = TileType.BRIDGE_OPEN if initially_open else TileType.BRIDGE_CLOSED

    # Parse switches
    switches: List[Switch] = []
    for s_data in data.get("switches", []):
        action_str = s_data.get("action", "TOGGLE").upper()
        action = SwitchAction[action_str]
        s_type = TileType.SWITCH_HEAVY if s_data.get("type") == "HEAVY" else TileType.SWITCH_SOFT
        switch = Switch(
            x=s_data["x"],
            y=s_data["y"],
            switch_type=s_type,
            target_bridge_ids=s_data.get("targets", []),
            action=action,
        )
        switches.append(switch)
        tiles[(switch.x, switch.y)] = s_type

    # Spawn configuration
    spawn_data = data.get("spawn", {"x": 0, "y": 0, "orientation": "STANDING"})
    ori = BlockOrientation[spawn_data.get("orientation", "STANDING").upper()]
    spawn_state = BlockState(spawn_data["x"], spawn_data["y"], ori)

    if goal_pos is None:
        goal_pos = (0, 0)

    level_name = data.get("name", "Stage")

    return Board(
        tiles=tiles,
        goal_pos=goal_pos,
        spawn_state=spawn_state,
        switches=switches,
        bridges=bridges,
        level_name=level_name,
    )


def load_level_from_file(file_path: Path) -> Board:
    """Reads a JSON file and constructs a Board."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return parse_level_data(data)


class LevelLoader:
    """Convenience class providing static methods to load and parse stages."""

    @staticmethod
    def load_json_level(file_path: Any) -> Board:
        """Loads a stage from a path string or Path object."""
        path_obj = Path(file_path)
        return load_level_from_file(path_obj)

    @staticmethod
    def parse(data: Dict[str, Any]) -> Board:
        """Parses a raw level data dictionary."""
        return parse_level_data(data)
