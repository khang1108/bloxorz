"""3D Board visualizer implementing the minimalist design system with distinct architectural tiles."""

from typing import Dict, Tuple
from ursina import Entity, color, destroy, curve, invoke
from ursina.models.procedural.cylinder import Cylinder

from bloxorz.core.constants import TileType
from bloxorz.core.board import Board
from bloxorz.ui.theme import Palette
from bloxorz.config import CONFIG


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

        cfg = CONFIG.board
        tile_size = cfg.tile_size

        for (x, y), tile_type in board.base_tiles.items():
            pos_x = float(x)
            pos_z = -float(y)

            # Deep pedestal base reaching down into the void
            if tile_type != TileType.GOAL:
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.pedestal_y, pos_z),
                    scale=(tile_size - cfg.pedestal_inset, cfg.pedestal_height, tile_size - cfg.pedestal_inset),
                    color=c_pedestal,
                )

            if tile_type == TileType.NORMAL:
                # Top slab
                top_slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.normal_slab_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_normal,
                )
                # Inner recessed architectural plate
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.normal_inset_y, pos_z),
                    scale=(tile_size * cfg.normal_inset_ratio, 0.02, tile_size * cfg.normal_inset_ratio),
                    color=c_inset,
                )
                self.tile_entities[(x, y)] = top_slab

            elif tile_type == TileType.FRAGILE:
                # Thinner, vibrant terracotta slab with distinct warning groove
                slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.fragile_slab_y, pos_z),
                    scale=(tile_size, cfg.fragile_slab_height, tile_size),
                    color=c_fragile,
                )
                # Warning center notch / crossbar pattern
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.fragile_inset_y, pos_z),
                    scale=(tile_size * cfg.fragile_inset_ratio, 0.02, tile_size * cfg.fragile_inset_ratio),
                    color=c_fragile_inset,
                )
                self.tile_entities[(x, y)] = slab

            elif tile_type == TileType.GOAL:
                # Deep void well
                well = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.goal_well_y, pos_z),
                    scale=(tile_size, cfg.goal_well_height, tile_size),
                    color=c_goal_void,
                )
                # Luminous golden halo rim frame
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.goal_rim_y, pos_z),
                    scale=(tile_size + cfg.goal_rim_offset, cfg.goal_rim_height, tile_size + cfg.goal_rim_offset),
                    color=c_goal_rim,
                )
                # Glowing inner floor
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.goal_floor_y, pos_z),
                    scale=(tile_size * cfg.goal_floor_ratio, cfg.goal_floor_height, tile_size * cfg.goal_floor_ratio),
                    color=c_goal_glow,
                )
                self.goal_entity = well
                self.tile_entities[(x, y)] = well

            elif tile_type in (TileType.SWITCH_SOFT, TileType.SWITCH_HEAVY):
                # Standard tile foundation
                base_slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.normal_slab_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_normal,
                )
                self.tile_entities[(x, y)] = base_slab

                if tile_type == TileType.SWITCH_SOFT:
                    # Circular elevated disc with subtle glowing halo
                    plate = Entity(
                        parent=self.root,
                        model=Cylinder(resolution=24),
                        position=(pos_x, cfg.switch_soft_y, pos_z),
                        scale=(cfg.switch_soft_radius, cfg.switch_soft_height, cfg.switch_soft_radius),
                        color=c_switch_soft,
                    )
                    self.switch_entities[(x, y)] = plate
                else:
                    # Heavy switch: Intersecting cross bars
                    plate = Entity(
                        parent=self.root,
                        model='cube',
                        position=(pos_x, cfg.switch_heavy_y, pos_z),
                        scale=(cfg.switch_heavy_long, cfg.switch_heavy_height, cfg.switch_heavy_short),
                        color=c_switch_heavy,
                    )
                    Entity(
                        parent=self.root,
                        model='cube',
                        position=(pos_x, cfg.switch_heavy_y, pos_z),
                        scale=(cfg.switch_heavy_short, cfg.switch_heavy_height, cfg.switch_heavy_long),
                        color=c_switch_heavy,
                    )
                    self.switch_entities[(x, y)] = plate

            elif tile_type == TileType.TELEPORT:
                # Teleport/splitter slab with twin architectural cyan insets
                top_slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.normal_slab_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_normal,
                )
                c_teleport_accent = color.hex(Palette.TEXT_ACCENT.hex_code)
                inset_w = tile_size * 0.36
                inset_h = tile_size * 0.36
                offset_x = tile_size * 0.22
                # Dual square plates symbolizing block division
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x - offset_x, cfg.normal_inset_y, pos_z),
                    scale=(inset_w, 0.02, inset_h),
                    color=c_teleport_accent,
                )
                Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x + offset_x, cfg.normal_inset_y, pos_z),
                    scale=(inset_w, 0.02, inset_h),
                    color=c_teleport_accent,
                )
                self.tile_entities[(x, y)] = top_slab

        # Build bridge entities (slatted architectural planks)
        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                pos_x = float(bx)
                pos_z = -float(by)
                bridge_tile = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.bridge_open_y if group.is_open else cfg.bridge_closed_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_bridge,
                    visible=group.is_open,
                )
                self.bridge_entities[(bx, by)] = bridge_tile

    def update_bridges(self, board: Board):
        """Smoothly animates bridge states when switched."""
        cfg = CONFIG.board
        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                ent = self.bridge_entities.get((bx, by))
                if not ent:
                    continue
                if group.is_open:
                    ent.visible = True
                    ent.animate_y(cfg.bridge_open_y, duration=cfg.bridge_anim_duration, curve=curve.out_cubic)
                else:
                    def hide_after_sink(e=ent):
                        e.visible = False
                    ent.animate_y(cfg.bridge_closed_y, duration=cfg.bridge_anim_duration, curve=curve.in_cubic)
                    invoke(hide_after_sink, delay=cfg.bridge_anim_duration)

    def animate_switch_press(self, x: int, y: int):
        """Micro-animation depressing switch plate when stepped on."""
        cfg = CONFIG.board
        plate = self.switch_entities.get((x, y))
        if plate:
            orig_y = plate.y
            plate.animate_y(orig_y - cfg.switch_press_depth, duration=cfg.switch_press_down_time, curve=curve.out_sine)
            invoke(
                lambda: plate.animate_y(orig_y, duration=cfg.switch_press_up_time, curve=curve.out_sine),
                delay=cfg.switch_press_down_time + 0.02,
            )
