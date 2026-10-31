import math
import random
from typing import Optional, Tuple
from ursina import Entity, camera, Vec3, mouse, time as u_time

from bloxorz.config import CONFIG


class CameraController(Entity):
    """Manages isometric view angle, distance, smooth auto-framing, and interactive 3D orbit/zoom."""

    _instance: Optional["CameraController"] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        CameraController._instance = self
        cfg = CONFIG.camera

        # Configure projection
        from ursina import application
        if getattr(application, "base", None):
            camera.orthographic = False
            camera.fov = cfg.fov

        # Juice & Screen Shake State
        self._shake_intensity: float = 0.0
        self._shake_offset: Vec3 = Vec3(0, 0, 0)

        # Angle, Distance, and Center tracking
        self.default_pitch: float = cfg.angle_x
        self.default_yaw: float = cfg.angle_y
        self.current_pitch: float = self.default_pitch
        self.current_yaw: float = self.default_yaw
        self.target_pitch: float = self.default_pitch
        self.target_yaw: float = self.default_yaw

        self.base_distance: float = cfg.min_distance
        self.current_distance: float = self.base_distance
        self.target_distance: float = self.base_distance
        self.min_zoom_distance: float = self.base_distance * cfg.min_distance_factor
        self.max_zoom_distance: float = self.base_distance * cfg.max_distance_factor

        self.default_center: Vec3 = Vec3(0, 0, 0)
        self.current_center: Vec3 = Vec3(0, 0, 0)
        self.target_center: Vec3 = Vec3(0, 0, 0)

        # Config sensitivity & limits
        self.orbit_speed_x: float = cfg.orbit_speed_x
        self.orbit_speed_y: float = cfg.orbit_speed_y
        self.zoom_speed: float = cfg.zoom_speed
        self.min_pitch: float = cfg.min_pitch
        self.max_pitch: float = cfg.max_pitch
        self.smoothing: float = cfg.smoothing
        self.step_orbit_angle: float = cfg.step_orbit_angle
        self.transition_duration: float = cfg.transition_duration

        # Interactive states
        self.is_orbiting: bool = False
        self.enabled_controls: bool = True
        self._prev_mouse_pos: Vec3 = Vec3(0, 0, 0)
        self._was_mouse_down: bool = False

        # Victory goal zoom animation state
        self._is_victory_zooming: bool = False
        self._victory_zoom_time: float = 0.0
        self._victory_zoom_duration: float = 4.5
        self._victory_start_dist: float = 0.0
        self._victory_start_pitch: float = 0.0
        self._victory_start_yaw: float = 0.0
        self._victory_start_center: Vec3 = Vec3(0, 0, 0)
        self._victory_target_center: Vec3 = Vec3(0, 0, 0)
        self._victory_target_dist: float = 0.0
        self._victory_target_pitch: float = 0.0
        self._victory_target_yaw: float = 0.0

    @classmethod
    def get_instance(cls) -> Optional["CameraController"]:
        """Returns the active singleton CameraController instance."""
        return cls._instance

    def shake_camera(self, intensity: float = 0.05, duration: float = 0.12) -> None:
        """Triggers a transient, non-destructive screen shake pulse."""
        if not getattr(CONFIG.animation, "screen_shake_enabled", True):
            return
        self._shake_intensity = min(0.35, max(self._shake_intensity, intensity))

    def frame_board(
        self,
        min_x: int,
        max_x: int,
        min_y: int,
        max_y: int,
        animate: bool = True,
        preserve_rotation: bool = False,
        center_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ):
        """Calculates optimal camera position to frame the board symmetrically."""
        self._is_victory_zooming = False
        cfg = CONFIG.camera
        center_x = (min_x + max_x) / 2.0
        center_z = -((min_y + max_y) / 2.0)

        board_width = max(1, max_x - min_x + 1)
        board_depth = max(1, max_y - min_y + 1)
        diagonal = math.sqrt(board_width ** 2 + board_depth ** 2)

        self.base_distance = max(
            cfg.min_distance,
            diagonal * cfg.distance_diagonal_scale + cfg.distance_offset
        )
        self.min_zoom_distance = self.base_distance * cfg.min_distance_factor
        self.max_zoom_distance = self.base_distance * cfg.max_distance_factor

        self._board_world_offset = Vec3(*center_offset)
        self.default_center = Vec3(
            center_x + self._board_world_offset.x,
            self._board_world_offset.y,
            center_z + self._board_world_offset.z,
        )
        self.target_center = Vec3(self.default_center)
        self.target_distance = self.base_distance

        if not preserve_rotation:
            self.target_pitch = self.default_pitch
            self.target_yaw = self.default_yaw
        else:
            # Preserve existing user rotation angles when switching stages
            self.target_pitch = max(self.min_pitch, min(self.max_pitch, self.current_pitch))
            self.target_yaw = self.current_yaw

        if not animate:
            self.current_center = Vec3(self.target_center)
            self.current_distance = self.target_distance
            self.current_pitch = self.target_pitch
            self.current_yaw = self.target_yaw
            self._apply_camera_transform()

    def orbit(self, delta_x: float, delta_y: float):
        """Offsets yaw and pitch based on mouse drag coordinates."""
        if not self.enabled_controls:
            return
        self._is_victory_zooming = False
        self.target_yaw += delta_x * self.orbit_speed_x
        new_pitch = self.target_pitch + delta_y * self.orbit_speed_y
        self.target_pitch = max(self.min_pitch, min(self.max_pitch, new_pitch))

    def zoom(self, direction: float):
        """Zooms camera in (direction < 0) or out (direction > 0)."""
        if not self.enabled_controls:
            return
        self._is_victory_zooming = False
        new_dist = self.target_distance + direction * self.zoom_speed
        self.target_distance = max(self.min_zoom_distance, min(self.max_zoom_distance, new_dist))

    def step_orbit(self, direction: int):
        """Rotates camera by a fixed step (e.g. +45 deg or -45 deg) on Q/E keys."""
        if not self.enabled_controls:
            return
        self._is_victory_zooming = False
        self.target_yaw += direction * self.step_orbit_angle

    def reset_view(self, animate: bool = True):
        """Smoothly returns camera to the canonical dimetric perspective."""
        self._is_victory_zooming = False
        self.target_yaw = self.default_yaw
        self.target_pitch = self.default_pitch
        self.target_distance = self.base_distance
        self.target_center = Vec3(self.default_center)
        if not animate:
            self.current_yaw = self.target_yaw
            self.current_pitch = self.target_pitch
            self.current_distance = self.target_distance
            self.current_center = Vec3(self.target_center)
            self._apply_camera_transform()

    def animate_victory_focus(self, goal_x: int, goal_y: int, duration: float = 4.5):
        """Gently drifts, tilts, and smoothly zooms camera deep into the goal hole upon victory."""
        goal_pos = Vec3(
            goal_x + self._board_world_offset.x,
            self._board_world_offset.y - 0.2,
            -goal_y + self._board_world_offset.z,
        )

        self._is_victory_zooming = True
        self._victory_zoom_time = 0.0
        self._victory_zoom_duration = max(1.0, duration)
        self._victory_start_dist = self.current_distance
        self._victory_start_pitch = self.current_pitch
        self._victory_start_yaw = self.current_yaw
        self._victory_start_center = Vec3(self.current_center)

        self._victory_target_center = goal_pos
        # Dramatic gradual zoom into the goal vortex (30% of base distance or 2.8 units)
        self._victory_target_dist = max(2.8, self.base_distance * 0.30)
        # Tilt downwards looking into the hole
        self._victory_target_pitch = min(75.0, max(52.0, self.current_pitch + 16.0))
        self._victory_target_yaw = self.current_yaw + 20.0

        self.target_center = goal_pos
        self.target_distance = self._victory_target_dist
        self.target_pitch = self._victory_target_pitch
        self.target_yaw = self._victory_target_yaw

    def update(self):
        """Damps current camera coordinates smoothly toward targets every frame."""
        dt = getattr(u_time, "dt", 0.016)
        if dt <= 0:
            dt = 0.016

        # Check interactive mouse drag (supports both Right Mouse and Left Mouse when not clicking UI)
        from ursina import application
        if getattr(application, "base", None) and mouse:
            try:
                curr_pos = mouse.position
                hovered = getattr(mouse, "hovered_entity", None)
                is_hovering_ui = bool(
                    hovered
                    and (
                        getattr(hovered, "parent", None) == camera.ui
                        or getattr(getattr(hovered, "parent", None), "parent", None) == camera.ui
                    )
                )
                is_down = getattr(mouse, "right", False) or (
                    getattr(mouse, "left", False) and not is_hovering_ui
                )
                if self.enabled_controls and is_down:
                    if self._was_mouse_down:
                        dx = curr_pos[0] - self._prev_mouse_pos[0]
                        dy = curr_pos[1] - self._prev_mouse_pos[1]
                        if dx != 0.0 or dy != 0.0:
                            self.orbit(dx, dy)
                    self._was_mouse_down = True
                else:
                    self._was_mouse_down = False
                self._prev_mouse_pos = curr_pos
            except Exception:
                pass

        if self._is_victory_zooming:
            self._victory_zoom_time += dt
            t = min(1.0, self._victory_zoom_time / self._victory_zoom_duration)
            # Smooth S-curve easing (cosine interpolation)
            s = 0.5 - 0.5 * math.cos(t * math.pi)

            self.current_distance = self._victory_start_dist + (
                self._victory_target_dist - self._victory_start_dist
            ) * s
            self.current_center = self._victory_start_center + (
                self._victory_target_center - self._victory_start_center
            ) * s
            self.current_pitch = self._victory_start_pitch + (
                self._victory_target_pitch - self._victory_start_pitch
            ) * s
            self.current_yaw = self._victory_start_yaw + (self._victory_target_yaw - self._victory_start_yaw) * s

            if t >= 1.0:
                self._is_victory_zooming = False
        else:
            # Exponential damping: lerp = 1 - exp(-smoothing * dt)
            damp = 1.0 - math.exp(-self.smoothing * dt)
            damp = max(0.0, min(1.0, damp))

            self.current_yaw += (self.target_yaw - self.current_yaw) * damp
            self.current_pitch += (self.target_pitch - self.current_pitch) * damp
            self.current_distance += (self.target_distance - self.current_distance) * damp

            diff_center = self.target_center - self.current_center
            self.current_center += diff_center * damp

        # Process screen shake damping
        if self._shake_intensity > 0.001:
            decay = getattr(CONFIG.animation, "shake_decay", 8.0)
            self._shake_intensity = max(0.0, self._shake_intensity - self._shake_intensity * decay * dt)
            rx = (random.random() * 2.0 - 1.0) * self._shake_intensity
            ry = (random.random() * 2.0 - 1.0) * self._shake_intensity
            rz = (random.random() * 2.0 - 1.0) * self._shake_intensity
            self._shake_offset = Vec3(rx, ry, rz)
        else:
            self._shake_intensity = 0.0
            self._shake_offset = Vec3(0, 0, 0)

        self._apply_camera_transform()

    def _apply_camera_transform(self):
        """Applies current pitch, yaw, distance, and center to Ursina camera."""
        from ursina import application
        if not getattr(application, "base", None):
            return

        rad_pitch = math.radians(self.current_pitch)
        rad_yaw = math.radians(self.current_yaw)

        offset_y = self.current_distance * math.sin(rad_pitch)
        h_dist = self.current_distance * math.cos(rad_pitch)
        offset_x = h_dist * math.sin(rad_yaw)
        offset_z = -h_dist * math.cos(rad_yaw)

        camera.position = Vec3(
            self.current_center.x + offset_x + self._shake_offset.x,
            self.current_center.y + offset_y + self._shake_offset.y,
            self.current_center.z + offset_z + self._shake_offset.z,
        )
        camera.rotation = Vec3(self.current_pitch, -self.current_yaw, 0)
