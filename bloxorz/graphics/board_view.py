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
from ursina import Entity, color, destroy, curve, invoke, time, Vec3, Texture
from ursina.models.procedural.cylinder import Cylinder

from bloxorz.core.constants import TileType
from bloxorz.core.board import Board
from bloxorz.ui.theme import Palette
from bloxorz.config import CONFIG
from bloxorz.graphics.fx_manager import FXManager
from bloxorz.graphics.background_matrix import ColumnSea

_TEX_PATH = Path(__file__).resolve().parent.parent / "assets" / "textures" / "tile_bevel.png"
_TILE_TEX = Texture(str(_TEX_PATH)) if _TEX_PATH.exists() else None


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

            # Deep monolithic foundation dropping into the column sea
            if tile_type != TileType.GOAL:
                Entity(
                    parent=tile_root,
                    model='cube',
                    position=(0.0, -tile_h - base_depth / 2.0, 0.0),
                    scale=(1.002, base_depth, 1.002),
                    color=c_pedestal,
                )
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

                if tile_type == TileType.SWITCH_SOFT:
                    plate = Entity(
                        parent=tile_root,
                        model=Cylinder(resolution=24),
                        position=(0.0, 0.04, 0.0),
                        scale=(0.52, 0.08, 0.52),
                        color=c_switch_soft,
                    )
                    self.switch_entities[(x, y)] = plate
                else:
                    x_root = Entity(
                        parent=tile_root,
                        position=(0.0, 0.04, 0.0),
                        rotation_y=45,
                    )
                    Entity(
                        parent=x_root,
                        model='cube',
                        position=(0, 0, 0),
                        scale=(0.64, 0.08, 0.20),
                        color=c_switch_heavy,
                    )
                    Entity(
                        parent=x_root,
                        model='cube',
                        position=(0, 0, 0),
                        scale=(0.20, 0.08, 0.64),
                        color=c_switch_heavy,
                    )
                    self.switch_entities[(x, y)] = x_root

            elif tile_type == TileType.TELEPORT:
                top_slab = Entity(
                    parent=tile_root,
                    model='cube',
                    texture=_TILE_TEX,
                    position=(0.0, -tile_h / 2.0, 0.0),
                    scale=(tile_w, tile_h, tile_w),
                    color=c_normal,
                )
                c_teleport_accent = color.hex(Palette.TEXT_ACCENT.hex_code)
                inset_w = tile_w * 0.36
                inset_h = tile_w * 0.36
                offset_x = tile_w * 0.22
                Entity(
                    parent=tile_root,
                    model='cube',
                    position=(-offset_x, 0.01, 0.0),
                    scale=(inset_w, 0.03, inset_h),
                    color=c_teleport_accent,
                )
                Entity(
                    parent=tile_root,
                    model='cube',
                    position=(offset_x, 0.01, 0.0),
                    scale=(inset_w, 0.03, inset_h),
                    color=c_teleport_accent,
                )
                self.tile_entities[(x, y)] = top_slab

        # Build bridge entities (slatted architectural planks)
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

                bridge_tile = Entity(
                    parent=bridge_root,
                    model='cube',
                    texture=_TILE_TEX,
                    position=(0.0, -tile_h / 2.0 if group.is_open else -1.50, 0.0),
                    scale=(tile_w, tile_h, tile_w),
                    color=c_bridge,
                    visible=group.is_open,
                )
                self.bridge_entities[(bx, by)] = bridge_tile

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
        cfg = CONFIG.board
        stagger_delay = 0.05
        idx = 0

        for group in board.bridges.values():
            for (bx, by) in group.tiles:
                ent = self.bridge_entities.get((bx, by))
                if not ent:
                    continue
                delay = idx * stagger_delay
                idx += 1

                if group.is_open:
                    ent.visible = True
                    invoke(
                        lambda e=ent: e.animate_y(cfg.bridge_open_y, duration=cfg.bridge_anim_duration, curve=curve.out_cubic),
                        delay=delay,
                    )
                else:
                    def hide_after_sink(e=ent):
                        e.visible = False
                    invoke(
                        lambda e=ent: e.animate_y(cfg.bridge_closed_y, duration=cfg.bridge_anim_duration, curve=curve.in_cubic),
                        delay=delay,
                    )
                    invoke(hide_after_sink, delay=delay + cfg.bridge_anim_duration)

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

        # Pulsating arcane breathing glow for goal core floor
        if self.goal_floor:
            c_glow = Palette.GOAL_GLOW
            glow_alpha = 0.70 + 0.30 * math.sin(self._anim_time * 2.2)
            self.goal_floor.color = color.rgba(c_glow.r, c_glow.g, c_glow.b, glow_alpha)
