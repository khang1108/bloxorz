"""3D Board visualizer implementing the minimalist design system with distinct architectural tiles."""

import math
from typing import Dict, Optional, Tuple
from ursina import Entity, Mesh, Vec3, color, destroy, curve, invoke, time
from ursina.models.procedural.cylinder import Cylinder
from ursina.shaders import unlit_shader

from bloxorz.core.constants import TileType
from bloxorz.core.board import Board
from bloxorz.ui.theme import Palette
from bloxorz.config import CONFIG


class _PulseRing(Entity):
    """Blue neon ring that softly expands and fades around a soft switch."""

    def __init__(self, parent, position, radius: float, accent) -> None:
        segments = 32
        vertices = []
        triangles = []
        inner_radius = radius * 0.84
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            cosine, sine = math.cos(angle), math.sin(angle)
            vertices.extend(
                (
                    (cosine * radius, 0, sine * radius),
                    (cosine * inner_radius, 0, sine * inner_radius),
                )
            )
        for index in range(segments):
            outer = index * 2
            inner = outer + 1
            next_outer = ((index + 1) % segments) * 2
            next_inner = next_outer + 1
            triangles.extend(
                (
                    (outer, next_outer, next_inner),
                    (outer, next_inner, inner),
                )
            )
        super().__init__(
            parent=parent,
            name="soft_switch_pulse",
            model=Mesh(vertices=vertices, triangles=triangles, static=True),
            position=position,
            shader=unlit_shader,
            color=color.rgba(accent.r, accent.g, accent.b, 0.7),
            transparency=True,
            double_sided=True,
        )
        self._accent = accent
        self._elapsed = 0.0

    def update(self) -> None:
        self._elapsed += max(0.0, time.dt)
        wave = (math.sin(self._elapsed * 5.0) + 1.0) / 2.0
        scale = 0.9 + wave * 0.2
        self.scale = (scale, 1, scale)
        self.color = color.rgba(
            self._accent.r,
            self._accent.g,
            self._accent.b,
            0.35 + wave * 0.55,
        )


class _TeleportOrbit(Entity):
    """Rotating two-node teleport symbol joined by a neon connector."""

    def __init__(self, parent: Entity, position, accent) -> None:
        super().__init__(
            parent=parent,
            name="teleport_orbit",
            position=position,
            shader=unlit_shader,
            color=color.white,
        )
        self._accent = accent
        self._elapsed = 0.0
        radius = 0.105
        segments = 24
        Entity(
            parent=self,
            name="teleport_connector",
            model="cube",
            position=(0, 0.004, 0),
            scale=(0.30, 0.018, 0.025),
            color=accent,
        )
        for x in (-0.19, 0.19):
            vertices = [(0.0, 0.0, 0.0)]
            for index in range(segments):
                angle = math.tau * index / segments
                vertices.append(
                    (math.cos(angle) * radius, 0, math.sin(angle) * radius)
                )
            disk_mesh = Mesh(
                vertices=vertices,
                triangles=[
                    (0, index + 1, (index + 1) % segments + 1)
                    for index in range(segments)
                ],
                static=True,
            )
            Entity(
                parent=self,
                name="teleport_node",
                model=disk_mesh,
                position=(x, 0.016, 0),
                color=accent,
                shader=unlit_shader,
                double_sided=True,
            )

    def update(self) -> None:
        self._elapsed += max(0.0, time.dt)
        self.rotation_y = (self._elapsed * 70.0) % 360


class _HeavySwitch(Entity):
    """Red heavy switch cross with a repeating warning blink."""

    def __init__(self, parent: Entity, position, config) -> None:
        super().__init__(
            parent=parent,
            name="heavy_switch_pulse",
            position=position,
        )
        self._elapsed = 0.0
        self._bars = []
        for rotation in (45, -45):
            self._bars.append(
                Entity(
                    parent=self,
                    model="cube",
                    rotation_y=rotation,
                    scale=(
                        config.switch_heavy_long,
                        config.switch_heavy_height,
                        config.switch_heavy_short,
                    ),
                    shader=unlit_shader,
                    color=color.hex(Palette.SWITCH_HEAVY.hex_code),
                )
            )

    def update(self) -> None:
        self._elapsed += max(0.0, time.dt)
        pulse = (math.sin(self._elapsed * 6.0) + 1.0) / 2.0
        brightness = 0.38 + pulse * 0.62
        base = color.hex(Palette.SWITCH_HEAVY.hex_code)
        for bar in self._bars:
            bar.color = color.rgb(
                base.r * brightness,
                base.g * brightness,
                base.b * brightness,
            )


