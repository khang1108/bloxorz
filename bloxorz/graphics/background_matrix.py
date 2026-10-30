"""Background Matrix: Undulating ocean of architectural columns inspired by Bloxpath.

Features:
- Vast field of monolithic obsidian columns surrounding the floating stage
- Smooth harmonic continuous wave undulation (dập dìu như sóng nước) matching Bloxpath
- Radial atmospheric depth fog blending seamlessly into the deep abyssal void
- High performance (60-120+ FPS locked) using single-cube entities and optimized math
- Leaves clean void footprint under the playable puzzle island
"""

import math
from pathlib import Path
from typing import List, Tuple, Set, Optional
from ursina import Entity, color, destroy, time, Texture

from bloxorz.config import CONFIG
from bloxorz.ui.theme import Palette

_TEX_PATH = Path(__file__).resolve().parent.parent / "assets" / "textures" / "tile_bevel.png"
_TILE_TEX = Texture(str(_TEX_PATH)) if _TEX_PATH.exists() else None

_LAVA_TEX_PATH = Path(__file__).resolve().parent.parent / "assets" / "textures" / "cyber_lava.png"
_LAVA_TEX = Texture(str(_LAVA_TEX_PATH)) if _LAVA_TEX_PATH.exists() else None
if _LAVA_TEX and hasattr(_LAVA_TEX, "_texture") and _LAVA_TEX._texture:
    try:
        from panda3d.core import SamplerState
        _LAVA_TEX._texture.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        _LAVA_TEX._texture.setMagfilter(SamplerState.FT_linear)
    except Exception:
        pass


