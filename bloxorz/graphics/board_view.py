"""3D Board visualizer implementing the minimalist Bloxpath-inspired design system.

Features:
- Rock-solid, pristine architectural monolith tiles (zero awkward wobbling)
- Procedural Stage Intro Assembly (tiles gracefully rise into place upon loading)
- Bloxpath-signature Tile Step Highlight (illuminates subtly upon block contact)
- Distinct visual cues for fragile, switches, teleporters, and bridges
- Frame-perfect 60-120+ FPS Ursina Entity delta-time update loop
"""

import math
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from ursina import Entity, Mesh, color, destroy, curve, invoke, time, Vec3, Texture
from ursina.models.procedural.cylinder import Cylinder
from ursina.shaders import unlit_shader

from bloxorz.core.constants import TileType
from bloxorz.core.board import Board
from bloxorz.ui.theme import Palette
from bloxorz.config import CONFIG
from bloxorz.graphics.fx_manager import FXManager
from bloxorz.graphics.background_matrix import ColumnSea

_TEX_PATH = Path(__file__).resolve().parent.parent / "assets" / "textures" / "tile_bevel.png"
_TILE_TEX = Texture(str(_TEX_PATH)) if _TEX_PATH.exists() else None

_MAGMA_TEX_PATH = Path(__file__).resolve().parent.parent / "assets" / "textures" / "magma_veins.png"
_MAGMA_TEX = Texture(str(_MAGMA_TEX_PATH)) if _MAGMA_TEX_PATH.exists() else None
if _MAGMA_TEX and hasattr(_MAGMA_TEX, "_texture") and _MAGMA_TEX._texture:
    try:
        from panda3d.core import SamplerState
        _MAGMA_TEX._texture.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        _MAGMA_TEX._texture.setMagfilter(SamplerState.FT_linear)
        _MAGMA_TEX._texture.setWrapU(SamplerState.WM_repeat)
        _MAGMA_TEX._texture.setWrapV(SamplerState.WM_repeat)
    except Exception:
        pass


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