class _LandingFlash(Entity):
    """Brief translucent highlight that fades over a landed-on tile."""

    DURATION = 0.38

    def __init__(self, parent: Entity, x: float, z: float, tile_size: float) -> None:
        half = tile_size / 2
        super().__init__(
            parent=parent,
            name="tile_landing_flash",
            model=Mesh(
                vertices=[
                    (-half, 0, -half),
                    (half, 0, -half),
                    (half, 0, half),
                    (-half, 0, half),
                ],
                triangles=[(0, 1, 2), (0, 2, 3)],
                static=True,
            ),
            position=(x, 0.018, z),
            shader=unlit_shader,
            color=color.rgba(1.0, 0.96, 0.68, 0.85),
            transparency=True,
            double_sided=True,
        )
        self._elapsed = 0.0

    def update(self) -> None:
        self._elapsed += max(0.0, time.dt)
        progress = self._elapsed / self.DURATION
        if progress >= 1:
            destroy(self)
            return
        alpha = 0.85 * (1 - progress) ** 1.5
        self.color = color.rgba(1.0, 0.96, 0.68, alpha)


def _column_mesh(width: float, height: float, opacity: float) -> Mesh:
    gold = color.hex(Palette.GOAL_BEAM.hex_code)
    white = color.hex("#FFFDF0")
    half = width / 2
    faces = (
        ((-half, -height / 2, -half), (half, -height / 2, -half),
         (half, height / 2, -half), (-half, height / 2, -half)),
        ((half, -height / 2, half), (-half, -height / 2, half),
         (-half, height / 2, half), (half, height / 2, half)),
        ((-half, -height / 2, half), (-half, -height / 2, -half),
         (-half, height / 2, -half), (-half, height / 2, half)),
        ((half, -height / 2, -half), (half, -height / 2, half),
         (half, height / 2, half), (half, height / 2, -half)),
        ((-half, height / 2, -half), (half, height / 2, -half),
         (half, height / 2, half), (-half, height / 2, half)),
        ((-half, -height / 2, half), (half, -height / 2, half),
         (half, -height / 2, -half), (-half, -height / 2, -half)),
    )
    vertices = []
    triangles = []
    colors = []
    for face in faces:
        start = len(vertices)
        vertices.extend(face)
        triangles.extend(((start, start + 1, start + 2), (start, start + 2, start + 3)))
        for vertex in face:
            blend = (vertex[1] / height) + 0.5
            channels = tuple(
                gold_channel * (1 - blend) + white_channel * blend
                for gold_channel, white_channel in zip(
                    (gold.r, gold.g, gold.b),
                    (white.r, white.g, white.b),
                )
            )
            colors.append(color.rgba(*channels, opacity))
    return Mesh(vertices=vertices, triangles=triangles, colors=colors, static=True)


def _beacon_tip_mesh(width: float, height: float) -> Mesh:
    gold = color.hex(Palette.GOAL_BEAM.hex_code)
    white = color.hex("#FFFDF0")
    half = width / 2
    vertices = [
        (-half, 0, -half),
        (half, 0, -half),
        (half, 0, half),
        (-half, 0, half),
        (0, height, 0),
    ]
    triangles = [
        (0, 1, 4),
        (1, 2, 4),
        (2, 3, 4),
        (3, 0, 4),
        (0, 2, 1),
        (0, 3, 2),
    ]
    colors = [
        color.rgb(gold.r, gold.g, gold.b),
        color.rgb(gold.r, gold.g, gold.b),
        color.rgb(gold.r, gold.g, gold.b),
        color.rgb(gold.r, gold.g, gold.b),
        color.rgb(white.r, white.g, white.b),
    ]
    return Mesh(vertices=vertices, triangles=triangles, colors=colors, static=True)


