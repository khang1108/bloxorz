"""3D Board visualizer implementing the minimalist design system with distinct architectural tiles."""

from typing import Dict, Tuple
from ursina import Entity, color, destroy, curve, invoke

from bloxorz.core.constants import TileType
from bloxorz.core.board import Board
from bloxorz.ui.theme import Palette


class BoardView:
    """Renders the 3D grid with clear void gaps, distinct tile types, and subtle architectural grooves."""

    def __init__(self):
        self.root = Entity(name="board_root")
        self.tile_entities: Dict[Tuple[int, int], Entity] = {}
        self.switch_entities: Dict[Tuple[int, int], Entity] = {}
        self.bridge_entities: Dict[Tuple[int, int], Entity] = {}
        self.goal_entity: Entity = None

    def clear(self):
        """Destroys all visual entities on the board."""
        for child in list(self.root.children):
            destroy(child)
        self.tile_entities.clear()
        self.switch_entities.clear()
        self.bridge_entities.clear()
        self.goal_entity = None

    def build(self, board: Board):
        """Constructs 3D representations of all board elements with distinct styling and wider void gaps."""
        self.clear()

        # Design tokens
        c_normal = color.hex(Palette.TILE_NORMAL.hex_code)
        c_pedestal = color.hex(Palette.TILE_PEDESTAL.hex_code)
        c_inset = color.hex(Palette.TILE_INSET.hex_code)
        c_fragile = color.hex(Palette.TILE_FRAGILE.hex_code)
        c_fragile_inset = color.hex(Palette.TILE_FRAGILE_INSET.hex_code)
        c_switch_soft = color.hex(Palette.SWITCH_SOFT.hex_code)
        c_switch_heavy = color.hex(Palette.SWITCH_HEAVY.hex_code)
        c_bridge = color.hex(Palette.BRIDGE_ACTIVE.hex_code)
        c_goal_rim = color.hex(Palette.GOAL_RIM.hex_code)
        c_goal_void = color.hex(Palette.TILE_GOAL.hex_code)
        c_goal_glow = color.hex(Palette.GOAL_GLOW.hex_code)

        tile_size = 0.86  # Wide 0.14 gap exposing the void between tiles

        for (x, y), tile_type in board.base_tiles.items():
            pos_x = float(x)
            pos_z = -float(y)

            # Deep pedestal base reaching down into the void
            if tile_type != TileType.GOAL:
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.22, pos_z),
                    scale=(tile_size - 0.04, 0.32, tile_size - 0.04),
                    color=c_pedestal,
                )

            if tile_type == TileType.NORMAL:
                # Top slab
                top_slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.06, pos_z),
                    scale=(tile_size, 0.12, tile_size),
                    color=c_normal,
                )
                # Inner recessed architectural plate
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.005, pos_z),
                    scale=(tile_size * 0.72, 0.02, tile_size * 0.72),
                    color=c_inset,
                )
                self.tile_entities[(x, y)] = top_slab

            elif tile_type == TileType.FRAGILE:
                # Thinner, vibrant terracotta slab with distinct warning groove
                slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.04, pos_z),
                    scale=(tile_size, 0.08, tile_size),
                    color=c_fragile,
                )
                # Warning center notch / crossbar pattern
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, 0.005, pos_z),
                    scale=(tile_size * 0.70, 0.02, tile_size * 0.70),
                    color=c_fragile_inset,
                )
                self.tile_entities[(x, y)] = slab

            elif tile_type == TileType.GOAL:
                # Deep void well
                well = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.55, pos_z),
                    scale=(tile_size, 0.90, tile_size),
                    color=c_goal_void,
                )
                # Luminous golden halo rim frame
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.02, pos_z),
                    scale=(tile_size + 0.04, 0.04, tile_size + 0.04),
                    color=c_goal_rim,
                )
                # Glowing inner floor
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.98, pos_z),
                    scale=(tile_size * 0.75, 0.04, tile_size * 0.75),
                    color=c_goal_glow,
                )
                self.goal_entity = well
                self.tile_entities[(x, y)] = well

            elif tile_type in (TileType.SWITCH_SOFT, TileType.SWITCH_HEAVY):
                # Standard tile foundation
                base_slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.06, pos_z),
                    scale=(tile_size, 0.12, tile_size),
                    color=c_normal,
                )
                self.tile_entities[(x, y)] = base_slab

                if tile_type == TileType.SWITCH_SOFT:
                    # Circular elevated disc with subtle glowing halo
                    plate = Entity(
                        parent=self.root,
                        model='cylinder',
                        position=(pos_x, 0.04, pos_z),
                        scale=(0.48, 0.08, 0.48),
                        color=c_switch_soft,
                    )
                    self.switch_entities[(x, y)] = plate
                else:
                    # Heavy switch: Intersecting cross bars
                    plate = Entity(
                        parent=self.root,
                        model='cube',
                        position=(pos_x, 0.04, pos_z),
                        scale=(0.54, 0.08, 0.18),
                        color=c_switch_heavy,
                    )
                    Entity(
                        parent=self.root,
                        model='cube',
                        position=(pos_x, 0.04, pos_z),
                        scale=(0.18, 0.08, 0.54),
                        color=c_switch_heavy,
                    )
                    self.switch_entities[(x, y)] = plate

        # Build bridge entities (slatted architectural planks)
        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                pos_x = float(bx)
                pos_z = -float(by)
                bridge_tile = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, -0.06 if group.is_open else -1.5, pos_z),
                    scale=(tile_size, 0.12, tile_size),
                    color=c_bridge,
                    visible=group.is_open,
                )
                self.bridge_entities[(bx, by)] = bridge_tile

    def update_bridges(self, board: Board):
        """Smoothly animates bridge states when switched."""
        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                ent = self.bridge_entities.get((bx, by))
                if not ent:
                    continue
                if group.is_open:
                    ent.visible = True
                    ent.animate_y(-0.06, duration=0.25, curve=curve.out_cubic)
                else:
                    def hide_after_sink(e=ent):
                        e.visible = False
                    ent.animate_y(-1.5, duration=0.25, curve=curve.in_cubic)
                    invoke(hide_after_sink, delay=0.25)

    def animate_switch_press(self, x: int, y: int):
        """Micro-animation depressing switch plate when stepped on."""
        plate = self.switch_entities.get((x, y))
        if plate:
            orig_y = plate.y
            plate.animate_y(orig_y - 0.04, duration=0.08, curve=curve.out_sine)
            invoke(lambda: plate.animate_y(orig_y, duration=0.12, curve=curve.out_sine), delay=0.1)
