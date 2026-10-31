"""3D Block representation and frame-perfect delta-time rolling animations.

Features:
- Kinetic roll easing (smooth acceleration, fast turnover, crisp snap)
- Ghost echo trail emission on roll takeoff
- Ground impact cushion and dust spark emission on landing
- Black hole suction & dual wormhole ballistic flight for teleport split/merge
- Physical see-saw torque tilt on cantilever overhangs, fragile collapse, and void tumble
- Victory vortex swirl and confetti celebration
- Dual modular titanium textured cube skin restoring Bao's cyber aesthetic
"""

import math
import random
from pathlib import Path
from typing import Callable, Optional, Tuple, Any, List
from ursina import Entity, Vec3, color, time, Texture

from bloxorz.core.constants import Direction, BlockOrientation
from bloxorz.core.block.base import BaseBlockState
from bloxorz.ui.theme import Palette, Motion, ColorToken
from bloxorz.config import CONFIG
from bloxorz.graphics.fx_manager import FXManager
from bloxorz.graphics.camera_ctrl import CameraController
from bloxorz.audio.sound_manager import play_sfx

_CYBER_TEX_PATH = Path(__file__).resolve().parent.parent / "assets" / "textures" / "cyber_titanium.png"
_CYBER_TEX = Texture(str(_CYBER_TEX_PATH)) if _CYBER_TEX_PATH.exists() else None

_TEX_PATH = Path(__file__).resolve().parent.parent / "assets" / "textures" / "tile_bevel.png"
_TILE_TEX = Texture(str(_TEX_PATH)) if _TEX_PATH.exists() else None

_BLOCK_TEX = _CYBER_TEX or _TILE_TEX


def _evaluate_roll_curve(p: float) -> float:
    """Authentic Bloxpath kinematic roll curve: smooth acceleration from rest, fast turnover, crisp snap."""
    return p * p * (3.0 - 2.0 * p)