class _GoalBeacon(Entity):
    """Two-cell golden beacon with continuously radiating light particles."""

    HEIGHT = 2.0
    TIP_HEIGHT = 0.3
    PARTICLE_COUNT = 18
    PARTICLE_LIFETIME = 2.2

    def __init__(self, parent: Entity, x: float, z: float) -> None:
        super().__init__(
            parent=parent,
            name="goal_beacon",
            position=(x, self.HEIGHT / 2 + 0.01, z),
        )
        glow_width = 0.38
        Entity(
            parent=self,
            name="goal_beacon_glow",
            model=_column_mesh(glow_width, self.HEIGHT - self.TIP_HEIGHT, 0.22),
            position=(0, -self.TIP_HEIGHT / 2, 0),
            shader=unlit_shader,
            color=color.white,
            transparency=True,
            double_sided=True,
        )
        Entity(
            parent=self,
            name="goal_beacon_core",
            model=_column_mesh(0.13, self.HEIGHT - self.TIP_HEIGHT, 1.0),
            position=(0, -self.TIP_HEIGHT / 2, 0),
            shader=unlit_shader,
            color=color.white,
            double_sided=True,
        )
        Entity(
            parent=self,
            name="goal_beacon_tip_glow",
            model=_beacon_tip_mesh(glow_width, self.TIP_HEIGHT),
            position=(0, self.HEIGHT / 2 - self.TIP_HEIGHT, 0),
            shader=unlit_shader,
            color=color.rgba(1, 1, 1, 0.24),
            transparency=True,
            double_sided=True,
        )
        Entity(
            parent=self,
            name="goal_beacon_tip",
            model=_beacon_tip_mesh(0.13, self.TIP_HEIGHT),
            position=(0, self.HEIGHT / 2 - self.TIP_HEIGHT, 0),
            shader=unlit_shader,
            color=color.white,
            double_sided=True,
        )
        self._elapsed = 0.0
        self._particles = []
        self._gold = color.hex(Palette.GOAL_BEAM.hex_code)
        for index in range(self.PARTICLE_COUNT):
            particle = Entity(
                parent=self,
                name="goal_particle",
                model="sphere",
                shader=unlit_shader,
                color=color.rgba(self._gold.r, self._gold.g, self._gold.b, 0),
                scale=0.035,
                transparency=True,
            )
            self._particles.append(particle)

    def update(self) -> None:
        self._elapsed += max(0.0, time.dt)
        for index, particle in enumerate(self._particles):
            phase = (self._elapsed / self.PARTICLE_LIFETIME + index / self.PARTICLE_COUNT) % 1
            angle = index * 2.399 + phase * math.tau * 0.3
            radius = 0.08 + phase * 0.72
            origin_y = 0.08 + (index % 5) * 0.25
            particle.position = Vec3(
                math.cos(angle) * radius,
                origin_y + phase * 0.48,
                math.sin(angle) * radius,
            )
            alpha = min(1.0, phase * 4) * (1 - phase)
            particle.color = color.rgba(
                self._gold.r,
                self._gold.g,
                self._gold.b,
                alpha,
            )