class BoardView(Entity):
    """Renders the 3D grid with clear void gaps, distinct tile types, and Bloxpath-style tactile feedback."""

    _instance: Optional["BoardView"] = None

    def __init__(self, **kwargs):
        super().__init__(name="board_root", **kwargs)
        BoardView._instance = self

        # Backward compatibility: self.root points to self
        self.root = self

        # Bloxpath Undulating Background Column Sea
        self.column_sea = ColumnSea(parent=self)

        # Container registries
        self.tile_roots: Dict[Tuple[int, int], Entity] = {}
        self.tile_entities: Dict[Tuple[int, int], Entity] = {}
        self.tile_types: Dict[Tuple[int, int], TileType] = {}
        self.board: Optional[Board] = None
        self.switch_entities: Dict[Tuple[int, int], Entity] = {}
        self.bridge_entities: Dict[Tuple[int, int], Entity] = {}
        self.bridge_roots: Dict[Tuple[int, int], Entity] = {}
        self.pedestal_entities: List[Tuple[Entity, float]] = []
        self.goal_entity: Optional[Entity] = None
        self.goal_floor: Optional[Entity] = None

        # Fragile crumble tracking
        self._crumbling_tiles: Set[Tuple[int, int]] = set()
        self._anim_time: float = 0.0
        self._wave_time: float = 0.0

    @classmethod
    def get_instance(cls) -> Optional["BoardView"]:
        """Returns the active BoardView instance."""
        return cls._instance

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
        for child in list(self.children):
            if child is not getattr(self, "column_sea", None):
                destroy(child)

        if getattr(self, "column_sea", None):
            self.column_sea.clear()

        self._wave_time = 0.0

        self.tile_roots.clear()
        self.tile_entities.clear()
        self.tile_types.clear()
        self.board = None
        self.switch_entities.clear()
        self.bridge_entities.clear()
        self.bridge_roots.clear()
        self.pedestal_entities.clear()
        self._crumbling_tiles.clear()
        self.goal_entity = None
        self.goal_floor = None

    def build(self, board: Board):
        """Constructs 3D representations of all board elements with authentic Bloxpath plateau styling."""
        self.clear()
        self.board = board
        if hasattr(board, "base_tiles"):
            self.tile_types = dict(board.base_tiles)

        # Build undulating background column sea around the stage
        if getattr(self, "column_sea", None):
            self.column_sea.build_around_board(board)

        c_normal = color.hex(Palette.TILE_NORMAL.hex_code)
        c_pedestal = color.hex(Palette.TILE_PEDESTAL.hex_code)
        c_fragile = color.hex(Palette.TILE_FRAGILE.hex_code)
        c_under_rim = color.hex(Palette.UNDER_RIM.hex_code)
        c_switch_soft = color.hex(Palette.SWITCH_SOFT.hex_code)
        c_switch_heavy = color.hex(Palette.SWITCH_HEAVY.hex_code)
        c_bridge = color.hex(Palette.BRIDGE_ACTIVE.hex_code)
        c_goal_rim = color.hex(Palette.GOAL_RIM.hex_code)
        c_goal_void = color.hex(Palette.TILE_GOAL.hex_code)
        c_goal_glow = color.hex(Palette.GOAL_GLOW.hex_code)

        tile_w = 0.97
        tile_h = 0.35
        base_depth = 2.40

        # Stage Assembly Intro Animation parameters
        intro_enabled = getattr(CONFIG.animation, "stage_intro_anim", True)
        stagger = getattr(CONFIG.animation, "stage_intro_stagger", 0.018)
        dur = getattr(CONFIG.animation, "stage_intro_duration", 0.28)

        spawn_pos = board.spawn_state.get_center_3d() if hasattr(board, "spawn_state") else (0, 0, 0)
        sp_x, sp_y = float(spawn_pos[0]), float(spawn_pos[1])

        # Track occupied walkable cells for perimeter calculation
        occupied: Set[Tuple[int, int]] = set(board.base_tiles.keys())
        if hasattr(board, "bridges"):
            for group in board.bridges.values():
                occupied.update(group.tiles)
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

        for (x, y), tile_type in board.base_tiles.items():
            pos_x = float(x)
            pos_z = -float(y)

            # Master container for tile
            init_y = -3.6 if intro_enabled else 0.0
            tile_root = Entity(
                parent=self,
                position=(pos_x, init_y, pos_z),
                name=f"tile_root_{x}_{y}",
            )
            self.tile_roots[(x, y)] = tile_root

            if intro_enabled:
                dist = math.hypot(pos_x - sp_x, pos_z - (-sp_y))
                delay = min(0.38, dist * stagger)
                tile_root.animate_y(0.0, duration=dur + 0.12, delay=delay, curve=curve.out_back)

            # Deep monolithic foundation dropping into the column sea with glowing magma veins
            if tile_type != TileType.GOAL:
                ped = Entity(
                    parent=tile_root,
                    model='cube',
                    texture=_MAGMA_TEX,
                    position=(0.0, -tile_h - base_depth / 2.0, 0.0),
                    scale=(1.002, base_depth, 1.002),
                    color=color.white if _MAGMA_TEX else c_pedestal,
                )
                if _MAGMA_TEX:
                    ped.texture_scale = (0.70, 1.30)
                    u_off = (float(x) * 0.28 + float(y) * 0.43) % 1.0
                    ped.texture_offset = (u_off, 0.0)
                    self.pedestal_entities.append((ped, u_off))

                # Cyberpunk Magma heat collar anchoring the volcanic rock into the flowing lava
                Entity(
                    parent=tile_root,
                    model='cube',
                    position=(0.0, -1.73, 0.0),
                    scale=(1.06, 0.05, 1.06),
                    color=color.hex(Palette.LAVA_UNDERGLOW.hex_code),
                    unlit=True,
                )

            if tile_type == TileType.NORMAL:
                top_slab = Entity(
                    parent=tile_root,
                    model='cube',
                    texture=_TILE_TEX,
                    position=(0.0, -tile_h / 2.0, 0.0),
                    scale=(tile_w, tile_h, tile_w),
                    color=c_normal,
                )
                self.tile_entities[(x, y)] = top_slab
                self._add_top_surface(
                    0, 0, 0.002, tile_w,
                    ("#070B13", "#0D1422", "#080D18", "#101827"),
                    Palette.TILE_BORDER.hex_code,
                    border_width_factor=0.065, parent=tile_root,
                )

            elif tile_type == TileType.FRAGILE:
                slab = Entity(
                    parent=tile_root,
                    model='cube',
                    texture=_TILE_TEX,
                    position=(0.0, -tile_h / 2.0, 0.0),
                    scale=(tile_w, tile_h, tile_w),
                    color=c_fragile,
                )
                self.tile_entities[(x, y)] = slab
                self._add_top_surface(
                    0, 0, 0.002, tile_w,
                    ("#482006", "#8A3B08", "#5A2608", "#A64A0A"),
                    Palette.TILE_FRAGILE.hex_code, parent=tile_root,
                )
                vertices, triangles = [], []
                for start, end in crack_paths:
                    self._append_crack_segment(
                        vertices, triangles, 0, 0, start, end, width=0.014, y=0.014,
                    )
                Entity(
                    parent=tile_root, name="fragile_crack_mesh",
                    model=Mesh(vertices=vertices, triangles=triangles, static=True),
                    color=c_fragile, shader=unlit_shader, double_sided=True,
                )

            elif tile_type == TileType.GOAL:
                # Open square void well
                well = Entity(
                    parent=tile_root,
                    model='cube',
                    position=(0.0, -tile_h - 0.40, 0.0),
                    scale=(tile_w, 0.80, tile_w),
                    color=c_goal_void,
                )
                # Golden halo rim framing 4 outer edges of the void hole
                rim_t = 0.08
                Entity(parent=tile_root, model='cube', position=(0.0, 0.01, -0.45), scale=(tile_w, 0.03, rim_t), color=c_goal_rim)
                Entity(parent=tile_root, model='cube', position=(0.0, 0.01, 0.45), scale=(tile_w, 0.03, rim_t), color=c_goal_rim)
                Entity(parent=tile_root, model='cube', position=(-0.45, 0.01, 0.0), scale=(rim_t, 0.03, tile_w), color=c_goal_rim)
                Entity(parent=tile_root, model='cube', position=(0.45, 0.01, 0.0), scale=(rim_t, 0.03, tile_w), color=c_goal_rim)

                # Pulsating arcane core floor at bottom of void well
                goal_floor = Entity(
                    parent=tile_root,
                    model='cube',
                    position=(0.0, -tile_h - 0.78, 0.0),
                    scale=(tile_w * 0.75, 0.04, tile_w * 0.75),
                    color=c_goal_glow,
                )
                self.goal_entity = well
                self.goal_floor = goal_floor
                self.tile_entities[(x, y)] = well
                _GoalBeacon(tile_root, 0, 0)

            elif tile_type in (TileType.SWITCH_SOFT, TileType.SWITCH_HEAVY):
                base_slab = Entity(
                    parent=tile_root,
                    model='cube',
                    texture=_TILE_TEX,
                    position=(0.0, -tile_h / 2.0, 0.0),
                    scale=(tile_w, tile_h, tile_w),
                    color=c_normal,
                )
                self.tile_entities[(x, y)] = base_slab
                is_soft = tile_type == TileType.SWITCH_SOFT
                self._add_top_surface(
                    0, 0, 0.002, tile_w,
                    (
                        ("#07172A", "#092445", "#06172A", "#0C1C32")
                        if is_soft
                        else ("#210A12", "#3B0B16", "#230913", "#44101A")
                    ),
                    (Palette.SWITCH_SOFT if is_soft else Palette.SWITCH_HEAVY).hex_code,
                    parent=tile_root,
                )

                if tile_type == TileType.SWITCH_SOFT:
                    plate = Entity(
                        parent=tile_root,
                        model=Cylinder(resolution=24),
                        position=(0.0, 0.04, 0.0),
                        scale=(0.52, 0.08, 0.52),
                        color=c_switch_soft,
                    )
                    _PulseRing(
                        parent=tile_root,
                        position=(0, 0.09, 0),
                        radius=cfg.switch_soft_radius * 0.78,
                        accent=c_switch_soft,
                    )
                    self.switch_entities[(x, y)] = plate
                else:
                    heavy_switch = _HeavySwitch(
                        parent=tile_root,
                        position=(0, 0.04, 0),
                        config=cfg,
                    )
                    self.switch_entities[(x, y)] = heavy_switch

            elif tile_type == TileType.TELEPORT:
                top_slab = Entity(
                    parent=tile_root,
                    model='cube',
                    texture=_TILE_TEX,
                    position=(0.0, -tile_h / 2.0, 0.0),
                    scale=(tile_w, tile_h, tile_w),
                    color=c_normal,
                )
                self._add_top_surface(
                    0, 0, 0.002, tile_w,
                    ("#1A0B2B", "#351454", "#200D38", "#45165C"),
                    Palette.TILE_TELEPORT.hex_code,
                    parent=tile_root,
                )
                _TeleportOrbit(
                    parent=tile_root, position=(0, 0.035, 0),
                    accent=color.hex(Palette.TILE_TELEPORT.hex_code),
                )
                self.tile_entities[(x, y)] = top_slab

        # Build bridge entities (Full architectural monolith columns matching normal tiles)
        closed_y = -3.80
        open_y = 0.0
        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                pos_x = float(bx)
                pos_z = -float(by)
                bridge_root = Entity(
                    parent=self,
                    position=(pos_x, 0.0, pos_z),
                    name=f"bridge_root_{bx}_{by}",
                )
                self.bridge_roots[(bx, by)] = bridge_root

                # Full bridge column that rises up / sinks down
                bridge_col = Entity(
                    parent=bridge_root,
                    position=(0.0, open_y if group.is_open else closed_y, 0.0),
                    visible=group.is_open,
                    name=f"bridge_col_{bx}_{by}",
                )
                self.bridge_entities[(bx, by)] = bridge_col

                # 1. Top walkable slab matching standard tiles
                top_slab = Entity(
                    parent=bridge_col,
                    model='cube',
                    texture=_TILE_TEX,
                    position=(0.0, -tile_h / 2.0, 0.0),
                    scale=(tile_w, tile_h, tile_w),
                    color=c_normal,
                )
                self.tile_entities[(bx, by)] = top_slab
                top_slab.color = c_bridge
                self._add_top_surface(
                    0, 0, 0.002, tile_w,
                    ("#684D00", "#B88A08", "#7D5E04", "#D8A810"),
                    Palette.BRIDGE_BORDER.hex_code, parent=bridge_col,
                )

                # 2. Deep monolithic foundation with flowing magma veins
                ped = Entity(
                    parent=bridge_col,
                    model='cube',
                    texture=_MAGMA_TEX,
                    position=(0.0, -tile_h - base_depth / 2.0, 0.0),
                    scale=(1.002, base_depth, 1.002),
                    color=color.white if _MAGMA_TEX else c_pedestal,
                )
                if _MAGMA_TEX:
                    ped.texture_scale = (0.70, 1.30)
                    u_off = (float(bx) * 0.28 + float(by) * 0.43) % 1.0
                    ped.texture_offset = (u_off, 0.0)
                    self.pedestal_entities.append((ped, u_off))

                # 3. Cyberpunk Magma heat collar
                Entity(
                    parent=bridge_col,
                    model='cube',
                    position=(0.0, -1.73, 0.0),
                    scale=(1.06, 0.05, 1.06),
                    color=color.hex(Palette.LAVA_UNDERGLOW.hex_code),
                    unlit=True,
                )

        # Setup ambient dust centered around the stage
        if board.base_tiles:
            xs = [x for x, _ in board.base_tiles.keys()]
            ys = [y for _, y in board.base_tiles.keys()]
            mid_x = (min(xs) + max(xs)) / 2.0
            mid_z = -((min(ys) + max(ys)) / 2.0)
            fx = FXManager.get_instance()
            fx.setup_ambient_dust(center=Vec3(mid_x, 0.0, mid_z), bounds=max(len(xs), len(ys)) * 0.9)

    # -------------------------------------------------------------------------
    # Surface Elevation & Highlight Methods
    # -------------------------------------------------------------------------

    def compute_wave_y(self, world_x: float, world_z: float) -> float:
        """Harmonic sea undulation for walkable tiles floating like an island on the sea."""
        if not getattr(CONFIG.animation, "wave_enabled", True):
            return 0.0
        amp = getattr(CONFIG.animation, "wave_amplitude", 0.22)
        speed = getattr(CONFIG.animation, "wave_speed", 1.35)
        fx = getattr(CONFIG.animation, "wave_freq_x", 0.38)
        fz = getattr(CONFIG.animation, "wave_freq_z", 0.32)
        t = self._wave_time * speed
        return (
            amp * math.sin(t + world_x * fx + world_z * fz)
            + (amp * 0.35) * math.cos(t * 0.85 - world_x * 0.25 + world_z * 0.45)
        )

    def get_surface_y(self, grid_x: float, grid_y: float) -> float:
        """Returns the dynamic sea surface elevation at grid (x, y)."""
        return self.compute_wave_y(float(grid_x), -float(grid_y))

    def highlight_tiles(self, cells: List[Tuple[int, int]]) -> None:
        """Bloxpath-signature tile illumination pulse when stepped on."""
        if not getattr(CONFIG.animation, "tile_highlight_enabled", True):
            return

        palette_mode = getattr(CONFIG.animation, "palette_mode", "alabaster").lower()
        if palette_mode == "alabaster":
            c_highlight = color.hex(Palette.TILE_ALABASTER_HIGHLIGHT.hex_code)
            c_normal = color.hex(Palette.TILE_ALABASTER.hex_code)
        else:
            c_highlight = color.hex(Palette.TILE_HIGHLIGHT.hex_code)  # Sáng màu hơn: Luminous platinum slate
            c_normal = color.hex(Palette.TILE_NORMAL.hex_code)

        dur = getattr(CONFIG.animation, "tile_highlight_duration", 0.25)

        for (cx, cy) in cells:
            if self.tile_types and (cx, cy) in self.tile_types:
                if self.tile_types[(cx, cy)] != TileType.NORMAL:
                    continue
            elif self.board and hasattr(self.board, "get_tile"):
                if self.board.get_tile(cx, cy) != TileType.NORMAL:
                    continue

            ent = self.tile_entities.get((cx, cy))
            if ent and hasattr(ent, "color") and hasattr(ent, "animate_color"):
                ent.color = c_highlight
                ent.animate_color(c_normal, duration=dur, curve=curve.out_sine)

    def cushion_impact(self, impact_x: float, impact_y: float, intensity: float = 1.0) -> None:
        """No floor depression in Bloxpath mode (rock-solid grid)."""
        pass

    # -------------------------------------------------------------------------
    # Fragile Tile Crumble & Collapse
    # -------------------------------------------------------------------------

    def animate_fragile_crumble(self, x: int, y: int, on_complete: Optional[callable] = None) -> None:
        """Executes a 3-phase collapse: vibration -> fragment burst -> abyss fall."""
        tile_root = self.tile_roots.get((x, y))
        if not tile_root:
            if on_complete:
                on_complete()
            return

        self._crumbling_tiles.add((x, y))
        orig_x = tile_root.x
        orig_z = tile_root.z

        # Phase 1: Micro-vibration (0.12s)
        fx = FXManager.get_instance()
        fx.spawn_crumble_debris(tile_root.position, count=14)

        def start_fall():
            # Phase 2 & 3: Collapse into abyss
            tile_root.x = orig_x
            tile_root.z = orig_z
            tile_root.animate_y(-8.0, duration=0.85, curve=curve.in_cubic)
            if on_complete:
                invoke(on_complete, delay=0.85)

        shake_steps = 6
        step_dt = 0.02
        for i in range(shake_steps):
            sx = orig_x + (0.04 if i % 2 == 0 else -0.04) * (1.0 - i / shake_steps)
            invoke(lambda p=sx: setattr(tile_root, 'x', p), delay=i * step_dt)

        invoke(start_fall, delay=shake_steps * step_dt)

    # -------------------------------------------------------------------------
    # Interactive Switch & Bridge Transitions
    # -------------------------------------------------------------------------

    def update_bridges(self, board: Board):
        """Smoothly animates bridge states with staggered architectural deployment."""
        stagger_delay = 0.06
        idx = 0

        closed_y = -3.80
        open_y = 0.0

        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                col = self.bridge_entities.get((bx, by))
                if not col:
                    continue
                delay = idx * stagger_delay
                idx += 1

                if group.is_open:
                    col.visible = True
                    invoke(
                        lambda c=col: c.animate_y(open_y, duration=0.42, curve=curve.out_back),
                        delay=delay,
                    )
                else:
                    def hide_after_sink(c=col):
                        c.visible = False
                    invoke(
                        lambda c=col: c.animate_y(closed_y, duration=0.38, curve=curve.in_cubic),
                        delay=delay,
                    )
                    invoke(hide_after_sink, delay=delay + 0.38)

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

    # -------------------------------------------------------------------------
    # Per-Frame Delta-Time Engine Update Loop
    # -------------------------------------------------------------------------

    def update(self) -> None:
        """Delta-time loop: smooth sea undulation for walkable tiles and goal breathing."""
        dt = time.dt
        if dt <= 0.0:
            return

        self._anim_time += dt
        self._wave_time += dt

        # Dập dìu như nổi trên mặt biển cho các ô đi được (walkable tiles)
        if getattr(CONFIG.animation, "wave_enabled", True) and self.tile_roots:
            for (x, y), root in self.tile_roots.items():
                if (x, y) not in self._crumbling_tiles:
                    root.y = self.compute_wave_y(float(x), -float(y))

            for (bx, by), broot in self.bridge_roots.items():
                broot.y = self.compute_wave_y(float(bx), -float(by))

        # Flowing molten lava veins streaming down the walkable column pillars
        if self.pedestal_entities:
            flow_y = +(self._anim_time * 0.075)  # Flowing downward smoothly
            heat_pulse = 0.94 + 0.10 * math.sin(self._anim_time * 2.2)
            c_flow = color.rgba(heat_pulse, heat_pulse * 0.95, heat_pulse * 0.92, 1.0)
            for ped, u_off in self.pedestal_entities:
                ped.texture_offset = (u_off, flow_y)
                ped.color = c_flow

        # Pulsating arcane breathing glow for goal core floor
        if self.goal_floor:
            c_glow = Palette.GOAL_GLOW
            glow_alpha = 0.70 + 0.30 * math.sin(self._anim_time * 2.2)
            self.goal_floor.color = color.rgba(c_glow.r, c_glow.g, c_glow.b, glow_alpha)
    def animate_landing(self, cells) -> None:
        """Flash each occupied board cell as the block finishes a landing."""
        tile_size = CONFIG.board.tile_size
        for x, y in cells:
            cell = (x, y)
            if cell not in self.tile_entities and cell not in self.bridge_entities:
                continue
            parent = self.tile_roots.get(cell) or self.bridge_entities.get(cell)
            if parent is not None:
                _LandingFlash(parent, 0, 0, tile_size)