class ColumnSea(Entity):
    """Generates and animates the signature Bloxpath ocean of bobbing columns and Cyberpunk Lava Sea."""

    _instance: Optional["ColumnSea"] = None

    def __init__(self, **kwargs):
        super().__init__(name="column_sea_root", **kwargs)
        ColumnSea._instance = self
        self.columns: List[Tuple[Entity, float, float, float]] = []
        self.column_base_colors: List[Tuple[float, float, float]] = []
        self.column_pop_params: List[Tuple[float, float, float, float]] = []
        self.lava_plane: Optional[Entity] = None
        self.lava_plane_deep: Optional[Entity] = None
        self._time: float = 0.0

    @classmethod
    def get_instance(cls) -> Optional["ColumnSea"]:
        """Returns the active singleton ColumnSea instance."""
        return cls._instance

    def clear(self):
        """Destroys all visual column entities and lava planes."""
        for col, _, _, _ in self.columns:
            destroy(col)
        self.columns.clear()
        self.column_base_colors.clear()
        self.column_pop_params.clear()

        if self.lava_plane:
            destroy(self.lava_plane)
            self.lava_plane = None
        if self.lava_plane_deep:
            destroy(self.lava_plane_deep)
            self.lava_plane_deep = None

        self._time = 0.0

    def build_around_board(self, board, padding: int = 8):
        """Constructs subdued monolithic columns and flowing Cyberpunk Neon Lava beneath the board."""
        self.clear()
        if not getattr(CONFIG.animation, "column_sea_enabled", True):
            return

        if not hasattr(board, "base_tiles") or not board.base_tiles:
            return

        # Find stage bounds and occupied tiles
        occupied: Set[Tuple[int, int]] = set(board.base_tiles.keys())
        if hasattr(board, "bridges"):
            for group in board.bridges.values():
                occupied.update(group.tiles)

        xs = [x for x, _ in occupied]
        ys = [y for _, y in occupied]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0

        # Calculate circular organic bounds around the stage
        stage_radius = max(max_x - min_x, max_y - min_y) * 0.5 + 1.0
        inner_radius = stage_radius + 4.5
        outer_radius = stage_radius + 15.0

        col_h = 7.0
        base_top_y = getattr(CONFIG.animation, "column_sea_base_y", -1.72)

        # ---------------------------------------------------------------------
        # Cyberpunk Neon Molten Lava Abyss (Infinite flowing magma ocean)
        # ---------------------------------------------------------------------
        lava_size = max(130.0, outer_radius * 2.8)
        base_lava_y = -1.75

        if _LAVA_TEX:
            if hasattr(_LAVA_TEX, "_texture") and _LAVA_TEX._texture:
                try:
                    from panda3d.core import SamplerState
                    _LAVA_TEX._texture.setMinfilter(SamplerState.FT_linear_mipmap_linear)
                    _LAVA_TEX._texture.setMagfilter(SamplerState.FT_linear)
                except Exception:
                    pass

            self.lava_plane = Entity(
                parent=self,
                model='plane',
                texture=_LAVA_TEX,
                position=(center_x, base_lava_y, -center_y),
                scale=(lava_size, 1.0, lava_size),
                unlit=True,
                double_sided=True,
                name="cyber_lava_surface",
            )
            self.lava_plane.texture_scale = (lava_size / 13.0, lava_size / 13.0)

            # Deeper secondary parallax lava layer for glowing depth
            self.lava_plane_deep = Entity(
                parent=self,
                model='plane',
                texture=_LAVA_TEX,
                rotation_y=35,
                position=(center_x, base_lava_y - 0.20, -center_y),
                scale=(lava_size * 1.25, 1.0, lava_size * 1.25),
                color=color.rgba(0.40, 0.18, 0.10, 0.45),
                unlit=True,
                double_sided=True,
                name="cyber_lava_deep",
            )
            self.lava_plane_deep.texture_scale = (lava_size / 22.0, lava_size / 22.0)

        # ---------------------------------------------------------------------
        # Radial Organic Volcanic Archipelago (Tản tự nhiên, không ranh giới hộp)
        # ---------------------------------------------------------------------
        x_start = int(math.floor(center_x - outer_radius))
        x_end = int(math.ceil(center_x + outer_radius))
        y_start = int(math.floor(center_y - outer_radius))
        y_end = int(math.ceil(center_y + outer_radius))

        for gx in range(x_start, x_end + 1):
            for gy in range(y_start, y_end + 1):
                # Never spawn columns directly under playable island tiles
                if (gx, gy) in occupied:
                    continue

                dist = math.hypot(gx - center_x, gy - center_y)
                if dist > outer_radius:
                    continue

                # Radial organic tectonic dissipation (quần đảo đá nứt nẻ tự nhiên)
                if dist > inner_radius:
                    t_dist = (dist - inner_radius) / (outer_radius - inner_radius)
                    prob = 0.5 * (1.0 + math.cos(t_dist * math.pi))
                    # Deterministic hash per cell
                    h = math.sin(float(gx) * 374761.393 + float(gy) * 668265.263) * 43758.5453
                    h = h - math.floor(h)
                    if h > prob:
                        continue
                    # Gradual tectonic sinking towards outer lava sea
                    sink = (t_dist ** 1.35) * 0.42
                    col_w = 0.92 - t_dist * 0.12
                else:
                    sink = 0.0
                    col_w = 0.92

                pos_x = float(gx)
                pos_z = -float(gy)

                base_top_y_local = base_top_y - sink
                base_h = base_top_y_local - col_h / 2.0

                # Atmospheric depth fog: smooth radial falloff into the void
                fog_factor = max(0.0, min(1.0, 1.0 - (dist / outer_radius) ** 1.25))

                # Subdued volcanic basalt tone (serves purely as backdrop)
                r = 0.024 + 0.038 * fog_factor
                g = 0.024 + 0.040 * fog_factor
                b = 0.032 + 0.050 * fog_factor
                col_color = color.rgba(r, g, b, 1.0)

                # Monolithic pillar cube with crisp beveled texture
                col_ent = Entity(
                    parent=self,
                    model='cube',
                    texture=_TILE_TEX,
                    position=(pos_x, base_h, pos_z),
                    scale=(col_w, col_h, col_w),
                    color=col_color,
                    name=f"col_{gx}_{gy}",
                )

                # Deterministic pseudo-random pop cycle parameters per column
                seed = math.sin(pos_x * 12.9898 + pos_z * 78.233) * 43758.5453
                seed = seed - math.floor(seed)
                period = 8.0 + seed * 14.0       # 8 to 22 seconds between pops
                pop_dur = 2.4 + seed * 1.6       # 2.4 to 4.0 seconds duration
                offset = seed * 30.0             # Staggered offsets
                pop_h = 0.35 + seed * 0.40       # Rise height: 0.35 to 0.75 units

                self.columns.append((col_ent, base_h, pos_x, pos_z))
                self.column_base_colors.append((r, g, b))
                self.column_pop_params.append((period, pop_dur, offset, pop_h))

    def update(self):
        """Per-frame loop: flowing Cyberpunk Lava Sea + sporadic column popping with molten glow."""
        dt = time.dt
        if dt <= 0.0:
            return

        self._time += dt
        t = self._time

        # 1. Flowing Cyberpunk Lava Sea animation
        if self.lava_plane:
            # Flowing molten magma current
            self.lava_plane.texture_offset = (t * 0.010, t * 0.007)
            # Radiant heat pulse (warm cyber neon lava glow)
            heat_pulse = 0.72 + 0.10 * math.sin(t * 1.5)
            self.lava_plane.color = color.rgba(heat_pulse * 0.65, heat_pulse * 0.38, heat_pulse * 0.25, 0.85)
            self.lava_plane.y = -1.7505 + 0.03 * math.sin(t * 1.1)

        if self.lava_plane_deep:
            self.lava_plane_deep.texture_offset = (-t * 0.006, t * 0.008)
            self.lava_plane_deep.y = -1.95 + 0.02 * math.sin(t * 0.9)

        # 2. Mostly static background columns with sporadic asynchronous popping & radiant thermal uplift
        if self.columns:
            has_colors = len(self.column_base_colors) == len(self.columns)
            for i, (col, base_h, px, pz) in enumerate(self.columns):
                period, pop_dur, offset, pop_h = self.column_pop_params[i]
                t_local = (t + offset) % period
                if t_local < pop_dur:
                    # Silky-smooth bell-shaped pop curve: rises, lingers at apex, smoothly settles
                    p = t_local / pop_dur
                    rise = math.sin(p * math.pi) ** 2
                    col.y = base_h + pop_h * rise

                    # Dynamic incandescent molten glow as column emerges from magma!
                    if has_colors:
                        r, g, b = self.column_base_colors[i]
                        heat = rise * 0.14
                        col.color = color.rgba(
                            min(1.0, r + heat * 0.85),
                            min(1.0, g + heat * 0.22),
                            min(1.0, b + heat * 0.08),
                            1.0
                        )
                else:
                    if col.y != base_h:
                        col.y = base_h
                        if has_colors:
                            r, g, b = self.column_base_colors[i]
                            col.color = color.rgba(r, g, b, 1.0)
