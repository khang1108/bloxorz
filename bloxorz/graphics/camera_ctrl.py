"""Minimalist isometric camera controller with smooth framing."""

import math
from ursina import camera, Vec3, curve


from bloxorz.config import CONFIG


class CameraController:
    """Manages isometric view angle, distance, and auto-framing for Bloxorz."""

    def __init__(self):
        cfg = CONFIG.camera
        # Configure projection
        camera.orthographic = False
        camera.fov = cfg.fov

        # Elegant architectural dimetric angle
        self.angle_x = cfg.angle_x
        self.angle_y = cfg.angle_y
        self.target_center = Vec3(0, 0, 0)
        self.target_distance = cfg.min_distance

    def frame_board(self, min_x: int, max_x: int, min_y: int, max_y: int, animate: bool = True):
        """Calculates optimal camera position to frame the board symmetrically."""
        cfg = CONFIG.camera
        center_x = (min_x + max_x) / 2.0
        center_z = -((min_y + max_y) / 2.0)

        board_width = max(1, max_x - min_x + 1)
        board_depth = max(1, max_y - min_y + 1)
        diagonal = math.sqrt(board_width ** 2 + board_depth ** 2)

        # Set distance based on board scale
        self.target_distance = max(
            cfg.min_distance,
            diagonal * cfg.distance_diagonal_scale + cfg.distance_offset
        )
        self.target_center = Vec3(center_x, 0.0, center_z)

        # Compute camera position relative to target center using spherical coordinates
        rad_x = math.radians(self.angle_x)
        rad_y = math.radians(self.angle_y)

        offset_y = self.target_distance * math.sin(rad_x)
        horizontal_dist = self.target_distance * math.cos(rad_x)
        offset_x = horizontal_dist * math.sin(rad_y)
        offset_z = -horizontal_dist * math.cos(rad_y)

        final_pos = Vec3(
            center_x + offset_x,
            offset_y,
            center_z + offset_z
        )

        if animate:
            dur = cfg.transition_duration
            camera.animate_position(final_pos, duration=dur, curve=curve.out_cubic)
            camera.animate_rotation(Vec3(self.angle_x, -self.angle_y, 0), duration=dur, curve=curve.out_cubic)
        else:
            camera.position = final_pos
            camera.rotation = Vec3(self.angle_x, -self.angle_y, 0)