class BoardView:
    """Renders the 3D grid with clear void gaps, distinct tile types, and subtle architectural grooves."""

    def __init__(self):
        self.root = Entity(name="board_root")
        self.tile_entities: Dict[Tuple[int, int], Entity] = {}
        self.switch_entities: Dict[Tuple[int, int], Entity] = {}
        self.bridge_entities: Dict[Tuple[int, int], Entity] = {}
        self.goal_entity: Entity = None

    def _add_top_surface(
        self,
        x: float,
        z: float,
        y: float,
        tile_size: float,
        gradient: Tuple[str, str, str, str],
        border_hex: str,
        border_width_factor: float = 0.045,
        parent: Optional[Entity] = None,
    ) -> None:
        half = tile_size / 2
        vertices = [
            (-half, 0, -half),
            (half, 0, -half),
            (half, 0, half),
            (-half, 0, half),
        ]
        Entity(
            parent=parent if parent is not None else self.root,
            name="tile_gradient_surface",
            model=Mesh(
                vertices=vertices,
                triangles=[(0, 1, 2), (0, 2, 3)],
                colors=[color.hex(value) for value in gradient],
                static=True,
            ),
            position=(x, y, z),
            shader=unlit_shader,
            double_sided=True,
        )

        border_width = tile_size * border_width_factor
        border_vertices = []
        border_triangles = []
        for start, end in (
            ((-half, -half), (half, -half)),
            ((half, -half), (half, half)),
            ((half, half), (-half, half)),
            ((-half, half), (-half, -half)),
        ):
            base = len(border_vertices)
            if start[0] == end[0]:
                border_vertices.extend(
                    (
                        (start[0] - border_width / 2, 0, start[1]),
                        (start[0] + border_width / 2, 0, start[1]),
                        (end[0] + border_width / 2, 0, end[1]),
                        (end[0] - border_width / 2, 0, end[1]),
                    )
                )
            else:
                border_vertices.extend(
                    (
                        (start[0], 0, start[1] - border_width / 2),
                        (start[0], 0, start[1] + border_width / 2),
                        (end[0], 0, end[1] + border_width / 2),
                        (end[0], 0, end[1] - border_width / 2),
                    )
                )
            border_triangles.extend(((base, base + 1, base + 2), (base, base + 2, base + 3)))
        border_color = color.hex(border_hex)
        Entity(
            parent=parent if parent is not None else self.root,
            name="tile_neon_border",
            model=Mesh(
                vertices=border_vertices,
                triangles=border_triangles,
                colors=[
                    color.rgba(border_color.r, border_color.g, border_color.b, 0.98)
                ] * len(border_vertices),
                static=True,
            ),
            position=(x, y + 0.003, z),
            shader=unlit_shader,
            transparency=True,
            double_sided=True,
        )

    @staticmethod
    def _append_crack_segment(
        vertices,
        triangles,
        x: float,
        z: float,
        start: Tuple[float, float],
        end: Tuple[float, float],
        width: float,
        y: float,
    ) -> None:
        dx = end[0] - start[0]
        dz = end[1] - start[1]
        length = math.hypot(dx, dz)
        if length == 0:
            return
        offset_x = -dz / length * width / 2
        offset_z = dx / length * width / 2
        first = (x + start[0] + offset_x, y, z + start[1] + offset_z)
        second = (x + start[0] - offset_x, y, z + start[1] - offset_z)
        third = (x + end[0] - offset_x, y, z + end[1] - offset_z)
        fourth = (x + end[0] + offset_x, y, z + end[1] + offset_z)
        base = len(vertices)
        vertices.extend((first, second, third, fourth))
        triangles.extend(((base, base + 1, base + 2), (base, base + 2, base + 3)))

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
        crack_vertices = []
        crack_triangles = []
        crack_paths = (
            ((-0.25, -0.20), (0.0, 0.0)),
            ((0.0, 0.0), (0.18, 0.28)),
            ((0.0, 0.0), (0.27, -0.11)),
            ((-0.15, 0.18), (0.05, 0.29)),
            ((0.12, -0.02), (0.25, -0.28)),
            ((-0.05, -0.05), (-0.25, -0.27)),
        )

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
                top_slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.normal_slab_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_normal,
                )
                self._add_top_surface(
                    pos_x, pos_z, 0.002, tile_size,
                    ("#070B13", "#0D1422", "#080D18", "#101827"),
                    Palette.TILE_BORDER.hex_code,
                    border_width_factor=0.065,
                )
                self.tile_entities[(x, y)] = top_slab

            elif tile_type == TileType.FRAGILE:
                slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.fragile_slab_y, pos_z),
                    scale=(tile_size, cfg.fragile_slab_height, tile_size),
                    color=c_fragile,
                )
                self._add_top_surface(
                    pos_x, pos_z, 0.002, tile_size,
                    ("#482006", "#8A3B08", "#5A2608", "#A64A0A"),
                    Palette.TILE_FRAGILE.hex_code,
                )
                for start, end in crack_paths:
                    self._append_crack_segment(
                        crack_vertices,
                        crack_triangles,
                        pos_x,
                        pos_z,
                        (start[0] * tile_size, start[1] * tile_size),
                        (end[0] * tile_size, end[1] * tile_size),
                        width=0.014,
                        y=0.014,
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
                _GoalBeacon(self.root, pos_x, pos_z)

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
                is_soft = tile_type == TileType.SWITCH_SOFT
                self._add_top_surface(
                    pos_x, pos_z, 0.002, tile_size,
                    (
                        ("#07172A", "#092445", "#06172A", "#0C1C32")
                        if is_soft
                        else ("#210A12", "#3B0B16", "#230913", "#44101A")
                    ),
                    (Palette.SWITCH_SOFT if is_soft else Palette.SWITCH_HEAVY).hex_code,
                )

                if tile_type == TileType.SWITCH_SOFT:
                    Entity(
                        parent=self.root,
                        model=Cylinder(resolution=24),
                        position=(pos_x, cfg.switch_soft_y - 0.02, pos_z),
                        scale=(cfg.switch_soft_radius + 0.08, 0.04, cfg.switch_soft_radius + 0.08),
                        color=c_inset,
                    )
                    plate = Entity(
                        parent=self.root,
                        model=Cylinder(resolution=24),
                        position=(pos_x, cfg.switch_soft_y, pos_z),
                        scale=(cfg.switch_soft_radius, cfg.switch_soft_height, cfg.switch_soft_radius),
                        color=c_switch_soft,
                    )
                    _PulseRing(
                        parent=self.root,
                        position=(
                            pos_x,
                            cfg.switch_soft_y + cfg.switch_soft_height / 2 + 0.006,
                            pos_z,
                        ),
                        radius=cfg.switch_soft_radius * 0.78,
                        accent=c_switch_soft,
                    )
                    self.switch_entities[(x, y)] = plate
                else:
                    Entity(
                        parent=self.root,
                        model='cube',
                        position=(pos_x, cfg.switch_heavy_y - 0.02, pos_z),
                        scale=(0.74, 0.04, 0.74),
                        color=c_inset,
                    )
                    heavy_switch = _HeavySwitch(
                        parent=self.root,
                        position=(pos_x, cfg.switch_heavy_y, pos_z),
                        config=cfg,
                    )
                    self.switch_entities[(x, y)] = heavy_switch

            elif tile_type == TileType.TELEPORT:
                top_slab = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.normal_slab_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_normal,
                )
                c_teleport_accent = color.hex(Palette.TILE_TELEPORT.hex_code)
                self._add_top_surface(
                    pos_x, pos_z, 0.002, tile_size,
                    ("#1A0B2B", "#351454", "#200D38", "#45165C"),
                    Palette.TILE_TELEPORT.hex_code,
                )
                _TeleportOrbit(
                    parent=self.root,
                    position=(pos_x, cfg.normal_inset_y + 0.018, pos_z),
                    accent=c_teleport_accent,
                )
                self.tile_entities[(x, y)] = top_slab

        if crack_vertices:
            Entity(
                parent=self.root,
                name="fragile_crack_mesh",
                model=Mesh(
                    vertices=crack_vertices,
                    triangles=crack_triangles,
                    colors=[c_fragile_inset] * len(crack_vertices),
                    static=True,
                ),
                shader=unlit_shader,
                color=color.white,
                double_sided=True,
            )

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
                self._add_top_surface(
                    0, 0, cfg.normal_slab_height / 2 + 0.002, tile_size,
                    ("#684D00", "#B88A08", "#7D5E04", "#D8A810"),
                    Palette.BRIDGE_BORDER.hex_code,
                    parent=bridge_tile,
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

    def animate_landing(self, cells) -> None:
        """Flash each occupied board cell as the block finishes a landing."""
        tile_size = CONFIG.board.tile_size
        for x, y in cells:
            cell = (x, y)
            if cell not in self.tile_entities and cell not in self.bridge_entities:
                continue
            _LandingFlash(self.root, float(x), -float(y), tile_size)
