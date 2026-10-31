"""3D Board visualizer implementing Khoa's neo-minimalist architectural geometry with subtle border feedback."""

import math
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple
from ursina import Entity, Mesh, Vec3, color, destroy, curve, invoke, time
from ursina.models.procedural.cylinder import Cylinder
from ursina.shaders import unlit_shader

from bloxorz.core.constants import TileType
from bloxorz.core.board import Board
from bloxorz.ui.theme import Palette
from bloxorz.config import CONFIG
from bloxorz.graphics.board_meshes import (
    beveled_box_mesh,
    deck_border_mesh,
    deck_panel_mesh,
    hollow_box_mesh,
)


class _PulseRing(Entity):
    """Blue neon ring that softly expands and fades around a soft switch."""

    def __init__(self, parent: Entity, position: Tuple[float, float, float], radius: float, accent) -> None:
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

    def __init__(self, parent: Entity, position: Tuple[float, float, float], accent) -> None:
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

    def __init__(self, parent: Entity, position: Tuple[float, float, float], config) -> None:
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
    """Renders the 3D grid with clear void gaps, distinct tile types, and dynamic tactile feedback."""

    _instance: Optional["BoardView"] = None

    def __init__(self):
        BoardView._instance = self
        self.root = Entity(name="board_root")
        self.tile_entities: Dict[Tuple[int, int], Entity] = {}
        self.tile_types: Dict[Tuple[int, int], TileType] = {}
        self.tile_parts: Dict[Tuple[int, int], List[Entity]] = {}
        self.tile_roots: Dict[Tuple[int, int], Entity] = {}
        self.tile_borders: Dict[Tuple[int, int], Entity] = {}
        self._border_base_colors: Dict[Tuple[int, int], color.Color] = {}
        self._border_revisions: Dict[Tuple[int, int], int] = {}
        self._border_sizes: Dict[Tuple[int, int], float] = {}
        self._border_width_factors: Dict[Tuple[int, int], float] = {}
        self._last_bridge_states: Dict[str, bool] = {}
        self.switch_entities: Dict[Tuple[int, int], Entity] = {}
        self.bridge_entities: Dict[Tuple[int, int], Entity] = {}
        self.goal_entity: Optional[Entity] = None
        self.crack_entity: Optional[Entity] = None
        self._fragile_cracks: Dict[Tuple[int, int], Tuple[List, List]] = {}
        self._fragile_crack_color: color.Color = color.hex(Palette.TILE_FRAGILE_INSET.hex_code)
        self._bridge_revisions: Dict[Tuple[int, int], int] = {}
        self._switch_rest_y: Dict[Tuple[int, int], float] = {}
        self._switch_press_revisions: Dict[Tuple[int, int], int] = {}
        self.board: Optional[Board] = None
        self._crumbling_tiles: Set[Tuple[int, int]] = set()
        self._build_generation: int = 0
        self._wave_time: float = 0.0
        self._anim_time: float = 0.0

        # Propagate update loop through root entity
        self.root.update = self.update

    @classmethod
    def get_instance(cls) -> Optional["BoardView"]:
        """Returns the active BoardView instance."""
        return cls._instance

    def get_tile_border(self, cell: Tuple[int, int]) -> Optional[Entity]:
        """Returns the neon border entity for the specified board cell."""
        return self.tile_borders.get(cell)

    def _compute_exposed_edges(self, board: Board, x: int, y: int) -> List[str]:
        """Calculates which of the 4 local edges are exposed (adjacent to void or non-walkable tile)."""
        # Local x_neg=(x-1, y), x_pos=(x+1, y), z_neg=(x, y+1), z_pos=(x, y-1)
        neighbors = [
            ("x_neg", (x - 1, y)),
            ("x_pos", (x + 1, y)),
            ("z_neg", (x, y + 1)),
            ("z_pos", (x, y - 1)),
        ]
        exposed: List[str] = []
        for edge_name, (nx, ny) in neighbors:
            tile_type = board.get_tile(nx, ny)
            if not board.is_tile_walkable(tile_type):
                exposed.append(edge_name)
        return exposed

    def _add_top_surface(
        self,
        x: float,
        z: float,
        y: float,
        tile_size: float,
        gradient: Tuple[str, str, str, str],
        border_hex: str,
        border_width_factor: float = 0.018,
        parent: Optional[Entity] = None,
        exposed_edges: Optional[Iterable[str]] = None,
        detailed: bool = False,
    ) -> Tuple[Entity, Entity]:
        panel_size = tile_size * 0.88
        border_size = tile_size * 0.93
        edges = exposed_edges if exposed_edges is not None else ("x_neg", "x_pos", "z_neg", "z_pos")

        surface = Entity(
            parent=parent if parent is not None else self.root,
            name="tile_gradient_surface",
            model=deck_panel_mesh(panel_size, gradient, detailed=detailed),
            position=(x, y, z),
            shader=unlit_shader,
            double_sided=True,
        )

        border_color = color.hex(border_hex)
        base_color = color.rgba(border_color.r, border_color.g, border_color.b, 0.98)
        neon_border = Entity(
            parent=parent if parent is not None else self.root,
            name="tile_neon_border",
            model=deck_border_mesh(border_size, edges, width_factor=border_width_factor),
            position=(x, y + 0.003, z),
            shader=unlit_shader,
            color=base_color,
            transparency=True,
            double_sided=True,
        )
        return surface, neon_border

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

    def _rebuild_batched_crack_mesh(self) -> None:
        """Constructs or updates the single batched crack mesh for all intact fragile cells."""
        if not self._fragile_cracks:
            if self.crack_entity:
                destroy(self.crack_entity)
                self.crack_entity = None
            return

        batched_vertices = []
        batched_triangles = []
        for verts, tris in self._fragile_cracks.values():
            base = len(batched_vertices)
            batched_vertices.extend(verts)
            for t in tris:
                batched_triangles.append((t[0] + base, t[1] + base, t[2] + base))

        crack_model = Mesh(
            vertices=batched_vertices,
            triangles=batched_triangles,
            colors=[self._fragile_crack_color] * len(batched_vertices),
            static=True,
        )

        if self.crack_entity and getattr(self.crack_entity, "enabled", True):
            self.crack_entity.model = crack_model
        else:
            self.crack_entity = Entity(
                parent=self.root,
                name="fragile_crack_mesh",
                model=crack_model,
                shader=unlit_shader,
                color=color.white,
                double_sided=True,
            )

    def clear(self) -> None:
        """Destroys all visual entities on the board and invalidates active animation callbacks."""
        self._build_generation += 1
        for child in list(self.root.children):
            destroy(child)
        self.tile_entities.clear()
        self.tile_types.clear()
        self.tile_parts.clear()
        self.tile_roots.clear()
        self.tile_borders.clear()
        self._border_base_colors.clear()
        self._border_revisions.clear()
        self._border_sizes.clear()
        self._border_width_factors.clear()
        self._last_bridge_states.clear()
        self.switch_entities.clear()
        self.bridge_entities.clear()
        self._crumbling_tiles.clear()
        self._fragile_cracks.clear()
        self._bridge_revisions.clear()
        self._switch_rest_y.clear()
        self._switch_press_revisions.clear()
        self.crack_entity = None
        self.goal_entity = None
        self.board = None
        self._wave_time = 0.0

    def build(self, board: Board) -> None:
        """Constructs 3D representations of all board elements with fixed settled geometry and border lift entry."""
        self.clear()
        gen = self._build_generation
        self.board = board
        if hasattr(board, "base_tiles"):
            self.tile_types = dict(board.base_tiles)

        c_normal = color.hex(Palette.TILE_NORMAL.hex_code)
        c_pedestal = color.hex(Palette.TILE_PEDESTAL.hex_code)
        c_inset = color.hex(Palette.TILE_INSET.hex_code)
        c_fragile = color.hex(Palette.TILE_FRAGILE.hex_code)
        self._fragile_crack_color = color.hex(Palette.TILE_FRAGILE_INSET.hex_code)
        c_switch_soft = color.hex(Palette.SWITCH_SOFT.hex_code)
        c_bridge = color.hex(Palette.BRIDGE_ACTIVE.hex_code)
        c_goal_rim = color.hex(Palette.GOAL_RIM.hex_code)
        c_goal_void = color.hex(Palette.TILE_GOAL.hex_code)
        c_goal_glow = color.hex(Palette.GOAL_GLOW.hex_code)

        cfg = CONFIG.board
        tile_size = cfg.tile_size
        crack_paths = (
            ((-0.25, -0.20), (0.0, 0.0)),
            ((0.0, 0.0), (0.18, 0.28)),
            ((0.0, 0.0), (0.27, -0.11)),
            ((-0.15, 0.18), (0.05, 0.29)),
            ((0.12, -0.02), (0.25, -0.28)),
            ((-0.05, -0.05), (-0.25, -0.27)),
        )

        intro_enabled = getattr(CONFIG.animation, "stage_intro_anim", True)

        for (x, y), tile_type in board.base_tiles.items():
            pos_x = float(x)
            pos_z = -float(y)
            parts: List[Entity] = []

            # Deep pedestal base reaching down into the void
            if tile_type != TileType.GOAL:
                ped = Entity(
                    parent=self.root,
                    model=beveled_box_mesh(ribbed=True),
                    position=(pos_x, cfg.pedestal_y, pos_z),
                    scale=(tile_size - cfg.pedestal_inset, cfg.pedestal_height, tile_size - cfg.pedestal_inset),
                    color=c_pedestal,
                )
                parts.append(ped)

            if tile_type == TileType.NORMAL:
                top_slab = Entity(
                    parent=self.root,
                    model=beveled_box_mesh(ribbed=False),
                    position=(pos_x, cfg.normal_slab_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_normal,
                )
                exposed = self._compute_exposed_edges(board, x, y)
                surf, border = self._add_top_surface(
                    pos_x, pos_z, 0.002, tile_size,
                    ("#152131", "#2B3B50", "#182638", "#2F4259"),
                    Palette.TILE_BORDER.hex_code,
                    border_width_factor=0.018,
                    exposed_edges=exposed,
                    detailed=True,
                )
                self.tile_entities[(x, y)] = top_slab
                self.tile_roots[(x, y)] = top_slab
                self.tile_borders[(x, y)] = border
                self._border_base_colors[(x, y)] = border.color
                self._border_sizes[(x, y)] = tile_size * 0.93
                self._border_width_factors[(x, y)] = 0.018
                parts.extend([top_slab, surf, border])

            elif tile_type == TileType.FRAGILE:
                slab = Entity(
                    parent=self.root,
                    model=beveled_box_mesh(ribbed=False),
                    position=(pos_x, cfg.fragile_slab_y, pos_z),
                    scale=(tile_size, cfg.fragile_slab_height, tile_size),
                    color=c_fragile,
                )
                exposed = self._compute_exposed_edges(board, x, y)
                surf, border = self._add_top_surface(
                    pos_x, pos_z, 0.002, tile_size,
                    ("#482006", "#8A3B08", "#5A2608", "#A64A0A"),
                    Palette.TILE_FRAGILE.hex_code,
                    border_width_factor=0.018,
                    exposed_edges=exposed,
                    detailed=False,
                )
                cell_verts = []
                cell_tris = []
                for start, end in crack_paths:
                    self._append_crack_segment(
                        cell_verts,
                        cell_tris,
                        pos_x,
                        pos_z,
                        (start[0] * tile_size, start[1] * tile_size),
                        (end[0] * tile_size, end[1] * tile_size),
                        width=0.014,
                        y=0.014,
                    )
                self._fragile_cracks[(x, y)] = (cell_verts, cell_tris)
                self.tile_entities[(x, y)] = slab
                self.tile_roots[(x, y)] = slab
                self.tile_borders[(x, y)] = border
                self._border_base_colors[(x, y)] = border.color
                self._border_sizes[(x, y)] = tile_size * 0.93
                self._border_width_factors[(x, y)] = 0.018
                parts.extend([slab, surf, border])

            elif tile_type == TileType.GOAL:
                cfg_block_w = getattr(CONFIG.block, "unit_scale_1", 0.86)
                goal_outer = 0.98
                goal_aperture = min(goal_outer - 0.02, max(0.90, cfg_block_w + 0.04))
                goal_inner_ratio = goal_aperture / goal_outer
                hollow_mesh_halo = hollow_box_mesh(goal_inner_ratio)
                hollow_mesh_well = hollow_box_mesh(goal_inner_ratio)

                well = Entity(
                    parent=self.root,
                    name="goal_well",
                    model=hollow_mesh_well,
                    position=(pos_x, cfg.goal_well_y, pos_z),
                    scale=(goal_outer, cfg.goal_well_height, goal_outer),
                    color=c_goal_void,
                )
                halo = Entity(
                    parent=self.root,
                    name="goal_halo",
                    model=hollow_mesh_halo,
                    position=(pos_x, cfg.goal_rim_y, pos_z),
                    scale=(goal_outer, cfg.goal_rim_height, goal_outer),
                    color=c_goal_rim,
                )
                floor = Entity(
                    parent=self.root,
                    model='cube',
                    position=(pos_x, cfg.goal_floor_y, pos_z),
                    scale=(tile_size * cfg.goal_floor_ratio, cfg.goal_floor_height, tile_size * cfg.goal_floor_ratio),
                    color=c_goal_glow,
                )
                beacon = _GoalBeacon(self.root, pos_x, pos_z)
                self.goal_entity = well
                self.tile_entities[(x, y)] = well
                self.tile_roots[(x, y)] = well
                parts.extend([well, halo, floor, beacon])

            elif tile_type in (TileType.SWITCH_SOFT, TileType.SWITCH_HEAVY):
                base_slab = Entity(
                    parent=self.root,
                    model=beveled_box_mesh(ribbed=False),
                    position=(pos_x, cfg.normal_slab_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_normal,
                )
                self.tile_entities[(x, y)] = base_slab
                self.tile_roots[(x, y)] = base_slab
                is_soft = tile_type == TileType.SWITCH_SOFT
                exposed = self._compute_exposed_edges(board, x, y)
                surf, border = self._add_top_surface(
                    pos_x, pos_z, 0.002, tile_size,
                    (
                        ("#07172A", "#092445", "#06172A", "#0C1C32")
                        if is_soft
                        else ("#210A12", "#3B0B16", "#230913", "#44101A")
                    ),
                    (Palette.SWITCH_SOFT if is_soft else Palette.SWITCH_HEAVY).hex_code,
                    border_width_factor=0.065,
                    exposed_edges=exposed,
                    detailed=False,
                )
                self.tile_borders[(x, y)] = border
                self._border_base_colors[(x, y)] = border.color
                self._border_sizes[(x, y)] = tile_size * 0.93
                self._border_width_factors[(x, y)] = 0.065
                parts.extend([base_slab, surf, border])

                if is_soft:
                    plate = Entity(
                        parent=self.root,
                        model=Cylinder(resolution=24),
                        position=(pos_x, cfg.switch_soft_y, pos_z),
                        scale=(0.54, cfg.switch_soft_height, 0.54),
                        color=c_switch_soft,
                    )
                    ring = _PulseRing(
                        parent=self.root,
                        position=(pos_x, cfg.normal_slab_y + cfg.normal_slab_height / 2 + 0.003, pos_z),
                        radius=0.34,
                        accent=c_switch_soft,
                    )
                    self.switch_entities[(x, y)] = plate
                    self._switch_rest_y[(x, y)] = cfg.switch_soft_y
                    parts.extend([plate, ring])
                else:
                    inset_plate = Entity(
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
                    self._switch_rest_y[(x, y)] = cfg.switch_heavy_y
                    parts.extend([inset_plate, heavy_switch])

            elif tile_type == TileType.TELEPORT:
                top_slab = Entity(
                    parent=self.root,
                    model=beveled_box_mesh(ribbed=False),
                    position=(pos_x, cfg.normal_slab_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_normal,
                )
                c_teleport_accent = color.hex(Palette.TILE_TELEPORT.hex_code)
                exposed = self._compute_exposed_edges(board, x, y)
                surf, border = self._add_top_surface(
                    pos_x, pos_z, 0.002, tile_size,
                    ("#1A0B2B", "#351454", "#200D38", "#45165C"),
                    Palette.TILE_TELEPORT.hex_code,
                    border_width_factor=0.018,
                    exposed_edges=exposed,
                    detailed=False,
                )
                teleport_orbit = _TeleportOrbit(
                    parent=self.root,
                    position=(pos_x, cfg.normal_inset_y + 0.018, pos_z),
                    accent=c_teleport_accent,
                )
                self.tile_entities[(x, y)] = top_slab
                self.tile_roots[(x, y)] = top_slab
                self.tile_borders[(x, y)] = border
                self._border_base_colors[(x, y)] = border.color
                self._border_sizes[(x, y)] = tile_size * 0.93
                self._border_width_factors[(x, y)] = 0.018
                parts.extend([top_slab, surf, border, teleport_orbit])

            self.tile_parts[(x, y)] = parts

        if self._fragile_cracks:
            self._rebuild_batched_crack_mesh()

        # Build bridge entities (slatted architectural planks)
        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                pos_x = float(bx)
                pos_z = -float(by)
                bridge_tile = Entity(
                    parent=self.root,
                    model=beveled_box_mesh(ribbed=False),
                    position=(pos_x, cfg.bridge_open_y if group.is_open else cfg.bridge_closed_y, pos_z),
                    scale=(tile_size, cfg.normal_slab_height, tile_size),
                    color=c_bridge,
                    visible=group.is_open,
                )
                exposed = self._compute_exposed_edges(board, bx, by)
                surf, border = self._add_top_surface(
                    0, 0, cfg.normal_slab_height / 2 + 0.002, tile_size,
                    ("#684D00", "#B88A08", "#7D5E04", "#D8A810"),
                    Palette.BRIDGE_BORDER.hex_code,
                    border_width_factor=0.018,
                    parent=bridge_tile,
                    exposed_edges=exposed,
                    detailed=False,
                )
                self.bridge_entities[(bx, by)] = bridge_tile
                self.tile_borders[(bx, by)] = border
                self._border_base_colors[(bx, by)] = border.color
                self._border_sizes[(bx, by)] = tile_size * 0.93
                self._border_width_factors[(bx, by)] = 0.018

        self._last_bridge_states = {b_id: group.is_open for b_id, group in board.bridges.items()}

        # Simultaneous slight border brightness lift for 150ms entry
        if intro_enabled:
            intro_dur = getattr(CONFIG.animation, "stage_intro_duration", 0.15)
            for cell, border in self.tile_borders.items():
                base = self._border_base_colors.get(cell)
                if not base:
                    continue
                lifted = color.rgba(
                    base.r + (1.0 - base.r) * 0.12,
                    base.g + (1.0 - base.g) * 0.12,
                    base.b + (1.0 - base.b) * 0.12,
                    base.a,
                )
                border.color = lifted
                rev = self._border_revisions.get(cell, 0) + 1
                self._border_revisions[cell] = rev

                def restore_border_intro(c=cell, r=rev, g=gen, bc=base):
                    if self._build_generation == g and self._border_revisions.get(c) == r:
                        b = self.tile_borders.get(c)
                        if b:
                            b.color = bc

                border.animate_color(base, duration=intro_dur, curve=curve.out_quad)
                invoke(restore_border_intro, delay=intro_dur)

    def update_bridges(self, board: Board) -> None:
        """Smoothly animates bridge states with staggered architectural deployment."""
        gen = self._build_generation
        cfg = CONFIG.board
        stagger_delay = 0.06
        idx = 0

        changed_bridge_ids: Set[str] = set()
        for b_id, group in board.bridges.items():
            if self._last_bridge_states.get(b_id) != group.is_open:
                changed_bridge_ids.add(b_id)
            self._last_bridge_states[b_id] = group.is_open

        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                ent = self.bridge_entities.get((bx, by))
                if not ent:
                    continue
                delay = idx * stagger_delay
                idx += 1
                cell = (bx, by)
                rev = self._bridge_revisions.get(cell, 0) + 1
                self._bridge_revisions[cell] = rev

                if group.is_open:
                    ent.visible = True
                    ent.animate_y(cfg.bridge_open_y, duration=0.42, delay=delay, curve=curve.out_back)
                else:
                    def hide_after_sink(c=cell, r=rev, g=gen):
                        if self._build_generation == g and self._bridge_revisions.get(c) == r:
                            e = self.bridge_entities.get(c)
                            if e:
                                e.visible = False

                    ent.animate_y(cfg.bridge_closed_y, duration=0.38, delay=delay, curve=curve.in_cubic)
                    invoke(hide_after_sink, delay=delay + 0.38)

        # Skip mesh rebuild when bridge state is unchanged
        if not changed_bridge_ids:
            return

        # Refresh edge hierarchy ONLY for tiles affected by changed bridge groups
        for b_id in changed_bridge_ids:
            group = board.bridges[b_id]
            for (bx, by) in group.tiles:
                if (bx, by) in self.tile_borders:
                    b_size = self._border_sizes.get((bx, by), cfg.tile_size * 0.93)
                    b_wf = self._border_width_factors.get((bx, by), 0.018)
                    b_exposed = self._compute_exposed_edges(board, bx, by)
                    self.tile_borders[(bx, by)].model = deck_border_mesh(
                        b_size, b_exposed, width_factor=b_wf
                    )
                for nx, ny in ((bx - 1, by), (bx + 1, by), (bx, by + 1), (bx, by - 1)):
                    if (nx, ny) in self.tile_borders:
                        n_size = self._border_sizes.get((nx, ny), cfg.tile_size * 0.93)
                        n_wf = self._border_width_factors.get((nx, ny), 0.018)
                        n_exposed = self._compute_exposed_edges(board, nx, ny)
                        self.tile_borders[(nx, ny)].model = deck_border_mesh(
                            n_size, n_exposed, width_factor=n_wf
                        )

    def animate_switch_press(self, x: int, y: int) -> None:
        """Micro-animation depressing switch plate when stepped on."""
        cell = (x, y)
        plate = self.switch_entities.get(cell)
        if not plate:
            return

        gen = self._build_generation
        cfg = CONFIG.board
        rest_y = self._switch_rest_y.get(cell, plate.y)
        rev = self._switch_press_revisions.get(cell, 0) + 1
        self._switch_press_revisions[cell] = rev

        depressed_y = rest_y - cfg.switch_press_depth
        plate.animate_y(depressed_y, duration=cfg.switch_press_down_time, curve=curve.out_sine)

        def restore_plate(c=cell, r=rev, g=gen, ry=rest_y):
            if self._build_generation != g:
                return
            if self._switch_press_revisions.get(c) != r:
                return
            p = self.switch_entities.get(c)
            if p:
                p.animate_y(ry, duration=cfg.switch_press_up_time, curve=curve.out_sine)

        invoke(
            restore_plate,
            delay=cfg.switch_press_down_time + 0.02,
        )

    def animate_landing(self, cells: Iterable[Tuple[int, int]]) -> None:
        """Pulses borders of ordinary tiles for 120ms without spawning quads or recoloring slabs."""
        if not getattr(CONFIG.animation, "tile_highlight_enabled", True):
            return

        gen = self._build_generation
        highlight_dur = getattr(CONFIG.animation, "tile_highlight_duration", 0.12)
        for cell in cells:
            # Only ordinary walkable tiles receive landing border pulse
            if self.tile_types.get(cell) != TileType.NORMAL:
                continue

            border = self.tile_borders.get(cell)
            if not border:
                continue

            base = self._border_base_colors.get(cell)
            if not base:
                continue

            pulse_color = color.rgba(
                base.r + (1.0 - base.r) * 0.18,
                base.g + (1.0 - base.g) * 0.18,
                base.b + (1.0 - base.b) * 0.18,
                base.a,
            )
            border.color = pulse_color
            rev = self._border_revisions.get(cell, 0) + 1
            self._border_revisions[cell] = rev

            def restore_border_landing(c=cell, r=rev, g=gen, bc=base):
                if self._build_generation == g and self._border_revisions.get(c) == r:
                    b = self.tile_borders.get(c)
                    if b:
                        b.color = bc

            border.animate_color(base, duration=highlight_dur, curve=curve.out_quad)
            invoke(restore_border_landing, delay=highlight_dur)

    def highlight_tiles(self, cells: Iterable[Tuple[int, int]]) -> None:
        """Compatibility delegate forwarding to canonical animate_landing."""
        self.animate_landing(cells)

    def cushion_impact(self, impact_x: float, impact_y: float, intensity: float = 1.0) -> None:
        """Physical impact feedback on tiles (rock-solid floor preserves stability)."""
        pass

    def get_surface_y(self, grid_x: float, grid_y: float) -> float:
        """Returns board-local surface elevation at grid (x, y). Permanently static at 0.0."""
        return 0.0

    def compute_wave_y(self, world_x: float, world_z: float) -> float:
        """Compatibility wave helper. Permanently static at 0.0."""
        return 0.0

    def animate_fragile_crumble(
        self,
        x: int,
        y: int,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        """Executes a 3-phase collapse: vibration -> fragment burst -> abyss fall."""
        cell = (x, y)
        parts = list(self.tile_parts.get(cell, []))
        if not parts and cell in self.tile_entities:
            parts = [self.tile_entities[cell]]

        if not parts and cell not in self._fragile_cracks:
            if on_complete:
                on_complete()
            return

        gen = self._build_generation
        self._crumbling_tiles.add(cell)

        # Detach cell crack geometry from the batched mesh so intact tiles keep batching
        if cell in self._fragile_cracks:
            cell_verts, cell_tris = self._fragile_cracks.pop(cell)
            self._rebuild_batched_crack_mesh()
            detached_crack = Entity(
                parent=self.root,
                name="detached_fragile_crack",
                model=Mesh(
                    vertices=cell_verts,
                    triangles=cell_tris,
                    colors=[self._fragile_crack_color] * len(cell_verts),
                    static=True,
                ),
                shader=unlit_shader,
                color=color.white,
                double_sided=True,
            )
            parts.append(detached_crack)

        # Phase 1: Micro-vibration and Debris Burst
        try:
            from bloxorz.graphics.fx_manager import FXManager
            fx = FXManager.get_instance()
            if fx and hasattr(fx, "spawn_crumble_debris"):
                fx.spawn_crumble_debris(Vec3(float(x), 0.0, -float(y)), count=14)
        except Exception:
            pass

        shake_steps = 6
        step_dt = 0.02
        orig_positions = [(ent, ent.x) for ent in parts if ent]

        for i in range(shake_steps):
            offset = (0.04 if i % 2 == 0 else -0.04) * (1.0 - i / shake_steps)

            def apply_shake(off=offset, g=gen):
                if self._build_generation != g:
                    return
                for ent, ox in orig_positions:
                    if ent:
                        ent.x = ox + off

            invoke(apply_shake, delay=i * step_dt)

        def start_fall(g=gen):
            if self._build_generation != g:
                return
            # Reset X positions
            for ent, ox in orig_positions:
                if ent:
                    ent.x = ox
            # Phase 2 & 3: Collapse into abyss
            for ent, _ in orig_positions:
                if ent:
                    ent.animate_y(ent.y - 8.0, duration=0.85, curve=curve.in_cubic)

            def finish(g2=g):
                if self._build_generation != g2:
                    return
                for ent, _ in orig_positions:
                    if ent:
                        destroy(ent)
                if on_complete:
                    on_complete()

            invoke(finish, delay=0.85)

        invoke(start_fall, delay=shake_steps * step_dt)

    def update(self) -> None:
        """Per-frame update loop advancing internal animation clocks."""
        dt = max(0.0, time.dt)
        if dt <= 0.0:
            return
        self._anim_time += dt
        self._wave_time += dt
