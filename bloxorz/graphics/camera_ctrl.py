"""Minimalist isometric camera controller with smooth framing, 3D orbit, and zoom."""

import math
from ursina import Entity, camera, Vec3, mouse, time as u_time

from bloxorz.config import CONFIG


class CameraController(Entity):
    """Manages isometric view angle, distance, smooth auto-framing, and interactive 3D orbit/zoom."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        cfg = CONFIG.camera

        # Configure projection
        from ursina import application
        if getattr(application, "base", None):
            camera.orthographic = False
            camera.fov = cfg.fov

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
        self._was_mouse_right_down: bool = False

    def frame_board(self, min_x: int, max_x: int, min_y: int, max_y: int, animate: bool = True):
        """Calculates optimal camera position to frame the board symmetrically."""
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

        self.default_center = Vec3(center_x, 0.0, center_z)
        self.target_center = Vec3(self.default_center)
        self.target_distance = self.base_distance
        self.target_pitch = self.default_pitch
        self.target_yaw = self.default_yaw

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
        self.target_yaw += delta_x * self.orbit_speed_x
        new_pitch = self.target_pitch + delta_y * self.orbit_speed_y
        self.target_pitch = max(self.min_pitch, min(self.max_pitch, new_pitch))

    def zoom(self, direction: float):
        """Zooms camera in (direction < 0) or out (direction > 0)."""
        if not self.enabled_controls:
            return
        new_dist = self.target_distance + direction * self.zoom_speed
        self.target_distance = max(self.min_zoom_distance, min(self.max_zoom_distance, new_dist))

    def step_orbit(self, direction: int):
        """Rotates camera by a fixed step (e.g. +45 deg or -45 deg) on Q/E keys."""
        if not self.enabled_controls:
            return
        self.target_yaw += direction * self.step_orbit_angle

    def reset_view(self, animate: bool = True):
        """Smoothly returns camera to the canonical dimetric perspective."""
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

    def animate_victory_focus(self, goal_x: int, goal_y: int):
        """Gently drifts and tilts camera toward the goal vortex during stage victory."""
        tile_size = getattr(getattr(CONFIG, "board", None), "tile_size", 0.86)
        goal_pos = Vec3(goal_x * tile_size, -0.2, -goal_y * tile_size)
        self.target_center = goal_pos
        self.target_distance = self.base_distance * 0.80
        self.target_pitch = max(self.min_pitch, self.current_pitch - 6.0)
        self.target_yaw = self.current_yaw + 15.0

    def update(self):
        """Damps current camera coordinates smoothly toward targets every frame."""
        dt = getattr(u_time, "dt", 0.016)
        if dt <= 0:
            dt = 0.016

        # Check interactive mouse drag (RMB)
        if mouse and hasattr(mouse, "position"):
            curr_pos = mouse.position
            if self.enabled_controls and getattr(mouse, "right", False):
                if self._was_mouse_right_down:
                    dx = curr_pos[0] - self._prev_mouse_pos[0]
                    dy = curr_pos[1] - self._prev_mouse_pos[1]
                    if dx != 0.0 or dy != 0.0:
                        self.orbit(dx, dy)
                self._was_mouse_right_down = True
            else:
                self._was_mouse_right_down = False
            self._prev_mouse_pos = curr_pos

        # Exponential damping: lerp = 1 - exp(-smoothing * dt)
        damp = 1.0 - math.exp(-self.smoothing * dt)
        damp = max(0.0, min(1.0, damp))

        self.current_yaw += (self.target_yaw - self.current_yaw) * damp
        self.current_pitch += (self.target_pitch - self.current_pitch) * damp
        self.current_distance += (self.target_distance - self.current_distance) * damp

        diff_center = self.target_center - self.current_center
        self.current_center += diff_center * damp

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
            self.current_center.x + offset_x,
            self.current_center.y + offset_y,
            self.current_center.z + offset_z,
        )
        camera.rotation = Vec3(self.current_pitch, -self.current_yaw, 0)
