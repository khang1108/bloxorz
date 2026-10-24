"""3D Block representation and frame-perfect delta-time rolling animations."""

from typing import Callable, Optional, Tuple
from ursina import Entity, Vec3, color, curve, time

from bloxorz.core.constants import Direction
from bloxorz.core.block import BlockState
from bloxorz.ui.theme import Palette, Motion
from bloxorz.config import CONFIG


class BlockView(Entity):
    """Manages 3D block mesh with frame-perfect delta-time rotation.

    Inherits from Ursina Entity to utilize update() loop, ensuring zero async
    race conditions, zero flickering, and buttery-smooth 60-120+ FPS animations.
    """

    def __init__(self):
        super().__init__(name="block_view_controller")
        c_block = color.hex(Palette.BLOCK_CORE.hex_code)

        # Permanent Pivot Entity: all rolling transformations occur on this pivot
        self.pivot = Entity(name="block_pivot")

        # The Visual Mesh is permanently parented to the pivot (zero reparenting, zero flick)
        self.mesh = Entity(
            parent=self.pivot,
            name="block_mesh",
            model='cube',
            color=c_block,
        )

        self.current_state: Optional[BlockState] = None
        self.is_animating: bool = False

        # Delta-time roll state
        self._is_rolling: bool = False
        self._roll_progress: float = 0.0
        self._roll_axis: str = "z"
        self._roll_angle: float = 0.0
        self._on_roll_complete: Optional[Callable[[], None]] = None

        # Fall / Victory animation states
        self._is_falling: bool = False
        self._fall_time: float = 0.0
        self._on_fall_complete: Optional[Callable[[], None]] = None

        self._is_sinking_victory: bool = False
        self._victory_time: float = 0.0
        self._on_victory_complete: Optional[Callable[[], None]] = None

    @staticmethod
    def _compute_scale(dim: Tuple[float, float, float]) -> Vec3:
        """Calculates visual scale based on unit dimensions configured in config."""
        u1 = CONFIG.block.unit_scale_1
        u2 = CONFIG.block.unit_scale_2
        sx = u2 if dim[0] > 1.5 else u1
        sy = u2 if dim[2] > 1.5 else u1  # Height along Y in Ursina
        sz = u2 if dim[1] > 1.5 else u1  # Depth along Z in Ursina
        return Vec3(sx, sy, sz)

    def sync_to_state(self, state: BlockState):
        """Immediately snaps the 3D block to the given state without animation."""
        self.current_state = state
        self.is_animating = False
        self._is_rolling = False
        self._is_falling = False
        self._is_sinking_victory = False

        center = state.get_center_3d()
        dim = state.get_dimensions_3d()

        # World coordinates: X = center.x, Y = height, Z = -center.y
        world_center = Vec3(float(center[0]), float(center[2]), -float(center[1]))
        target_scale = self._compute_scale(dim)

        self.pivot.position = world_center
        self.pivot.rotation = Vec3(0, 0, 0)
        self.pivot.visible = True

        self.mesh.position = Vec3(0, 0, 0)
        self.mesh.rotation = Vec3(0, 0, 0)
        self.mesh.scale = target_scale
        self.mesh.visible = True

    def roll_animated(
        self,
        prev_state: BlockState,
        next_state: BlockState,
        direction: Direction,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """Initiates a smooth roll along the contact pivot edge using the per-frame update loop."""
        self.is_animating = True
        self.current_state = next_state

        c_prev = prev_state.get_center_3d()
        dim_prev = prev_state.get_dimensions_3d()

        center_world = Vec3(float(c_prev[0]), float(c_prev[2]), -float(c_prev[1]))
        half_x = dim_prev[0] / 2.0
        half_y = dim_prev[1] / 2.0  # Grid Y -> Ursina Z

        # Compute exact contact edge pivot on the ground (Y = 0) with verified mathematical signs
        if direction == Direction.RIGHT:
            pivot_pos = Vec3(center_world.x + half_x, 0.0, center_world.z)
            rot_axis = "z"
            rot_angle = 90.0   # +90 rolls right above ground in Ursina
        elif direction == Direction.LEFT:
            pivot_pos = Vec3(center_world.x - half_x, 0.0, center_world.z)
            rot_axis = "z"
            rot_angle = -90.0  # -90 rolls left above ground in Ursina
        elif direction == Direction.DOWN:  # South (-Z in Ursina)
            pivot_pos = Vec3(center_world.x, 0.0, center_world.z - half_y)
            rot_axis = "x"
            rot_angle = -90.0  # -90 rolls toward -Z above ground
        elif direction == Direction.UP:    # North (+Z in Ursina)
            pivot_pos = Vec3(center_world.x, 0.0, center_world.z + half_y)
            rot_axis = "x"
            rot_angle = 90.0   # +90 rolls toward +Z above ground
        else:
            self.sync_to_state(next_state)
            if on_complete:
                on_complete()
            return

        # 1. Place pivot at contact edge
        self.pivot.position = pivot_pos
        self.pivot.rotation = Vec3(0, 0, 0)

        # 2. Offset mesh locally so its initial world position is continuous (0-pixel shift)
        self.mesh.position = center_world - pivot_pos
        self.mesh.rotation = Vec3(0, 0, 0)
        self.mesh.scale = self._compute_scale(dim_prev)

        # 3. Setup delta-time animation variables
        self._roll_axis = rot_axis
        self._roll_angle = rot_angle
        self._roll_progress = 0.0
        self._on_roll_complete = on_complete
        self._is_rolling = True

    def animate_fall(self, on_complete: Optional[Callable[[], None]] = None):
        """Initiates tumbling descent into the abyss upon falling off."""
        self.is_animating = True
        self._is_rolling = False
        self._is_falling = True
        self._fall_time = 0.0
        self._on_fall_complete = on_complete

    def animate_victory(self, on_complete: Optional[Callable[[], None]] = None):
        """Initiates sinking into the goal hole upon victory."""
        self.is_animating = True
        self._is_rolling = False
        self._is_sinking_victory = True
        self._victory_time = 0.0
        self._on_victory_complete = on_complete

    def update(self):
        """Per-frame delta-time loop guaranteeing 60-120+ FPS smoothness and zero race conditions."""
        dt = time.dt

        # Handle rolling
        if self._is_rolling:
            dur = Motion.ROLL_DURATION
            self._roll_progress += dt / dur

            if self._roll_progress >= 1.0:
                self._roll_progress = 1.0
                self._is_rolling = False
                self.sync_to_state(self.current_state)
                self.is_animating = False
                if self._on_roll_complete:
                    cb = self._on_roll_complete
                    self._on_roll_complete = None
                    cb()
            else:
                t = curve.out_cubic(self._roll_progress)
                if self._roll_axis == "z":
                    self.pivot.rotation_z = self._roll_angle * t
                else:
                    self.pivot.rotation_x = self._roll_angle * t

        # Handle falling
        elif self._is_falling:
            self._fall_time += dt
            self.pivot.y -= CONFIG.block.fall_gravity * dt
            self.pivot.rotation_x += CONFIG.block.fall_rot_x * dt
            self.pivot.rotation_y += CONFIG.block.fall_rot_y * dt
            self.pivot.rotation_z += CONFIG.block.fall_rot_z * dt

            if self._fall_time >= Motion.FALL_DURATION:
                self._is_falling = False
                self.is_animating = False
                self.mesh.visible = False
                if self._on_fall_complete:
                    cb = self._on_fall_complete
                    self._on_fall_complete = None
                    cb()

        # Handle victory sink
        elif self._is_sinking_victory:
            self._victory_time += dt
            sink_dur = Motion.VICTORY_PULSE_DURATION
            if self._victory_time <= sink_dur:
                self.pivot.y -= (CONFIG.block.victory_sink_depth * dt) / sink_dur
            else:
                self._is_sinking_victory = False
                self.is_animating = False
                if self._on_victory_complete:
                    cb = self._on_victory_complete
                    self._on_victory_complete = None
                    cb()