class BlockView(Entity):
    """Manages 3D block mesh with frame-perfect delta-time rotation and physical VFX juice."""

    @classmethod
    def _get_block_color(cls) -> color.Color:
        """Returns the titanium hero block color from shared Palette tokens."""
        return color.hex(Palette.BLOCK_CORE.hex_code)

    @classmethod
    def _get_active_split_color(cls) -> color.Color:
        """Returns the bright white titanium token for the active split cube."""
        return color.hex(Palette.BLOCK_SPLIT_ACTIVE.hex_code)

    @classmethod
    def _get_passive_split_color(cls) -> color.Color:
        """Returns the dimmed slate titanium token for the passive split cube."""
        return color.hex(Palette.BLOCK_SPLIT_PASSIVE.hex_code)

    def _set_mesh_visible(self, vis: bool) -> None:
        """Sets visibility for parent mesh container and modular subcubes."""
        self.mesh.visible = vis
        if hasattr(self, "mesh_cube_1") and self.mesh_cube_1:
            self.mesh_cube_1.visible = vis
        if hasattr(self, "mesh_cube_2") and self.mesh_cube_2:
            self.mesh_cube_2.visible = vis

    def _set_mesh_color(self, c: color.Color) -> None:
        """Propagates color tint to parent mesh container and modular subcubes."""
        self.mesh.color = c
        if hasattr(self, "mesh_cube_1") and self.mesh_cube_1:
            self.mesh_cube_1.color = c
        if hasattr(self, "mesh_cube_2") and self.mesh_cube_2:
            self.mesh_cube_2.color = c

    def _update_subcubes_layout(self, dim: Tuple[float, float, float]) -> None:
        """Arranges dual modular 1x1x1 subcubes along the primary axis of orientation."""
        if not hasattr(self, "mesh_cube_1") or not self.mesh_cube_1:
            return
        if dim[0] > 1.5:  # LYING_X: horizontal along X axis
            self.mesh_cube_1.position = Vec3(-0.5, 0, 0)
            self.mesh_cube_2.position = Vec3(0.5, 0, 0)
        elif dim[1] > 1.5:  # LYING_Y: horizontal along Z axis (depth in Ursina)
            self.mesh_cube_1.position = Vec3(0, 0, -0.5)
            self.mesh_cube_2.position = Vec3(0, 0, 0.5)
        else:  # STANDING: vertical along Y axis (elevation in Ursina)
            self.mesh_cube_1.position = Vec3(0, -0.5, 0)
            self.mesh_cube_2.position = Vec3(0, 0.5, 0)

    def __init__(self):
        super().__init__(name="block_view_controller")
        c_block = self._get_block_color()

        # Permanent Pivot Entity: all rolling transformations occur on this pivot
        self.pivot = Entity(parent=self, name="block_pivot")

        # The Visual Mesh is permanently parented to the pivot (zero reparenting, zero flick).
        # Constructed with dual modular 1x1x1 subcubes to ensure distortion-free 1:1 UV mapping
        # on all faces and an authentic cyber division seam line.
        self.mesh = Entity(
            parent=self.pivot,
            name="block_mesh",
        )

        u1 = getattr(CONFIG.block, "unit_scale_1", 0.94)
        sub_scale = Vec3(u1, u1, u1)

        self.mesh_cube_1 = Entity(
            parent=self.mesh,
            name="block_subcube_1",
            model='cube',
            texture=_BLOCK_TEX,
            color=c_block,
            scale=sub_scale,
        )
        self.mesh_cube_2 = Entity(
            parent=self.mesh,
            name="block_subcube_2",
            model='cube',
            texture=_BLOCK_TEX,
            color=c_block,
            scale=sub_scale,
        )
        self._update_subcubes_layout((1, 1, 2))

        # Dual 1x1x1 split cubes for teleport mechanics
        c_active = self._get_active_split_color()
        c_passive = self._get_passive_split_color()

        self.split_mesh_1 = Entity(
            parent=self,
            name="split_cube_1",
            model='cube',
            texture=_BLOCK_TEX,
            color=c_active,
            scale=sub_scale,
            visible=False,
        )
        self.split_mesh_2 = Entity(
            parent=self,
            name="split_cube_2",
            model='cube',
            texture=_BLOCK_TEX,
            color=c_passive,
            scale=sub_scale,
            visible=False,
        )

        self.current_state: Optional[BaseBlockState] = None
        self.board_view: Optional[Any] = None
        self.is_animating: bool = False

        # Delta-time roll state
        self._is_rolling: bool = False
        self._roll_progress: float = 0.0
        self._roll_axis: str = "z"
        self._roll_angle: float = 0.0
        self._on_roll_complete: Optional[Callable[[], None]] = None

        # Landing micro-bounce & squash state
        self._is_landing_bounce: bool = False
        self._landing_bounce_time: float = 0.0
        self._landing_bounce_duration: float = 0.10
        self._landing_bounce_offset: float = 0.0
        self._landing_squash_y: float = 1.0
        self._landing_stretch_xz: float = 1.0

        # Fall animation state (Physical see-saw, fragile plunge, edge tumble)
        self._is_falling: bool = False
        self._fall_time: float = 0.0
        self._is_seesaw: bool = False
        self._seesaw_phase: int = 1
        self._seesaw_axis: str = "z"
        self._tilt_sign: float = 1.0
        self._current_tilt_angle: float = 0.0
        self._angular_velocity: float = 0.0
        self._fall_velocity_y: float = 0.0
        self._fall_velocity_horiz: Vec3 = Vec3(0, 0, 0)
        self._fall_axis: str = "z"
        self._fall_mode: str = "DIRECT"
        self._falling_split_cube: Optional[Entity] = None
        self._on_fall_complete: Optional[Callable[[], None]] = None
        self._roll_outcome: str = "SAFE"
        self._roll_board: Optional[Any] = None
        self._roll_direction: Optional[Direction] = None
        self._cube_roll_outcome: str = "SAFE"
        self._cube_roll_board: Optional[Any] = None
        self._cube_roll_direction: Optional[Direction] = None

        # Victory goal plunge animation state
        self._is_sinking_victory: bool = False
        self._victory_time: float = 0.0
        self._on_victory_complete: Optional[Callable[[], None]] = None

        # Teleport split aerial flight animation state
        self._is_teleporting: bool = False
        self._teleport_time: float = 0.0
        self._teleport_duration: float = Motion.TELEPORT_FLIGHT_DURATION
        self._teleport_src: Tuple[float, float] = (0.0, 0.0)
        self._teleport_dst_1: Tuple[float, float] = (0.0, 0.0)
        self._teleport_dst_2: Tuple[float, float] = (0.0, 0.0)
        self._teleport_final_state: Optional[BaseBlockState] = None
        self._on_teleport_complete: Optional[Callable[[], None]] = None
        self._teleport_spark_timer: float = 0.0
        self._teleport_has_landed: bool = False

        # 1x1x1 cube edge-pivot rolling animation state
        self._is_cube_rolling: bool = False
        self._cube_roll_progress: float = 0.0
        self._cube_rolling_mesh: Optional[Entity] = None
        self._cube_pivot_pos: Vec3 = Vec3(0, 0, 0)
        self._cube_delta_pos: Vec3 = Vec3(0, 0, 0)
        self._cube_rot_axis: str = "z"
        self._cube_rot_angle: float = 0.0
        self._on_cube_roll_complete: Optional[Callable[[], None]] = None

        # Pre-allocated Black Hole Singularity & Dual Wormhole VFX Entities
        self._teleport_pad_src = Entity(
            name="tp_pad_src",
            model='circle',
            rotation_x=90,
            scale=Vec3(1.25, 1.25, 1.0),
            color=color.rgba(0.01, 0.0, 0.02, 1.0),
            unlit=True,
            visible=False,
        )
        self._teleport_pad_dst1 = Entity(
            name="tp_pad_dst1",
            model='circle',
            rotation_x=90,
            scale=Vec3(1.25, 1.25, 1.0),
            color=color.rgba(0.01, 0.0, 0.02, 1.0),
            unlit=True,
            visible=False,
        )
        self._teleport_pad_dst2 = Entity(
            name="tp_pad_dst2",
            model='circle',
            rotation_x=90,
            scale=Vec3(1.25, 1.25, 1.0),
            color=color.rgba(0.01, 0.0, 0.02, 1.0),
            unlit=True,
            visible=False,
        )

        # Cross-quad vertical columns of light (Source, Dest 1, Dest 2)
        self._teleport_beam_src = self._build_cross_beam("tp_beam_src", Palette.TELEPORT_BEAM)
        self._teleport_beam_dst1 = self._build_cross_beam("tp_beam_dst1", Palette.TELEPORT_BEAM_DST)
        self._teleport_beam_dst2 = self._build_cross_beam("tp_beam_dst2", Palette.TELEPORT_BEAM_DST)

        # High-contrast glowing accretion rims around black holes
        self._teleport_ring_1 = Entity(
            name="tp_ring_1",
            model='circle',
            rotation_x=90,
            scale=Vec3(1.48, 1.48, 1.0),
            color=color.hex("#D946EF"),
            unlit=True,
            visible=False,
        )
        self._teleport_ring_2 = Entity(
            name="tp_ring_2",
            model='circle',
            rotation_x=90,
            scale=Vec3(1.72, 1.72, 1.0),
            color=color.hex("#00F0FF"),
            unlit=True,
            visible=False,
        )
        self._teleport_ring_dst1 = Entity(
            name="tp_ring_dst1",
            model='circle',
            rotation_x=90,
            scale=Vec3(1.48, 1.48, 1.0),
            color=color.hex("#D946EF"),
            unlit=True,
            visible=False,
        )
        self._teleport_ring_dst2 = Entity(
            name="tp_ring_dst2",
            model='circle',
            rotation_x=90,
            scale=Vec3(1.48, 1.48, 1.0),
            color=color.hex("#D946EF"),
            unlit=True,
            visible=False,
        )

        # Keep teleport effects in the same board-local frame as the block.
        for name, entity in vars(self).items():
            if name.startswith("_teleport_") and isinstance(entity, Entity):
                entity.parent = self

    @staticmethod
    def _build_cross_beam(name: str, token: ColorToken) -> Entity:
        """Constructs an unlit double-quad intersecting vertical pillar of light."""
        root = Entity(name=name, visible=False)
        c = color.rgba(token.r, token.g, token.b, token.a)
        Entity(parent=root, model='quad', scale=Vec3(0.80, 14.0, 1.0), unlit=True, color=c)
        Entity(parent=root, model='quad', scale=Vec3(0.80, 14.0, 1.0), rotation_y=90, unlit=True, color=c)
        return root

    def _hide_teleport_fx(self) -> None:
        """Hides all active teleport light pillars, rings, and pads."""
        if hasattr(self, "_teleport_pad_src"):
            self._teleport_pad_src.visible = False
            self._teleport_pad_dst1.visible = False
            self._teleport_pad_dst2.visible = False
            self._teleport_beam_src.visible = False
            self._teleport_beam_dst1.visible = False
            self._teleport_beam_dst2.visible = False
            self._teleport_ring_1.visible = False
            self._teleport_ring_2.visible = False
            if hasattr(self, "_teleport_ring_dst1"):
                self._teleport_ring_dst1.visible = False
                self._teleport_ring_dst2.visible = False

    def set_board_view(self, board_view: Any) -> None:
        """Connects board view to enable dynamic wave ground anchor tracking."""
        self.board_view = board_view

    def _get_surface_y(self, grid_x: float, grid_y: float) -> float:
        """Queries active board view for surface elevation (returns 0.0 on static floor)."""
        bv = self.board_view
        if bv is None:
            from bloxorz.graphics.board_view import BoardView
            bv = BoardView.get_instance()
        if bv is not None and hasattr(bv, "get_surface_y"):
            return bv.get_surface_y(grid_x, grid_y)
        return 0.0

    @staticmethod
    def _compute_scale(dim: Tuple[float, float, float]) -> Vec3:
        """Calculates visual scale based on unit dimensions configured in config."""
        u1 = CONFIG.block.unit_scale_1
        u2 = CONFIG.block.unit_scale_2
        sx = u2 if dim[0] > 1.5 else u1
        sy = u2 if dim[2] > 1.5 else u1  # Height along Y in Ursina
        sz = u2 if dim[1] > 1.5 else u1  # Depth along Z in Ursina
        return Vec3(sx, sy, sz)

    def _trigger_landing(self) -> None:
        """Triggers subtle squash & stretch micro-bounce upon landing on tiles."""
        self._is_landing_bounce = True
        self._landing_bounce_time = 0.0

    def _spawn_landing_dust(self, cells: Optional[List[Tuple[int, int]]] = None) -> None:
        """Spawns radiant incandescent fire ash sparks streaking outward upon touchdown."""
        fx = FXManager.get_instance() if FXManager._instance else None
        if not fx:
            return

        target_cells = cells
        if target_cells is None and self.current_state:
            target_cells = self.current_state.occupied_cells

        if not target_cells:
            return

        ash_tokens = [
            Palette.EMBER_ASH,
            Palette.EMBER_ASH_GLOW,
            Palette.EMBER_ASH_SPARK,
        ]

        for (cx, cy) in target_cells:
            surf_y = self._get_surface_y(float(cx), float(cy))
            for _ in range(6):
                ang = random.uniform(0, math.tau)
                rad = random.uniform(0.48, 0.65)
                cos_a = math.cos(ang)
                sin_a = math.sin(ang)
                px = float(cx) + cos_a * rad
                pz = -float(cy) + sin_a * rad
                pos = Vec3(px, surf_y + 0.04, pz)
                out_dir = Vec3(cos_a, 0.0, sin_a)
                fx.spawn_ember_ash(
                    position=pos,
                    count=1,
                    tokens=ash_tokens,
                    outward_dir=out_dir,
                    speed=3.2,
                    life=0.45,
                )

    def sync_to_state(self, state: BaseBlockState, clear_fx: bool = True):
        """Immediately snaps the 3D block to the given state without animation."""
        self.current_state = state
        self.is_animating = False
        self._is_rolling = False
        self._is_falling = False
        self._is_seesaw = False
        self._fall_mode = "DIRECT"
        self._fall_velocity_y = 0.0
        self._fall_velocity_horiz = Vec3(0, 0, 0)
        self._falling_split_cube = None
        self._is_sinking_victory = False
        self._is_teleporting = False
        self._on_teleport_complete = None
        self._teleport_final_state = None
        self._is_cube_rolling = False
        self._cube_rolling_mesh = None
        self._on_cube_roll_complete = None
        self._hide_teleport_fx()

        # Reset landing squash
        self._is_landing_bounce = False
        self._landing_bounce_offset = 0.0
        self._landing_squash_y = 1.0
        self._landing_stretch_xz = 1.0

        if clear_fx:
            fx = FXManager.get_instance() if FXManager._instance else None
            if fx:
                fx.clear_all()

        # Restore full core material opacity & color
        c_active = self._get_active_split_color()
        c_passive = self._get_passive_split_color()
        self._set_mesh_color(self._get_block_color())

        if getattr(state, "is_split", False):
            self._set_mesh_visible(False)
            self.pivot.visible = False
            self.split_mesh_1.visible = True
            self.split_mesh_2.visible = True

            u1 = CONFIG.block.unit_scale_1
            half_u1 = u1 / 2.0

            b1 = getattr(state, "b1")
            b2 = getattr(state, "b2")

            y1 = half_u1 + self._get_surface_y(float(b1.x), float(b1.y))
            y2 = half_u1 + self._get_surface_y(float(b2.x), float(b2.y))

            self.split_mesh_1.position = Vec3(float(b1.x), y1, -float(b1.y))
            self.split_mesh_1.rotation = Vec3(0, 0, 0)
            self.split_mesh_1.scale = Vec3(u1, u1, u1)

            self.split_mesh_2.position = Vec3(float(b2.x), y2, -float(b2.y))
            self.split_mesh_2.rotation = Vec3(0, 0, 0)
            self.split_mesh_2.scale = Vec3(u1, u1, u1)

            if getattr(state, "active_index", 0) == 0:
                self.split_mesh_1.color = c_active
                self.split_mesh_2.color = c_passive
            else:
                self.split_mesh_1.color = c_passive
                self.split_mesh_2.color = c_active
            return

        # Monolithic block configuration
        self.split_mesh_1.visible = False
        self.split_mesh_2.visible = False

        center = state.get_center_3d()
        dim = state.get_dimensions_3d()

        wave_y = self._get_surface_y(float(center[0]), float(center[1]))
        world_center = Vec3(float(center[0]), float(center[2]) + wave_y, -float(center[1]))

        self.pivot.position = world_center
        self.pivot.rotation = Vec3(0, 0, 0)
        self.pivot.visible = True

        self.mesh.position = Vec3(0, 0, 0)
        self.mesh.rotation = Vec3(0, 0, 0)
        self.mesh.scale = Vec3(1, 1, 1)
        self._update_subcubes_layout(dim)
        self._set_mesh_visible(True)
        self._set_mesh_color(self._get_block_color())

    def _start_cube_roll(
        self,
        cube: Entity,
        src_x: int,
        src_y: int,
        direction: Direction,
        on_complete: Optional[Callable[[], None]] = None,
        outcome: str = "SAFE",
        board: Optional[Any] = None,
    ):
        """Initiates physical 90-degree edge-pivot rolling rotation for a single 1x1x1 cube."""
        self.is_animating = True
        self._is_cube_rolling = True
        self._cube_roll_progress = 0.0
        self._cube_rolling_mesh = cube
        self._on_cube_roll_complete = on_complete
        self._cube_roll_outcome = outcome
        self._cube_roll_board = board
        self._cube_roll_direction = direction

        u1 = CONFIG.block.unit_scale_1
        half_u1 = u1 / 2.0
        world_x = float(src_x)
        world_z = -float(src_y)
        ground_y = self._get_surface_y(world_x, float(src_y))

        if direction == Direction.RIGHT:
            pivot = Vec3(world_x + 0.5, ground_y, world_z)
            delta = Vec3(-0.5, half_u1, 0.0)
            axis = "z"
            angle = 90.0
        elif direction == Direction.LEFT:
            pivot = Vec3(world_x - 0.5, ground_y, world_z)
            delta = Vec3(0.5, half_u1, 0.0)
            axis = "z"
            angle = -90.0
        elif direction == Direction.UP:
            pivot = Vec3(world_x, ground_y, world_z + 0.5)
            delta = Vec3(0.0, half_u1, -0.5)
            axis = "x"
            angle = 90.0
        elif direction == Direction.DOWN:
            pivot = Vec3(world_x, ground_y, world_z - 0.5)
            delta = Vec3(0.0, half_u1, 0.5)
            axis = "x"
            angle = -90.0
        else:
            self.is_animating = False
            self._is_cube_rolling = False
            if on_complete:
                on_complete()
            return

        self._cube_pivot_pos = pivot
        self._cube_delta_pos = delta
        self._cube_rot_axis = axis
        self._cube_rot_angle = angle

    def animate_teleport_split(
        self,
        standing_state: BaseBlockState,
        split_state: BaseBlockState,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """Initiates a cinematic black hole suction & dual wormhole ballistic ejection sequence."""
        self.is_animating = True
        self._is_rolling = False
        self._is_falling = False
        self._is_sinking_victory = False
        self._is_teleporting = True
        self._teleport_time = 0.0
        self._teleport_spark_timer = 0.0
        self._teleport_duration = getattr(CONFIG.motion, "teleport_flight_duration", 1.10)
        self._teleport_has_landed = False

        c = standing_state.get_center_3d()
        x_src, y_src = float(c[0]), float(c[1])

        b1 = getattr(split_state, "b1")
        b2 = getattr(split_state, "b2")

        self._teleport_src = (x_src, y_src)
        self._teleport_dst_1 = (float(b1.x), float(b1.y))
        self._teleport_dst_2 = (float(b2.x), float(b2.y))
        self._teleport_final_state = split_state
        self._on_teleport_complete = on_complete

        surf_y_src = self._get_surface_y(x_src, y_src)

        # Monolithic block stays standing at the source tile during Phase 1
        dim = standing_state.get_dimensions_3d()
        self.pivot.position = Vec3(x_src, float(c[2]) + surf_y_src, -y_src)
        self.pivot.rotation = Vec3(0, 0, 0)
        self.pivot.visible = True
        self.mesh.position = Vec3(0, 0, 0)
        self.mesh.rotation = Vec3(0, 0, 0)
        self.mesh.scale = Vec3(1, 1, 1)
        self._update_subcubes_layout(dim)
        self._set_mesh_visible(True)
        self._set_mesh_color(self._get_block_color())

        # Hide split meshes initially
        self.split_mesh_1.visible = False
        self.split_mesh_2.visible = False
        u1 = CONFIG.block.unit_scale_1
        self.split_mesh_1.scale = Vec3(u1, u1, u1)
        self.split_mesh_2.scale = Vec3(u1, u1, u1)

        c_active = self._get_active_split_color()
        c_passive = self._get_passive_split_color()
        if getattr(split_state, "active_index", 0) == 0:
            self.split_mesh_1.color = c_active
            self.split_mesh_2.color = c_passive
        else:
            self.split_mesh_1.color = c_passive
            self.split_mesh_2.color = c_active

        # Phase 1: Activate black hole singularity vortex directly under the block's foot
        self._teleport_ring_2.position = Vec3(x_src, surf_y_src + 0.015, -y_src)
        self._teleport_ring_2.scale = Vec3(0.2, 0.2, 1.0)
        self._teleport_ring_2.visible = True

        self._teleport_ring_1.position = Vec3(x_src, surf_y_src + 0.020, -y_src)
        self._teleport_ring_1.scale = Vec3(0.18, 0.18, 1.0)
        self._teleport_ring_1.visible = True

        self._teleport_pad_src.position = Vec3(x_src, surf_y_src + 0.025, -y_src)
        self._teleport_pad_src.scale = Vec3(0.15, 0.15, 1.0)
        self._teleport_pad_src.color = color.rgba(0.01, 0.0, 0.02, 1.0)
        self._teleport_pad_src.visible = True

        # Ensure destination entities and beams are hidden at start
        self._teleport_beam_src.visible = False
        self._teleport_beam_dst1.visible = False
        self._teleport_beam_dst2.visible = False
        self._teleport_pad_dst1.visible = False
        self._teleport_pad_dst2.visible = False
        if hasattr(self, "_teleport_ring_dst1"):
            self._teleport_ring_dst1.visible = False
            self._teleport_ring_dst2.visible = False

        # Play futuristic teleport SFX
        play_sfx("teleport")

        fx = FXManager.get_instance() if FXManager._instance else None
        if fx:
            fx.spawn_particles(
                Vec3(x_src, surf_y_src + 0.2, -y_src),
                count=10,
                token=Palette.TELEPORT_ENERGY,
                speed=2.2,
                life=0.35,
            )

    def roll_animated(
        self,
        prev_state: BaseBlockState,
        next_state: BaseBlockState,
        direction: Direction,
        on_complete: Optional[Callable[[], None]] = None,
        on_split_takeoff: Optional[Callable[[], None]] = None,
        outcome: str = "SAFE",
        board: Optional[Any] = None,
    ):
        """Initiates a smooth roll along the contact pivot edge using the per-frame update loop."""
        self._roll_outcome = outcome
        self._roll_board = board
        self._roll_direction = direction

        # Case A: Monolithic block steps onto teleport tile and splits!
        if not getattr(prev_state, "is_split", False) and getattr(next_state, "is_split", False):
            standing_state = prev_state.roll(direction)

            def start_split():
                if on_split_takeoff:
                    on_split_takeoff()
                self.animate_teleport_split(
                    standing_state, next_state, on_complete=on_complete
                )

            self.roll_animated(
                prev_state,
                standing_state,
                direction,
                on_complete=start_split,
                outcome=outcome,
                board=board,
            )
            return

        # Case B: Dual cubes merging into monolithic block!
        if getattr(prev_state, "is_split", False) and not getattr(next_state, "is_split", False):
            self.current_state = next_state
            cube = (
                self.split_mesh_1
                if getattr(prev_state, "active_index", 0) == 0
                else self.split_mesh_2
            )
            act_prev = getattr(prev_state, "active_block")

            def finish_merge():
                play_sfx("merge")
                self.sync_to_state(next_state, clear_fx=False)
                self._spawn_landing_dust()
                if on_complete:
                    on_complete()

            self._start_cube_roll(
                cube,
                act_prev.x,
                act_prev.y,
                direction,
                on_complete=finish_merge,
                outcome=outcome,
                board=board,
            )
            return

        # Case C: Single active cube moving in split state
        if getattr(prev_state, "is_split", False) and getattr(next_state, "is_split", False):
            self.current_state = next_state
            cube = (
                self.split_mesh_1
                if getattr(prev_state, "active_index", 0) == 0
                else self.split_mesh_2
            )
            act_prev = getattr(prev_state, "active_block")

            def finish_cube_move():
                self.sync_to_state(next_state, clear_fx=False)
                if on_complete:
                    on_complete()

            self._start_cube_roll(
                cube,
                act_prev.x,
                act_prev.y,
                direction,
                on_complete=finish_cube_move,
                outcome=outcome,
                board=board,
            )
            return

        # Case D: Standard monolithic 1x1x2 block rolling
        self.is_animating = True
        self.current_state = next_state

        c_prev = prev_state.get_center_3d()
        dim_prev = prev_state.get_dimensions_3d()

        wave_prev = self._get_surface_y(float(c_prev[0]), float(c_prev[1]))
        center_world = Vec3(float(c_prev[0]), float(c_prev[2]) + wave_prev, -float(c_prev[1]))
        half_x = dim_prev[0] / 2.0
        half_y = dim_prev[1] / 2.0  # Grid Y -> Ursina Z

        # Spawn ghost echo trail at previous roll orientation
        fx = FXManager.get_instance()
        fx.spawn_ghost(self.pivot.position, self.pivot.rotation, self._compute_scale(dim_prev))

        # Compute exact contact edge pivot
        if direction == Direction.RIGHT:
            edge_x = center_world.x + half_x
            edge_z = center_world.z
            edge_y = self._get_surface_y(edge_x, -edge_z)
            pivot_pos = Vec3(edge_x, edge_y, edge_z)
            rot_axis = "z"
            rot_angle = 90.0
        elif direction == Direction.LEFT:
            edge_x = center_world.x - half_x
            edge_z = center_world.z
            edge_y = self._get_surface_y(edge_x, -edge_z)
            pivot_pos = Vec3(edge_x, edge_y, edge_z)
            rot_axis = "z"
            rot_angle = -90.0
        elif direction == Direction.DOWN:  # South (-Z in Ursina)
            edge_x = center_world.x
            edge_z = center_world.z - half_y
            edge_y = self._get_surface_y(edge_x, -edge_z)
            pivot_pos = Vec3(edge_x, edge_y, edge_z)
            rot_axis = "x"
            rot_angle = -90.0
        elif direction == Direction.UP:    # North (+Z in Ursina)
            edge_x = center_world.x
            edge_z = center_world.z + half_y
            edge_y = self._get_surface_y(edge_x, -edge_z)
            pivot_pos = Vec3(edge_x, edge_y, edge_z)
            rot_axis = "x"
            rot_angle = 90.0
        else:
            self.is_animating = False
            self.sync_to_state(next_state, clear_fx=False)
            if on_complete:
                on_complete()
            return

        # 1. Place pivot at contact edge
        self.pivot.position = pivot_pos
        self.pivot.rotation = Vec3(0, 0, 0)

        # 2. Offset mesh locally so its initial world position is continuous (0-pixel shift)
        self.mesh.position = center_world - pivot_pos
        self.mesh.rotation = Vec3(0, 0, 0)
        self.mesh.scale = Vec3(1, 1, 1)
        self._update_subcubes_layout(dim_prev)

        # 3. Setup delta-time animation variables
        self._roll_axis = rot_axis
        self._roll_angle = rot_angle
        self._roll_progress = 0.0
        self._on_roll_complete = on_complete
        self._is_rolling = True

    def animate_fall(
        self,
        board: Optional[Any] = None,
        direction: Optional[Direction] = None,
        on_complete: Optional[Callable[[], None]] = None,
        outcome: Optional[str] = None,
    ):
        """Initiates physical torque-based tipping, fragile drop, or parabolic tumble into the abyss."""
        self.is_animating = True
        self._is_rolling = False
        self._is_falling = True
        self._fall_time = 0.0
        self._on_fall_complete = on_complete

        # Screen shake on collapse / fall initiation
        cam = CameraController.get_instance()
        if cam:
            cam.shake_camera(intensity=getattr(CONFIG.animation, "shake_intensity_impact", 0.08))

        # Check for split state cube fall
        if self.current_state and getattr(self.current_state, "is_split", False):
            self._is_seesaw = False
            self._fall_time = 0.0
            self._fall_mode = "TUMBLE"
            act_idx = getattr(self.current_state, "active_index", 0)
            self._falling_split_cube = self.split_mesh_1 if act_idx == 0 else self.split_mesh_2
            horiz_speed = 1.8
            spin_speed = 360.0
            if direction == Direction.RIGHT:
                self._fall_velocity_horiz = Vec3(horiz_speed, 0, 0)
                self._angular_velocity = spin_speed
                self._fall_axis = "z"
            elif direction == Direction.LEFT:
                self._fall_velocity_horiz = Vec3(-horiz_speed, 0, 0)
                self._angular_velocity = -spin_speed
                self._fall_axis = "z"
            elif direction == Direction.UP:
                self._fall_velocity_horiz = Vec3(0, 0, horiz_speed)
                self._angular_velocity = spin_speed
                self._fall_axis = "x"
            elif direction == Direction.DOWN:
                self._fall_velocity_horiz = Vec3(0, 0, -horiz_speed)
                self._angular_velocity = -spin_speed
                self._fall_axis = "x"
            else:
                self._fall_velocity_horiz = Vec3(0, 0, 0)
                self._angular_velocity = 0.0
                self._fall_axis = "z"
            self._fall_velocity_y = 2.0
            return

        # Case 1: Fragile Tile Collapse (Straight vertical gravity plunge through hole)
        if outcome == "FELL_FRAGILE":
            self._is_seesaw = False
            self._fall_mode = "FRAGILE"
            self._fall_velocity_y = 0.0
            self._fall_velocity_horiz = Vec3(0, 0, 0)
            self._angular_velocity = 0.0
            self._fall_axis = "z"
            return

        # Case 2: Standard cantilever check (1 supported tile, 1 overhanging tile on 1x2 block)
        if board and self.current_state:
            supported = [
                (cx, cy) for (cx, cy) in self.current_state.occupied_cells
                if board.is_tile_walkable(board.get_tile(cx, cy))
            ]
            if len(supported) == 1 and self.current_state.orientation != BlockOrientation.STANDING:
                supp_x, supp_y = supported[0]
                void_cells = [
                    (cx, cy) for (cx, cy) in self.current_state.occupied_cells
                    if (cx, cy) != (supp_x, supp_y)
                ]
                void_x, void_y = void_cells[0]

                # Tile world positions (Ursina X = grid X, Ursina Z = -grid Y)
                supp_world = Vec3(float(supp_x), 0.0, -float(supp_y))
                void_world = Vec3(float(void_x), 0.0, -float(void_y))
                ground_y = self._get_surface_y(float(supp_x), float(supp_y))
                dim = self.current_state.get_dimensions_3d()
                c_center = self.current_state.get_center_3d()
                wave_center = self._get_surface_y(float(c_center[0]), float(c_center[1]))
                center_world = Vec3(float(c_center[0]), float(c_center[2]) + wave_center, -float(c_center[1]))

                # Determine overhanging edge fulcrum & exact physical tilt direction
                if self.current_state.orientation == BlockOrientation.LYING_X:
                    overhang_dir = 1.0 if void_world.x > supp_world.x else -1.0
                    edge_pos = Vec3(supp_world.x + overhang_dir * 0.5, ground_y, supp_world.z)
                    self._seesaw_axis = "z"
                    self._tilt_sign = overhang_dir  # +X -> +tilt (down into void), -X -> -tilt
                    self._is_seesaw = True
                elif self.current_state.orientation == BlockOrientation.LYING_Y:
                    overhang_dir_z = 1.0 if void_world.z > supp_world.z else -1.0
                    edge_pos = Vec3(supp_world.x, ground_y, supp_world.z + overhang_dir_z * 0.5)
                    self._seesaw_axis = "x"
                    self._tilt_sign = overhang_dir_z  # +Z (North) -> +tilt, -Z (South) -> -tilt
                    self._is_seesaw = True

                if self._is_seesaw:
                    self._seesaw_phase = 1
                    self._fall_mode = "CANTILEVER"
                    self._current_tilt_angle = 0.0
                    self.pivot.position = edge_pos
                    self.pivot.rotation = Vec3(0, 0, 0)
                    self.mesh.position = center_world - edge_pos
                    self.mesh.rotation = Vec3(0, 0, 0)
                    self.mesh.scale = Vec3(1, 1, 1)
                    self._update_subcubes_layout(dim)
                    self._angular_velocity = self._tilt_sign * 35.0
                    return

        # Case 3: Seamless Tumble fall off edge into empty space (0 supported tiles)
        self._is_seesaw = False
        self._fall_mode = "TUMBLE"
        self._fall_velocity_y = 2.0

        horiz_speed = 2.0
        spin_speed = 360.0

        if direction == Direction.RIGHT:
            self._fall_velocity_horiz = Vec3(horiz_speed, 0, 0)
            self._angular_velocity = spin_speed
            self._fall_axis = "z"
        elif direction == Direction.LEFT:
            self._fall_velocity_horiz = Vec3(-horiz_speed, 0, 0)
            self._angular_velocity = -spin_speed
            self._fall_axis = "z"
        elif direction == Direction.UP:
            self._fall_velocity_horiz = Vec3(0, 0, horiz_speed)
            self._angular_velocity = spin_speed
            self._fall_axis = "x"
        elif direction == Direction.DOWN:
            self._fall_velocity_horiz = Vec3(0, 0, -horiz_speed)
            self._angular_velocity = -spin_speed
            self._fall_axis = "x"
        else:
            self._fall_velocity_horiz = Vec3(0, 0, 0)
            self._angular_velocity = 0.0
            self._fall_axis = "z"

    def animate_victory(self, on_complete: Optional[Callable[[], None]] = None):
        """Initiates prolonged sinking descent into the goal hole upon victory."""
        self.is_animating = True
        self._is_rolling = False
        self._is_falling = False
        self._is_sinking_victory = True
        self._victory_time = 0.0
        self._fall_velocity_y = 0.0
        self._on_victory_complete = on_complete

        # Spawn celebratory confetti burst
        fx = FXManager.get_instance()
        fx.spawn_confetti(self.pivot.position, count=getattr(CONFIG.animation, "victory_confetti_count", 40))

        # Camera shake
        cam = CameraController.get_instance()
        if cam:
            cam.shake_camera(intensity=0.10)

    def update(self):
        """Per-frame delta-time loop guaranteeing 60-120+ FPS smoothness and zero race conditions."""
        dt = time.dt
        if dt <= 0.0:
            return

        # ---------------------------------------------------------------------
        # 1. Rolling Animation Loop
        # ---------------------------------------------------------------------
        if self._is_rolling:
            dur = Motion.ROLL_DURATION
            self._roll_progress += dt / dur

            if self._roll_progress >= 1.0:
                self._roll_progress = 1.0
                self._is_rolling = False

                board = getattr(self, "_roll_board", None)
                outcome = getattr(self, "_roll_outcome", "SAFE")
                supported_cells = []
                if board and self.current_state and hasattr(self.current_state, "occupied_cells"):
                    supported_cells = [
                        (cx, cy) for (cx, cy) in self.current_state.occupied_cells
                        if board.is_tile_walkable(board.get_tile(cx, cy))
                    ]

                is_void_fall = (outcome == "FELL_VOID" and len(supported_cells) == 0)

                if is_void_fall:
                    # Seamless tumble transition: freeze current 90-degree world position/rotation
                    world_pos = self.mesh.world_position
                    world_rot = self.mesh.world_rotation
                    self.pivot.position = world_pos - self.world_position
                    self.pivot.rotation = world_rot
                    self.mesh.position = Vec3(0, 0, 0)
                    self.mesh.rotation = Vec3(0, 0, 0)
                    self.is_animating = True
                else:
                    self.sync_to_state(self.current_state, clear_fx=False)
                    self.is_animating = False

                    if supported_cells:
                        self._spawn_landing_dust(supported_cells)
                    elif outcome == "SAFE":
                        self._spawn_landing_dust()

                if self._on_roll_complete:
                    cb = self._on_roll_complete
                    self._on_roll_complete = None
                    cb()
            else:
                board = getattr(self, "_roll_board", None)
                outcome = getattr(self, "_roll_outcome", "SAFE")
                is_void_fall = False
                if board and self.current_state and hasattr(self.current_state, "occupied_cells"):
                    supported_cells = [
                        (cx, cy) for (cx, cy) in self.current_state.occupied_cells
                        if board.is_tile_walkable(board.get_tile(cx, cy))
                    ]
                    is_void_fall = (outcome == "FELL_VOID" and len(supported_cells) == 0)

                if is_void_fall:
                    p = self._roll_progress
                    t = p * (0.35 + 0.65 * p)
                else:
                    t = _evaluate_roll_curve(self._roll_progress)

                if self._roll_axis == "z":
                    self.pivot.rotation_z = self._roll_angle * t
                else:
                    self.pivot.rotation_x = self._roll_angle * t

        # ---------------------------------------------------------------------
        # 2. Sci-Fi Teleport & Recall Update Loop
        # ---------------------------------------------------------------------
        elif self._is_teleporting:
            self._teleport_time += dt
            dur = self._teleport_duration
            t = min(1.0, self._teleport_time / dur)

            x_src, y_src = self._teleport_src
            x_dst1, y_dst1 = self._teleport_dst_1
            x_dst2, y_dst2 = self._teleport_dst_2

            surf_y_src = self._get_surface_y(x_src, y_src)
            surf_y_dst1 = self._get_surface_y(x_dst1, y_dst1)
            surf_y_dst2 = self._get_surface_y(x_dst2, y_dst2)

            u1 = CONFIG.block.unit_scale_1
            half_u1 = u1 / 2.0
            fx = FXManager.get_instance() if FXManager._instance else None
            cam = CameraController.get_instance()

            t_cut = 0.308

            # PHASE 1: SOURCE BLACK HOLE OPENS & MONOLITH PLUNGES DOWNWARD INTO HOLE (t < t_cut)
            if t < t_cut:
                p1 = t / t_cut

                p_open = min(1.0, p1 * 4.0)
                r_hole = 1.35 * math.sin(p_open * math.pi * 0.5)

                self._teleport_ring_2.visible = True
                self._teleport_ring_2.position = Vec3(x_src, surf_y_src + 0.015, -y_src)
                self._teleport_ring_2.scale = Vec3(r_hole * 1.35, r_hole * 1.35, 1.0)
                self._teleport_ring_2.rotation_y = p1 * 540.0

                self._teleport_ring_1.visible = True
                self._teleport_ring_1.position = Vec3(x_src, surf_y_src + 0.020, -y_src)
                self._teleport_ring_1.scale = Vec3(r_hole * 1.15, r_hole * 1.15, 1.0)
                self._teleport_ring_1.rotation_y = -p1 * 720.0

                self._teleport_pad_src.visible = True
                self._teleport_pad_src.position = Vec3(x_src, surf_y_src + 0.025, -y_src)
                self._teleport_pad_src.scale = Vec3(r_hole, r_hole, 1.0)
                self._teleport_pad_src.rotation_y = p1 * 360.0

                p_plunge = p1 ** 1.85
                drop_dist = -4.2 * p_plunge
                self.pivot.position = Vec3(x_src, (1.0 + surf_y_src) + drop_dist, -y_src)

                self.pivot.rotation_y = p_plunge * 540.0
                self.pivot.rotation_x = math.sin(p1 * math.pi) * 14.0
                self.pivot.rotation_z = -math.sin(p1 * math.pi) * 10.0

                factor_xz = max(0.12, 1.0 - p_plunge * 0.60)
                self.mesh.scale = Vec3(factor_xz, 1.0, factor_xz)

                fade = max(0.0, 1.0 - (p1 - 0.55) / 0.45) if p1 > 0.55 else 1.0
                gold = self._get_block_color()
                self._set_mesh_color(color.rgba(gold.r, gold.g, gold.b, fade))

                self._teleport_spark_timer += dt
                if self._teleport_spark_timer >= 0.05:
                    self._teleport_spark_timer = 0.0
                    if fx:
                        fx.spawn_particles(
                            Vec3(x_src, surf_y_src + 0.1, -y_src),
                            count=3,
                            token=Palette.TELEPORT_ENERGY,
                            speed=2.5,
                            life=0.20,
                        )

                if p1 > 0.60:
                    p_dst_open = (p1 - 0.60) / 0.40
                    r_dst = 1.35 * math.sin(p_dst_open * math.pi * 0.5)

                    if hasattr(self, "_teleport_ring_dst1"):
                        self._teleport_ring_dst1.visible = True
                        self._teleport_ring_dst1.position = Vec3(x_dst1, surf_y_dst1 + 0.015, -y_dst1)
                        self._teleport_ring_dst1.scale = Vec3(r_dst * 1.25, r_dst * 1.25, 1.0)
                        self._teleport_ring_dst1.rotation_y = p_dst_open * 360.0

                        self._teleport_ring_dst2.visible = True
                        self._teleport_ring_dst2.position = Vec3(x_dst2, surf_y_dst2 + 0.015, -y_dst2)
                        self._teleport_ring_dst2.scale = Vec3(r_dst * 1.25, r_dst * 1.25, 1.0)
                        self._teleport_ring_dst2.rotation_y = -p_dst_open * 360.0

                    self._teleport_pad_dst1.visible = True
                    self._teleport_pad_dst1.position = Vec3(x_dst1, surf_y_dst1 + 0.020, -y_dst1)
                    self._teleport_pad_dst1.scale = Vec3(r_dst, r_dst, 1.0)
                    self._teleport_pad_dst1.rotation_y = p_dst_open * 540.0

                    self._teleport_pad_dst2.visible = True
                    self._teleport_pad_dst2.position = Vec3(x_dst2, surf_y_dst2 + 0.020, -y_dst2)
                    self._teleport_pad_dst2.scale = Vec3(r_dst, r_dst, 1.0)
                    self._teleport_pad_dst2.rotation_y = -p_dst_open * 540.0

            # PHASE 2: LAUNCH DUAL SPLIT CUBES UPWARD
            else:
                p_launch = (t - t_cut) / (1.0 - t_cut)

                self._set_mesh_visible(False)
                self.pivot.visible = False
                self._teleport_pad_src.visible = False
                self._teleport_ring_1.visible = False
                self._teleport_ring_2.visible = False

                self.split_mesh_1.visible = True
                self.split_mesh_2.visible = True
                self.split_mesh_1.scale = Vec3(u1, u1, u1)
                self.split_mesh_2.scale = Vec3(u1, u1, u1)

                if p_launch < 0.68:
                    q = p_launch / 0.68

                    h_vert = max(0.0, 4.0 * 0.48 * q * (1.0 - q))
                    y1 = half_u1 + surf_y_dst1 + h_vert
                    y2 = half_u1 + surf_y_dst2 + h_vert

                    rot_x1 = 28.0 * math.sin(q * math.pi)
                    rot_z1 = -24.0 * math.sin(q * math.pi)
                    rot_y1 = q * 180.0

                    rot_x2 = -22.0 * math.sin(q * math.pi)
                    rot_z2 = 26.0 * math.sin(q * math.pi)
                    rot_y2 = -q * 180.0

                    self.split_mesh_1.position = Vec3(x_dst1, y1, -y_dst1)
                    self.split_mesh_1.rotation = Vec3(rot_x1, rot_y1, rot_z1)
                    self.split_mesh_2.position = Vec3(x_dst2, y2, -y_dst2)
                    self.split_mesh_2.rotation = Vec3(rot_x2, rot_y2, rot_z2)

                    r_close = max(0.0, 1.35 * (1.0 - q * 1.5))
                    self._teleport_pad_dst1.scale = Vec3(r_close, r_close, 1.0)
                    self._teleport_pad_dst2.scale = Vec3(r_close, r_close, 1.0)
                    if hasattr(self, "_teleport_ring_dst1"):
                        self._teleport_ring_dst1.scale = Vec3(r_close * 1.25, r_close * 1.25, 1.0)
                        self._teleport_ring_dst2.scale = Vec3(r_close * 1.25, r_close * 1.25, 1.0)
                    if r_close <= 0.01:
                        self._teleport_pad_dst1.visible = False
                        self._teleport_pad_dst2.visible = False
                        if hasattr(self, "_teleport_ring_dst1"):
                            self._teleport_ring_dst1.visible = False
                            self._teleport_ring_dst2.visible = False
                else:
                    r = (p_launch - 0.68) / 0.32
                    self._teleport_pad_dst1.visible = False
                    self._teleport_pad_dst2.visible = False
                    if hasattr(self, "_teleport_ring_dst1"):
                        self._teleport_ring_dst1.visible = False
                        self._teleport_ring_dst2.visible = False

                    if not self._teleport_has_landed:
                        self._teleport_has_landed = True
                        if fx:
                            fx.spawn_ember_ash(Vec3(x_dst1, surf_y_dst1 + 0.05, -y_dst1), count=8)
                            fx.spawn_ember_ash(Vec3(x_dst2, surf_y_dst2 + 0.05, -y_dst2), count=8)
                        if cam:
                            cam.shake_camera(intensity=0.07, duration=0.10)

                    bounce = 0.13 * math.exp(-7.0 * r) * abs(math.sin(r * math.pi * 2.0))
                    y1 = half_u1 + surf_y_dst1 + bounce
                    y2 = half_u1 + surf_y_dst2 + bounce

                    damp = math.exp(-7.5 * r) * math.cos(r * math.pi * 2.5)
                    rot_x1 = 18.0 * damp
                    rot_z1 = -15.0 * damp
                    rot_y1 = 180.0 * (1.0 - r)

                    rot_x2 = -14.0 * damp
                    rot_z2 = 16.0 * damp
                    rot_y2 = -180.0 * (1.0 - r)

                    self.split_mesh_1.position = Vec3(x_dst1, y1, -y_dst1)
                    self.split_mesh_1.rotation = Vec3(rot_x1, rot_y1, rot_z1)
                    self.split_mesh_2.position = Vec3(x_dst2, y2, -y_dst2)
                    self.split_mesh_2.rotation = Vec3(rot_x2, rot_y2, rot_z2)

            # FINAL TOUCHDOWN & COMPLETION (t >= 1.0)
            if t >= 1.0:
                self._is_teleporting = False
                self.is_animating = False

                self._hide_teleport_fx()

                self.split_mesh_1.rotation = Vec3(0, 0, 0)
                self.split_mesh_2.rotation = Vec3(0, 0, 0)

                self._spawn_landing_dust([(int(x_dst1), int(y_dst1)), (int(x_dst2), int(y_dst2))])

                final_state = self._teleport_final_state
                cb = self._on_teleport_complete
                self._teleport_final_state = None
                self._on_teleport_complete = None

                if final_state:
                    self.sync_to_state(final_state, clear_fx=False)
                if cb:
                    cb()

        # ---------------------------------------------------------------------
        # 3. 1x1x1 Cube Edge-Pivot Rolling Loop
        # ---------------------------------------------------------------------
        elif self._is_cube_rolling:
            dur = Motion.ROLL_DURATION
            self._cube_roll_progress += dt / dur

            if self._cube_roll_progress >= 1.0:
                self._is_cube_rolling = False
                outcome = getattr(self, "_cube_roll_outcome", "SAFE")
                is_void_cube = (outcome == "FELL_VOID")

                if is_void_cube:
                    self.is_animating = True
                else:
                    self.is_animating = False
                    if self._cube_rolling_mesh:
                        self._cube_rolling_mesh.rotation = Vec3(0, 0, 0)

                    if self.current_state and getattr(self.current_state, "is_split", False):
                        act = getattr(self.current_state, "active_block")
                        ax, ay = int(act.x), int(act.y)
                        self._spawn_landing_dust([(ax, ay)])

                if self._on_cube_roll_complete:
                    cb = self._on_cube_roll_complete
                    self._on_cube_roll_complete = None
                    cb()
            else:
                outcome = getattr(self, "_cube_roll_outcome", "SAFE")
                is_void_cube = (outcome == "FELL_VOID")
                if is_void_cube:
                    p = self._cube_roll_progress
                    t = p * (0.35 + 0.65 * p)
                else:
                    t = _evaluate_roll_curve(self._cube_roll_progress)
                angle = self._cube_rot_angle * t
                rad = math.radians(angle)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                p = self._cube_pivot_pos
                d = self._cube_delta_pos
                cube = self._cube_rolling_mesh

                if cube:
                    if self._cube_rot_axis == "z":
                        dx = d.x * cos_a + d.y * sin_a
                        dy = -d.x * sin_a + d.y * cos_a
                        cube.position = Vec3(p.x + dx, p.y + dy, p.z)
                        cube.rotation = Vec3(0.0, 0.0, angle)
                    else:
                        dz = d.z * cos_a + d.y * sin_a
                        dy = -d.z * sin_a + d.y * cos_a
                        cube.position = Vec3(p.x, p.y + dy, p.z + dz)
                        cube.rotation = Vec3(angle, 0.0, 0.0)

                    if self.current_state and getattr(self.current_state, "is_split", False):
                        act_idx = getattr(self.current_state, "active_index", 0)
                        other_cube = self.split_mesh_2 if act_idx == 0 else self.split_mesh_1
                        other_block = self.current_state.b2 if act_idx == 0 else self.current_state.b1
                        u1 = CONFIG.block.unit_scale_1
                        other_cube.y = (u1 / 2.0) + self._get_surface_y(float(other_block.x), float(other_block.y))

        # ---------------------------------------------------------------------
        # 4. Falling & Abyssal Void Dissolve Loop
        # ---------------------------------------------------------------------
        elif self._is_falling:
            self._fall_time += dt
            g = getattr(CONFIG.block, "fall_gravity", 14.0)

            if self._is_seesaw:
                if self._seesaw_phase == 1:
                    rad_arm = math.radians(min(80.0, abs(self._current_tilt_angle) + 12.0))
                    torque_alpha = self._tilt_sign * (0.85 * g * math.sin(rad_arm)) * (180.0 / math.pi)
                    self._angular_velocity += torque_alpha * dt
                    self._current_tilt_angle += self._angular_velocity * dt

                    if self._seesaw_axis == "z":
                        self.pivot.rotation_z = self._current_tilt_angle
                    else:
                        self.pivot.rotation_x = self._current_tilt_angle

                    if abs(self._current_tilt_angle) >= 55.0:
                        self._seesaw_phase = 2
                        world_pos = self.mesh.world_position
                        world_rot = self.mesh.world_rotation
                        self.pivot.position = world_pos - self.world_position
                        self.pivot.rotation = world_rot
                        self.mesh.position = Vec3(0, 0, 0)
                        self.mesh.rotation = Vec3(0, 0, 0)
                        self._fall_velocity_y = 2.2
                        if self._seesaw_axis == "z":
                            self._fall_velocity_horiz = Vec3(self._tilt_sign * 2.0, 0, 0)
                        else:
                            self._fall_velocity_horiz = Vec3(0, 0, self._tilt_sign * 2.0)
                else:
                    self._fall_velocity_y += g * dt
                    self.pivot.y -= self._fall_velocity_y * dt
                    self.pivot.x += self._fall_velocity_horiz.x * dt
                    self.pivot.z += self._fall_velocity_horiz.z * dt
                    if self._seesaw_axis == "z":
                        self.pivot.rotation_z += self._angular_velocity * dt
                    else:
                        self.pivot.rotation_x += self._angular_velocity * dt

            elif self._falling_split_cube:
                cube = self._falling_split_cube
                self._fall_velocity_y += g * dt
                cube.y -= self._fall_velocity_y * dt
                cube.x += self._fall_velocity_horiz.x * dt
                cube.z += self._fall_velocity_horiz.z * dt
                if self._fall_axis == "z":
                    cube.rotation_z += self._angular_velocity * dt
                else:
                    cube.rotation_x += self._angular_velocity * dt

            elif getattr(self, "_fall_mode", "DIRECT") == "FRAGILE":
                self._fall_velocity_y += g * dt
                self.pivot.y -= self._fall_velocity_y * dt
                self.mesh.x = math.sin(self._fall_time * 30.0) * 0.015
                self.mesh.rotation_z = math.sin(self._fall_time * 24.0) * 1.5

            else:  # TUMBLE or DIRECT fall
                self._fall_velocity_y += g * dt
                self.pivot.y -= self._fall_velocity_y * dt
                self.pivot.x += self._fall_velocity_horiz.x * dt
                self.pivot.z += self._fall_velocity_horiz.z * dt
                if self._fall_axis == "z":
                    self.pivot.rotation_z += self._angular_velocity * dt
                else:
                    self.pivot.rotation_x += self._angular_velocity * dt

            # Void Dissolve: Fade mesh alpha as it descends past Y = -3.5
            if self.pivot.y < -3.5:
                fade = max(0.0, 1.0 - (-self.pivot.y - 3.5) / 5.5)
                gold = self._get_block_color()
                self._set_mesh_color(color.rgba(gold.r, gold.g, gold.b, fade))
                if self._falling_split_cube:
                    self._falling_split_cube.color = color.rgba(gold.r, gold.g, gold.b, fade)

            fall_dur = Motion.FALL_DURATION
            if self._fall_time >= fall_dur:
                self._is_falling = False
                self.is_animating = False
                self._set_mesh_visible(False)
                self.pivot.visible = False
                if self._falling_split_cube:
                    self._falling_split_cube.visible = False
                    self._falling_split_cube = None
                if self._on_fall_complete:
                    cb = self._on_fall_complete
                    self._on_fall_complete = None
                    cb()

        # ---------------------------------------------------------------------
        # 5. Victory Goal Vortex Sink Loop
        # ---------------------------------------------------------------------
        elif self._is_sinking_victory:
            self._victory_time += dt
            sink_dur = getattr(Motion, "VICTORY_FALL_DURATION", 4.50)
            g = getattr(CONFIG.block, "fall_gravity", 9.8)

            self._fall_velocity_y += (0.42 * g) * dt
            self.pivot.y -= self._fall_velocity_y * dt

            vortex_spd = getattr(CONFIG.animation, "victory_vortex_speed", 180.0)
            self.pivot.rotation_y += vortex_spd * dt

            progress = min(1.0, self._victory_time / sink_dur)
            if progress > 0.12:
                shrink = max(0.02, 1.0 - ((progress - 0.12) / 0.88) * 0.98)
                self.mesh.scale = Vec3(shrink, shrink, shrink)

            if self._victory_time >= sink_dur:
                self._is_sinking_victory = False
                self.is_animating = False
                self._set_mesh_visible(False)
                self.mesh.scale = Vec3(1, 1, 1)
                if self._on_victory_complete:
                    cb = self._on_victory_complete
                    self._on_victory_complete = None
                    cb()

        # ---------------------------------------------------------------------
        # 6. Idle Ground Elevation Synchronization
        # ---------------------------------------------------------------------
        else:
            if self.current_state and not getattr(self, "_is_sinking_victory", False):
                if getattr(self.current_state, "is_split", False):
                    b1 = getattr(self.current_state, "b1")
                    b2 = getattr(self.current_state, "b2")
                    u1 = CONFIG.block.unit_scale_1
                    half_u1 = u1 / 2.0
                    y1 = half_u1 + self._get_surface_y(float(b1.x), float(b1.y))
                    y2 = half_u1 + self._get_surface_y(float(b2.x), float(b2.y))
                    self.split_mesh_1.y = y1
                    self.split_mesh_2.y = y2
                elif self.mesh.visible:
                    center = self.current_state.get_center_3d()
                    surf_y = self._get_surface_y(float(center[0]), float(center[1]))
                    base_y = float(center[2])
                    self.pivot.y = base_y + surf_y
