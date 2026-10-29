"""An architectural, north-up board schematic with live game-state overlays."""

import math
from typing import Dict, Optional, Tuple

from ursina import Entity, Text, camera, color, destroy, time, window

from bloxorz.core.block import BaseBlockState
from bloxorz.core.board import Board
from bloxorz.core.constants import TileType
from bloxorz.ui.minimap_marker import BlockMarker, corner_brackets
from bloxorz.ui.neon import NeonPanel, chamfered_mesh
from bloxorz.ui.theme import NeonHUD


def _plate(parent: Entity, size: tuple, tint: str, position: tuple = (0, 0), z: float = 0) -> Entity:
    return Entity(parent=parent, model=chamfered_mesh(*size, cut=min(.12, min(size) / 3)),
                  scale=size, position=(*position, z), color=color.hex(tint), double_sided=True)


def _destroy_tree(entity: Entity) -> None:
    # Ursina.destroy removes the parent NodePath but does not unregister descendants.
    for child in list(entity.children):
        _destroy_tree(child)
    destroy(entity)


class MiniMap:
    """Layered tiles, explicit switch glyphs, and a continuous block silhouette."""

    WIDTH = .36
    HEIGHT = .275
    GRID_WIDTH = .312
    GRID_HEIGHT = .180
    TILE_COLORS = {
        TileType.NORMAL: "#2B4358",
        TileType.GOAL: "#080C14",
        TileType.FRAGILE: "#A55534",
        TileType.SWITCH_SOFT: "#263E50",
        TileType.SWITCH_HEAVY: "#263E50",
        TileType.BRIDGE_CLOSED: "#0B1320",
        TileType.BRIDGE_OPEN: "#24465B",
        TileType.TELEPORT: "#26384E",
    }

    def __init__(self, parent: Optional[Entity] = None) -> None:
        self.root = Entity(parent=parent if parent is not None else camera.ui, name="minimap", z=-.1)
        self.root.update = self._update
        self._elapsed = 0.
        self._update_position()
        self.frame = NeonPanel(parent=self.root, width=self.WIDTH, height=self.HEIGHT, accent=NeonHUD.CYAN)
        Text(parent=self.root, text="TACTICAL / LIVE", position=(-.153, .112), origin=(-.5, 0),
             scale=.63, color=color.hex(NeonHUD.CYAN), z=-.02)
        self.grid_root = Entity(parent=self.root, y=.005)
        self._substrate = Entity(parent=self.grid_root, model="quad", color=color.hex("#050B15"), z=.02)
        self._bounds = Entity(parent=self.grid_root,
                              color=color.hex(NeonHUD.CYAN), alpha=.35, z=.015)
        self.tiles_root = Entity(parent=self.grid_root)
        self.tile_entities: Dict[Tuple[int, int], Entity] = {}
        self._bridge_symbols = {}
        self._goal_beacons = []
        self.block_markers = [BlockMarker(self.grid_root), BlockMarker(self.grid_root)]
        for x, label, tint in [(-.145, "YOU", NeonHUD.TEXT), (-.025, "GOAL", NeonHUD.AMBER)]:
            badge = Entity(parent=self.root, position=(x, -.113, -.02), scale=(.007, .007, 1))
            Entity(parent=badge, model="quad", color=color.hex(tint))
            Entity(parent=badge, model="quad", scale=.62, z=-.002,
                   color=color.hex(NeonHUD.TEXT if label == "YOU" else "#0A1020"))
            if label == "YOU":
                Entity(parent=badge, model=corner_brackets(1.4, 1.4),
                       color=color.hex(NeonHUD.CYAN), z=-.004)
            Text(parent=self.root, text=label, position=(x + .009, -.113), origin=(-.5, 0),
                 scale=.55, color=color.hex(NeonHUD.MUTED), z=-.02)
        self.cell_size = .02
        self._board: Optional[Board] = None
        self._bridge_key = None
        self._center = (0., 0.)

    def _update_position(self) -> None:
        self.root.position = (window.aspect_ratio / 2 - .215, -.125, -.1)

    def _update(self) -> None:
        self._update_position()
        dt = max(0., getattr(time, "dt", 0.))
        self._elapsed += dt
        breath = math.sin(self._elapsed * 2.)
        for glow, rim in self._goal_beacons:
            glow.alpha = .12 + .04 * breath
            rim.alpha = .85 + .10 * breath
        for marker in self.block_markers:
            marker.tick(dt)

    def project(self, x: float, y: float) -> Tuple[float, float]:
        """Keep square map cells and a north-up orientation."""
        return ((x - self._center[0]) * self.cell_size, -(y - self._center[1]) * self.cell_size)

    def _build(self, board: Board) -> None:
        for entity in list(self.tiles_root.children):
            _destroy_tree(entity)
        self.tile_entities.clear()
        self._bridge_symbols.clear()
        self._goal_beacons.clear()
        self._board = board
        self._bridge_key = None
        self._center = board.center_2d
        columns = max(1, board.max_x - board.min_x + 1)
        rows = max(1, board.max_y - board.min_y + 1)
        self.cell_size = min((self.GRID_WIDTH - .018) / columns, (self.GRID_HEIGHT - .018) / rows)
        self._substrate.scale = (columns * self.cell_size + .014, rows * self.cell_size + .014, 1)
        self._bounds.model = corner_brackets(columns * self.cell_size + .018,
                                             rows * self.cell_size + .018, arm_length=.016)
        for (x, y), tile_type in board.current_tiles.items():
            if tile_type == TileType.VOID:
                continue
            px, py = self.project(x, y)
            detail = Entity(parent=self.tiles_root, position=(px, py, 0),
                            scale=(self.cell_size, self.cell_size, 1))
            _plate(detail, (.96, .96), "#142A3B", (0, -.045), .008)
            surface = _plate(detail, (.82, .82), self.TILE_COLORS[tile_type])
            self.tile_entities[(x, y)] = surface
            if tile_type not in (TileType.GOAL, TileType.BRIDGE_CLOSED):
                Entity(parent=detail, model="quad", position=(0, .365, -.002),
                       scale=(.58, .045), color=color.hex("#7495A8"), alpha=.42)
            self._add_symbol(detail, tile_type)

    def _add_symbol(self, parent: Entity, tile_type: TileType) -> None:
        if tile_type == TileType.GOAL:
            glow = _plate(parent, (1.04, 1.04), NeonHUD.AMBER, z=.003)
            glow.alpha = .12
            rim = _plate(parent, (.84, .84), NeonHUD.AMBER, z=-.003)
            _plate(parent, (.63, .63), "#03060C", z=-.007)
            _plate(parent, (.39, .39), "#111424", (0, -.07), -.009)
            self._goal_beacons.append((glow, rim))
        elif tile_type == TileType.SWITCH_SOFT:
            Entity(parent=parent, model="circle", scale=(.53, .53), color=color.hex("#5FE3B0"), z=-.006)
            Entity(parent=parent, model="circle", scale=(.24, .24), color=color.hex("#0C2426"), z=-.008)
            Entity(parent=parent, model="circle", scale=(.15, .15), color=color.hex("#A7F3D0"), z=-.010)
        elif tile_type == TileType.SWITCH_HEAVY:
            for angle in (-45, 45):
                Entity(parent=parent, model="quad", scale=(.55, .12), rotation_z=angle,
                       color=color.hex("#FF718C"), z=-.006)
        elif tile_type == TileType.TELEPORT:
            for x in (-.18, .18):
                _plate(parent, (.24, .48), NeonHUD.VIOLET, (x, 0), -.006)
                _plate(parent, (.11, .27), "#18142C", (x, 0), -.008)
        elif tile_type == TileType.FRAGILE:
            for x in (-.16, .16):
                Entity(parent=parent, model="quad", scale=(.07, .42), position=(x, 0, -.006),
                       rotation_z=-30, color=color.hex("#FFB578"))
        elif tile_type in (TileType.BRIDGE_CLOSED, TileType.BRIDGE_OPEN):
            closed = Entity(parent=parent)
            _plate(closed, (.88, .88), "#506578", z=-.003)
            _plate(closed, (.73, .73), "#070D16", z=-.005)
            for x in (-.24, 0, .24):
                Entity(parent=closed, model="quad", position=(x, 0, -.008),
                       scale=(.13, .06), color=color.hex("#7390A4"))
            opened = Entity(parent=parent)
            for y in (-.27, .27):
                Entity(parent=opened, model="quad", y=y, z=-.006,
                       scale=(.74, .055), color=color.hex(NeonHUD.CYAN))
            self._bridge_symbols[parent] = (closed, opened)

    def sync(self, board: Board, block: BaseBlockState) -> None:
        """Update bridge layers and actor transforms without rebuilding geometry."""
        if board is not self._board:
            self._build(board)
        bridge_key = board.get_bridge_state_key()
        if bridge_key != self._bridge_key:
            for coordinate, surface in self.tile_entities.items():
                tile_type = board.get_tile(*coordinate)
                surface.color = color.hex(self.TILE_COLORS[tile_type])
                symbols = self._bridge_symbols.get(surface.parent)
                if symbols:
                    symbols[0].enabled = tile_type == TileType.BRIDGE_CLOSED
                    symbols[1].enabled = tile_type == TileType.BRIDGE_OPEN
            self._bridge_key = bridge_key

        if block.is_split:
            for index, coordinates in enumerate((block.cube1, block.cube2)):
                marker = self.block_markers[index]
                marker.enabled = True
                marker.configure(self.project(*coordinates), self.cell_size, (1, 1), index == block.active_index)
        else:
            cells = block.occupied_cells
            xs, ys = [x for x, _ in cells], [y for _, y in cells]
            footprint = (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
            center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
            self.block_markers[0].enabled = True
            self.block_markers[0].configure(self.project(*center), self.cell_size, footprint, True)
            self.block_markers[1].enabled = False

    def set_visible(self, visible: bool) -> None:
        self.root.enabled = visible
