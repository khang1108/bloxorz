"""World-space neon grid enclosure surrounding the active board."""

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageSequence
from panda3d.core import (
    ColorScaleAttrib,
    GeomVertexReader,
    MaterialAttrib,
    NodePath,
    Vec4,
)
from ursina import Entity, Mesh, Vec3, color, destroy, load_model, scene, time
from ursina.color import Color
from ursina.shaders import unlit_shader
from ursina.texture import Texture as UrsinaTexture


@dataclass
class _LightRunner:
    axis: int
    width_axis: int
    normal_axis: int
    inward: float
    start: Tuple[float, float, float]
    end: Tuple[float, float, float]
    phase: float
    speed: float
    color: Color
    entity: Optional[Entity] = None
    active_axis: int = -1


class _PixelWallAnimation(Entity):
    """Small original neon pixel-art loop rendered as one animated mesh."""

    FRAME_DURATION = 0.12
    GRID_SIZE = 25
    FRAME_COUNT = 8
    PIXEL_SIZE = 0.42

    CYAN = color.hex("#00F0FF")
    PINK = color.hex("#FF38C8")
    PURPLE = color.hex("#EC3697")
    LIGHT_PINK = color.hex("#FF9AE8")
    WHITE = color.hex("#F6F4FF")
    DARK_BLUE = color.hex("#16234B")
    _frame_meshes: Optional[Tuple[Mesh, ...]] = None

    def __init__(self, parent: Entity, position: Vec3) -> None:
        if type(self)._frame_meshes is None:
            type(self)._frame_meshes = tuple(
                self._make_frame(frame_index)
                for frame_index in range(self.FRAME_COUNT)
            )
        frames = type(self)._frame_meshes
        assert frames is not None
        self._frames = frames
        self._elapsed = 0.0
        self._frame_index = 0
        super().__init__(
            parent=parent,
            name="pixel_wall_animation",
            model=self._frames[0],
            position=position,
            shader=unlit_shader,
            color=color.white,
            double_sided=True,
            unlit=True
        )

    @classmethod
    def _pixel_color(cls, row: int, column: int, frame: int):
        cx = (cls.GRID_SIZE - 1) / 2
        cy = (cls.GRID_SIZE - 1) / 2
        dx = column - cx
        dy = row - cy
        radius = math.hypot(dx, dy)

        if 6.0 <= radius <= 8.0:
            angle = math.atan2(dy, dx) + frame * math.tau / cls.FRAME_COUNT
            segment = int((angle % math.tau) / (math.tau / 3))
            return (cls.CYAN, cls.PINK, cls.PURPLE)[segment]
        if 4.8 <= radius < 6.0 and (row + column + frame) % 3 == 0:
            return cls.LIGHT_PINK
        if abs(dx) + abs(dy) in (3, 4):
            return cls.PURPLE if frame % 2 else cls.PINK
        if abs(dx) <= 1 and abs(dy) <= 1:
            return cls.WHITE if (row + column + frame) % 3 else cls.CYAN

        building_heights = (4, 6, 3, 7, 5, 4, 6, 3, 5, 7, 4, 6, 3)
        if row >= 18:
            building_index = column // 2
            height = building_heights[building_index % len(building_heights)]
            if row >= cls.GRID_SIZE - height:
                if (column + row) % 3 == 0:
                    return cls.CYAN if building_index % 2 else cls.PINK
                return cls.DARK_BLUE

        stars = ((2, 3), (3, 19), (5, 7), (4, 21), (9, 2), (7, 22), (15, 4), (13, 21))
        for index, (star_row, star_column) in enumerate(stars):
            if (row, column) == (star_row, star_column) and frame % 4 != index % 4:
                return cls.CYAN if index % 2 else cls.LIGHT_PINK
        return None

    @classmethod
    def _make_frame(cls, frame: int) -> Mesh:
        vertices = []
        triangles = []
        colors = []
        half = cls.PIXEL_SIZE / 2
        for row in range(cls.GRID_SIZE):
            for column in range(cls.GRID_SIZE):
                pixel_color = cls._pixel_color(row, column, frame)
                if pixel_color is None:
                    continue
                center_y = (cls.GRID_SIZE / 2 - row - 0.5) * cls.PIXEL_SIZE
                center_z = (column - cls.GRID_SIZE / 2 + 0.5) * cls.PIXEL_SIZE
                start = len(vertices)
                vertices.extend(
                    (
                        (0, center_y - half, center_z - half),
                        (0, center_y + half, center_z - half),
                        (0, center_y + half, center_z + half),
                        (0, center_y - half, center_z + half),
                    )
                )
                triangles.extend(((start, start + 1, start + 2), (start, start + 2, start + 3)))
                colors.extend((pixel_color,) * 4)
        return Mesh(vertices=vertices, triangles=triangles, colors=colors, static=True)

    def update(self) -> None:
        self._elapsed += max(0.0, time.dt)
        frame_index = int(self._elapsed / self.FRAME_DURATION) % self.FRAME_COUNT
        if frame_index != self._frame_index:
            self._frame_index = frame_index
            self.model = self._frames[frame_index]


class _GifWallAnimation(Entity):
    """Display an animated GIF across an enclosure wall."""

    _cached_frames: Dict[Path, Tuple[Tuple[UrsinaTexture, ...], Tuple[float, ...], Tuple[int, int]]] = {}

    def __init__(
        self,
        parent: Entity,
        position: Vec3,
        gif_path: Path,
        width: float,
        height: float,
        rotation_y: float,
    ) -> None:
        frames, durations, _ = self._load_frames(gif_path)
        self._frames = frames
        self._durations = durations
        self._elapsed = 0.0
        self._frame_index = 0
        super().__init__(
            parent=parent,
            name="pixel_wall_gif",
            model="quad",
            texture=self._frames[0],
            position=position,
            rotation_y=rotation_y,
            scale=(width, height, 1),
            shader=unlit_shader,
            color=color.white,
            transparency=True,
            double_sided=True,
        )

    @classmethod
    def _load_frames(
        cls,
        gif_path: Path,
    ) -> Tuple[Tuple[UrsinaTexture, ...], Tuple[float, ...], Tuple[int, int]]:
        if gif_path in cls._cached_frames:
            return cls._cached_frames[gif_path]
        frames = []
        durations = []
        with Image.open(gif_path) as gif:
            image_size = gif.size
            for frame in ImageSequence.Iterator(gif):
                rgba_frame = frame.convert("RGBA")
                texture = UrsinaTexture(rgba_frame, filtering="nearest")
                frames.append(texture)
                durations.append(max(frame.info.get("duration", 100) / 1000, 0.02))

        result = (tuple(frames), tuple(durations), image_size)
        cls._cached_frames[gif_path] = result
        return result

    def update(self) -> None:
        self._elapsed += max(0.0, time.dt)
        while self._elapsed >= self._durations[self._frame_index]:
            self._elapsed -= self._durations[self._frame_index]
            self._frame_index = (self._frame_index + 1) % len(self._frames)
            self.texture = self._frames[self._frame_index]


class CyberGridBackground(Entity):
    """Render a six-sided neon grid enclosure that follows the camera view."""

    MIN_SIZE = 50.0
    BOARD_MARGIN = 3.0
    BOARD_VERTICAL_MARGIN = 5.0
    BOTTOM_FACE_RAISE = 30.0
    CAMERA_MARGIN = 1.12
    MAX_GRID_INTERVALS = 8
    RUNNER_CORE_DEPTH = 0.015
    WALL_GIF_CLEARANCE = 0.3
    BACKGROUND_OPACITY = 1.0
    GRID_OPACITY = 1.0
    PIXEL_WALL_GIF_PATH = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "background"
        / "wall_front.gif"
    )
    CITY_MODEL_PATH = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "models"
        / "city.glb"
    )
    CITY_ENCLOSURE_SCALE = 2.0
    CITY_HORIZONTAL_SCALE = 4.0
    ENCLOSURE_HEIGHT_SCALE = 1.5
    CITY_MODEL_SCALE = 1.8
    WALL_GIF_FILENAMES = {
        "-X": "wall_left.gif",
        "+X": "wall_right.gif",
        "-Z": "wall_front.gif",
        "+Z": "wall_back.gif",
    }
    CITY_BOTTOM_FACE_HEIGHT_RATIO = 0.7
    CITY_MAX_FOOTPRINT_RATIO = 2.0
    CITY_MAX_HEIGHT_RATIO = 0.42
    CITY_BASE_FLOOR_CLEARANCE = 0.08
    CITY_BASE_COLOR_GAMMA = 0.55
    CITY_FLOOR_CLEARANCE = 1.0
    CITY_GROUND_MATERIAL_NAME = "Meshpart1Mtl"
    CITY_GROUND_COLOR = (92, 99, 102)
    CITY_BOTTOM_FACE_COLOR = color.hex("#373A3D")
    CITY_MISSING_COLOR = (128, 128, 128)
    CITY_NEUTRAL_ARCHITECTURE_COLOR = (17, 17, 18)
    CITY_NEUTRAL_COLOR_MAX_CHANNEL_DIFFERENCE = 0.12
    CITY_NEUTRAL_COLOR_MIN_BRIGHTNESS = 0.35
    CITY_SHADOW_DIRECTION = (-0.55, -1.0, 0.35)
    CITY_SHADOW_RESOLUTION = 1024
    CITY_SHADOW_OPACITY = 112
    CITY_SHADOW_BLUR = 6
    CITY_SHADOW_CLEARANCE = 0.15
    ENCLOSURE_FACE_CLEARANCE = 0.03

    PURPLE = color.hex("#E91EA2")
    TRAIL_PURPLE = color.hex("#EBDDFF")

    def __init__(self, enable_city: Optional[bool] = None) -> None:
        super().__init__(parent=scene, name="cyber_grid_background")
        if enable_city is not None:
            self.enable_city = bool(enable_city)
        else:
            from bloxorz.config import CONFIG
            self.enable_city = getattr(
                getattr(CONFIG, "background", None),
                "enable_city_model",
                False,
            )
        self._animation_time = 0.0
        self._half_size = self.MIN_SIZE / 2
        self._floor_y = -self._half_size
        self._wall_floor_y = -self._half_size
        self._ceiling_y = self._half_size
        self._spacing = self.MIN_SIZE / self.MAX_GRID_INTERVALS
        self._runners: List[_LightRunner] = []
        self._runner_mesh_cache: Dict[Tuple[int, int, float, float, str, float], Mesh] = {}
        self._runner_entities: List[Entity] = []
        self._grid_entities: List[Entity] = []
        self._gradient_entities: List[Entity] = []
        self._bottom_face: Optional[Entity] = None
        self._pixel_wall: Optional[_PixelWallAnimation] = None
        self._wall_gifs: Dict[str, _GifWallAnimation] = {}
        self._bottom_city: Optional[Entity] = None
        self._city_shadow_overlay: Optional[Entity] = None
        self._has_board_bounds = False
        self._board_center_world = (0.0, 0.0, 0.0)

    @property
    def has_city_model(self) -> bool:
        """Returns True if the 3D city model is enabled and its asset file exists."""
        return bool(self.enable_city and self.CITY_MODEL_PATH.is_file())

    def _make_mesh_entity(
        self, mesh: Mesh, name: str, transparency: bool = True
    ) -> Entity:
        return Entity(
            parent=self,
            name=name,
            model=mesh,
            shader=unlit_shader,
            color=color.white,
            transparency=transparency,
            double_sided=True,
        )

    @staticmethod
    def _append_strip(
        vertices: List[Tuple[float, float, float]],
        triangles: List[Tuple[int, int, int]],
        colors: List[Color],
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        width_axis: int,
        width: float,
        line_color: Color,
        alpha: float,
    ) -> None:
        half_width = width / 2
        first = list(start)
        second = list(start)
        third = list(end)
        fourth = list(end)
        first[width_axis] -= half_width
        second[width_axis] += half_width
        third[width_axis] += half_width
        fourth[width_axis] -= half_width

        vertex_start = len(vertices)
        vertices.extend((tuple(first), tuple(second), tuple(third), tuple(fourth)))
        triangles.extend(
            (
                (vertex_start, vertex_start + 1, vertex_start + 2),
                (vertex_start, vertex_start + 2, vertex_start + 3),
            )
        )
        vertex_color = color.rgba(
            line_color.r,
            line_color.g,
            line_color.b,
            alpha * CyberGridBackground.GRID_OPACITY,
        )
        colors.extend((vertex_color,) * 4)

    @staticmethod
    def _coordinates(half_extent: float, spacing: float) -> List[float]:
        interval_count = max(1, round(2 * half_extent / spacing))
        return [
            -half_extent + 2 * half_extent * index / interval_count
            for index in range(interval_count + 1)
        ]

    @staticmethod
    def _coordinates_between(
        minimum: float,
        maximum: float,
        spacing: float,
    ) -> List[float]:
        interval_count = max(1, round((maximum - minimum) / spacing))
        return [
            minimum + (maximum - minimum) * index / interval_count
            for index in range(interval_count + 1)
        ]

    def set_board_bounds(
        self,
        min_x: int,
        max_x: int,
        min_y: int,
        max_y: int,
        camera_distance: float,
        board_height: float = 0.0,
    ) -> None:
        """Fit a static world-aligned cube around the board and camera orbit."""
        board_center_x = (min_x + max_x) / 2
        board_center_z = -((min_y + max_y) / 2)
        self._board_center_world = (board_center_x, 0.0, board_center_z)
        board_width = max_x - min_x + 1 + self.BOARD_MARGIN * 2
        board_depth = max_y - min_y + 1 + self.BOARD_MARGIN * 2
        side_length = max(
            self.MIN_SIZE,
            board_width,
            board_depth,
            camera_distance * 2 * self.CAMERA_MARGIN,
        )
        if self.has_city_model:
            side_length *= self.CITY_ENCLOSURE_SCALE

        self.position = (
            board_center_x,
            0.0,
            board_center_z,
        )
        self.scale_x = self.CITY_HORIZONTAL_SCALE
        self.scale_y = self.ENCLOSURE_HEIGHT_SCALE
        self.scale_z = self.scale_x
        self._half_size = side_length / 2
        base_world_floor_y = (
            -self._half_size * self.CITY_BOTTOM_FACE_HEIGHT_RATIO
            if self.has_city_model
            else -self._half_size
        )
        self._wall_floor_y = base_world_floor_y / self.scale_y
        world_floor_y = base_world_floor_y + self.BOTTOM_FACE_RAISE
        self._floor_y = world_floor_y / self.scale_y
        target_ceiling_y = (
            base_world_floor_y
            + (2 * self._half_size - base_world_floor_y) * self.scale_y / 2
        ) / self.scale_y
        board_ceiling_y = (
            board_height + self.BOARD_VERTICAL_MARGIN - self.y
        ) / self.scale_y
        self._ceiling_y = max(target_ceiling_y, board_ceiling_y)
        self._spacing = side_length / self.MAX_GRID_INTERVALS
        self._has_board_bounds = True
        self._build_enclosure()

    def _append_face_line(
        self,
        vertices: List[Tuple[float, float, float]],
        triangles: List[Tuple[int, int, int]],
        colors: List[Color],
        start: Tuple[float, float, float],
        end: Tuple[float, float, float],
        width_axis: int,
        normal_axis: int,
        inward: float,
        width: float,
        line_color: Color,
        alpha: float,
        depth: float,
        line_offset: float = 0.0,
    ) -> None:
        offset_start = list(start)
        offset_end = list(end)
        offset_start[width_axis] += line_offset
        offset_end[width_axis] += line_offset
        offset_start[normal_axis] += inward * depth
        offset_end[normal_axis] += inward * depth
        self._append_strip(
            vertices,
            triangles,
            colors,
            tuple(offset_start),
            tuple(offset_end),
            width_axis,
            width,
            line_color,
            alpha,
        )

    def _build_grid_layer(
        self,
        name: str,
        width_factor: float,
        alpha: float,
        depth: float,
    ) -> None:
        vertices: List[Tuple[float, float, float]] = []
        triangles: List[Tuple[int, int, int]] = []
        colors: List[Color] = []
        h = self._half_size
        lines = self._coordinates(h, self._spacing)
        if name == "grid_glow":
            width_factor = 0.18
        elif name == "grid_core":
            width_factor = 0.07
        width = self._spacing * width_factor

        def append_line(
            start: Tuple[float, float, float],
            end: Tuple[float, float, float],
            width_axis: int,
            normal_axis: int,
            inward: float,
            line_color: Color,
            line_width: Optional[float] = None,
        ) -> None:
            line_width = width if line_width is None else line_width
            self._append_face_line(
                vertices, triangles, colors, start, end,
                width_axis, normal_axis, inward,
                line_width, line_color, alpha, depth,
            )

        interior_lines = lines[1:-1]
        for coordinate in interior_lines:
            append_line(
                (-h, self._floor_y, coordinate),
                (h, self._floor_y, coordinate),
                2, 1, 1.0, self.PURPLE,
            )
            append_line(
                (coordinate, self._floor_y, -h),
                (coordinate, self._floor_y, h),
                0, 1, 1.0, self.PURPLE,
            )

        edge_width = self._spacing * 0.12
        for z in (-h, h):
            append_line(
                (-h, self._floor_y, z),
                (h, self._floor_y, z),
                2, 1, 1.0, self.PURPLE, edge_width,
            )
        for x in (-h, h):
            append_line(
                (x, self._floor_y, -h),
                (x, self._floor_y, h),
                0, 1, 1.0, self.PURPLE, edge_width,
            )

        mesh = Mesh(
            vertices=vertices,
            triangles=triangles,
            colors=colors,
            static=True,
        )
        self._grid_entities.append(
            self._make_mesh_entity(mesh, name, transparency=name != "grid_core")
        )

    def _build_runners(self) -> None:
        h = self._half_size
        wall_lines = self._coordinates_between(
            self._floor_y,
            self._ceiling_y,
            self._spacing,
        )
        stride = max(1, math.ceil(len(wall_lines) / 5))
        for entity in self._runner_entities:
            destroy(entity)
        self._runner_entities.clear()
        self._runner_mesh_cache.clear()
        self._runners = []

        for side_index, (x, inward) in enumerate(((-h, 1.0), (h, -1.0))):
            for index, y in enumerate(wall_lines[1::stride]):
                self._runners.append(
                    _LightRunner(
                        axis=2, width_axis=1, normal_axis=0, inward=inward,
                        start=(x, y, -h), end=(x, y, h),
                        phase=(index * 0.618 + side_index * 0.25) % 1,
                        speed=2.1 + (index % 3) * 0.14,
                        color=self.PURPLE,
                    )
                )

        for side_index, (z, inward) in enumerate(((-h, 1.0), (h, -1.0))):
            for index, y in enumerate(wall_lines[1::stride]):
                self._runners.append(
                    _LightRunner(
                        axis=0, width_axis=1, normal_axis=2, inward=inward,
                        start=(-h, y, z), end=(h, y, z),
                        phase=(index * 0.618 + side_index * 0.41) % 1,
                        speed=2.0 + (index % 4) * 0.13,
                        color=self.PURPLE,
                    )
                )

        for runner in self._runners:
            position, active_axis, normal_axis, inward, width_axis = self._runner_path(runner)
            runner.active_axis = active_axis
            lane_axis = 3 - runner.axis - runner.normal_axis
            self._runner_mesh(runner, runner.axis, lane_axis)
            self._runner_mesh(runner, runner.normal_axis, lane_axis)
            runner.entity = Entity(
                parent=self,
                name="grid_runner",
                model=self._runner_mesh(runner, active_axis, width_axis),
                position=Vec3(*position) + self._axis_offset(
                    normal_axis, inward * self.RUNNER_CORE_DEPTH
                ),
                shader=unlit_shader,
                color=color.white,
                double_sided=True,
                enabled=self._runner_visible(position, normal_axis),
            )
            self._runner_entities.append(runner.entity)

    @property
    def _runner_length(self) -> float:
        return min(self._spacing * 3.5, self._half_size * 0.32)

    @staticmethod
    def _axis_offset(axis: int, distance: float) -> Vec3:
        offset = Vec3(0, 0, 0)
        if axis == 0:
            offset.x = distance
        elif axis == 1:
            offset.y = distance
        else:
            offset.z = distance
        return offset

    def _runner_mesh(
        self, runner: _LightRunner, axis: int, width_axis: int
    ) -> Mesh:
        length = self._runner_length
        glow_width = self._spacing * 0.27
        core_length = length * 0.84
        core_width = self._spacing * 0.06
        trail_color = self.TRAIL_PURPLE
        color_key = f"{runner.color.r:.3f}:{runner.color.g:.3f}:{runner.color.b:.3f}"
        key = (
            axis,
            width_axis,
            round(length, 4),
            round(glow_width, 4),
            color_key,
            core_width,
        )
        if key in self._runner_mesh_cache:
            return self._runner_mesh_cache[key]

        vertices = []
        colors = []
        triangles = []
        glow_color = color.rgb(
            runner.color.r * 0.64,
            runner.color.g * 0.64,
            runner.color.b * 0.64,
        )
        for radius_length, radius_width in (
            (length, glow_width),
            (length * 0.9, core_width * 1.7),
        ):
            for index in range(20):
                angle = math.tau * index / 20
                point = [0.0, 0.0, 0.0]
                point[axis] = math.cos(angle) * radius_length / 2
                point[width_axis] = math.sin(angle) * radius_width / 2
                vertices.append(tuple(point))
                colors.append(glow_color)

        for index in range(20):
            outer = index
            next_outer = (index + 1) % 20
            inner = 20 + index
            next_inner = 20 + (index + 1) % 20
            triangles.extend(
                ((outer, next_outer, next_inner), (outer, next_inner, inner))
            )

        core_center = len(vertices)
        vertices.append((0.0, 0.0, 0.0))
        colors.append(color.rgb(trail_color.r, trail_color.g, trail_color.b))
        for index in range(20):
            angle = math.tau * index / 20
            point = [0.0, 0.0, 0.0]
            point[axis] = math.cos(angle) * core_length / 2
            point[width_axis] = math.sin(angle) * core_width / 2
            vertices.append(tuple(point))
            colors.append(color.rgb(trail_color.r, trail_color.g, trail_color.b))
        core_start = core_center + 1
        triangles.extend(
            (
                core_center,
                core_start + index,
                core_start + (index + 1) % 20,
            )
            for index in range(20)
        )
        mesh = Mesh(
            vertices=vertices,
            triangles=triangles,
            colors=colors,
            static=True,
        )
        self._runner_mesh_cache[key] = mesh
        return mesh

    def _runner_path(
        self,
        runner: _LightRunner,
    ) -> Tuple[Tuple[float, float, float], int, int, float, int]:
        h = self._half_size
        axis_scale = self.scale_x if runner.axis in (0, 2) else self.scale_y
        normal_scale = (
            self.scale_x
            if runner.normal_axis in (0, 2)
            else self.scale_y
        )
        axis_length = 2 * h * axis_scale
        normal_length = 2 * h * normal_scale
        segment_lengths = (axis_length, normal_length, axis_length, normal_length)
        perimeter = sum(segment_lengths)
        distance = (
            runner.phase * perimeter + self._animation_time * runner.speed
        ) % perimeter
        leg = 0
        while leg < len(segment_lengths) - 1 and distance >= segment_lengths[leg]:
            distance -= segment_lengths[leg]
            leg += 1
        segment_scale = axis_scale if leg in (0, 2) else normal_scale
        along = distance / segment_scale
        start_normal = runner.start[runner.normal_axis]
        normal_sign = 1.0 if start_normal >= 0 else -1.0
        lane_axis = 3 - runner.axis - runner.normal_axis
        point = list(runner.start)

        if leg == 0:
            active_axis = runner.axis
            point[runner.axis] = -h + along
            point[runner.normal_axis] = start_normal
            surface_normal = runner.normal_axis
            inward = -normal_sign
        elif leg == 1:
            active_axis = runner.normal_axis
            point[runner.axis] = h
            point[runner.normal_axis] = start_normal - normal_sign * along
            surface_normal = runner.axis
            inward = -1.0
        elif leg == 2:
            active_axis = runner.axis
            point[runner.axis] = h - along
            point[runner.normal_axis] = -start_normal
            surface_normal = runner.normal_axis
            inward = normal_sign
        else:
            active_axis = runner.normal_axis
            point[runner.axis] = -h
            point[runner.normal_axis] = -start_normal + normal_sign * along
            surface_normal = runner.axis
            inward = 1.0

        point[lane_axis] = runner.start[lane_axis]
        width_axis = lane_axis
        return tuple(point), active_axis, surface_normal, inward, width_axis

    def _build_enclosure(self) -> None:
        for entity in self._grid_entities:
            destroy(entity)
        self._grid_entities.clear()
        for entity in self._runner_entities:
            destroy(entity)
        self._runner_entities.clear()
        self._runner_mesh_cache.clear()
        self._runners.clear()
        for entity in self._gradient_entities:
            destroy(entity)
        self._gradient_entities.clear()
        if self._bottom_face is not None:
            destroy(self._bottom_face)
            self._bottom_face = None
        self._build_face_gradients()
        self._build_grid_layer("grid_glow", 0.14, 0.16, 0.025)
        self._build_grid_layer("grid_core", 0.035, 1.0, 0.0)
        self._build_pixel_wall()
        self._build_bottom_city()

    def _update_runner_entities(self) -> None:
        for runner in self._runners:
            position, active_axis, normal_axis, inward, width_axis = self._runner_path(runner)
            if active_axis != runner.active_axis:
                runner.entity.model = self._runner_mesh(runner, active_axis, width_axis)
                runner.active_axis = active_axis
            runner.entity.enabled = self._runner_visible(position, normal_axis)

            center = Vec3(*position)
            runner.entity.position = center + self._axis_offset(
                normal_axis, inward * self.RUNNER_CORE_DEPTH
            )

    def _runner_visible(
        self, position: Tuple[float, float, float], normal_axis: int
    ) -> bool:
        return not (
            normal_axis == 2
            and abs(position[2] + self._half_size) < 1e-5
        )

    def _build_pixel_wall(self) -> None:
        existing_wall_gifs = tuple(self._wall_gifs.values())
        for wall_gif in existing_wall_gifs:
            destroy(wall_gif)
        self._wall_gifs.clear()
        if self._pixel_wall is not None and self._pixel_wall not in existing_wall_gifs:
            destroy(self._pixel_wall)
        self._pixel_wall = None

        h = self._half_size
        local_height = self._ceiling_y - self._wall_floor_y
        center_y = (self._ceiling_y + self._wall_floor_y) * 0.5
        wall_specs = {
            "-X": (
                Vec3(-h + self.WALL_GIF_CLEARANCE, center_y, 0),
                2 * h,
                -90,
            ),
            "+X": (
                Vec3(h - self.WALL_GIF_CLEARANCE, center_y, 0),
                2 * h,
                90,
            ),
            "-Z": (
                Vec3(0, center_y, -h + self.WALL_GIF_CLEARANCE),
                2 * h,
                180,
            ),
            "+Z": (
                Vec3(0, center_y, h - self.WALL_GIF_CLEARANCE),
                2 * h,
                0,
            ),
        }
        asset_directory = self.PIXEL_WALL_GIF_PATH.parent
        for side, (position, width, rotation_y) in wall_specs.items():
            gif_path = asset_directory / self.WALL_GIF_FILENAMES[side]
            if side == "-Z" and not gif_path.is_file():
                gif_path = self.PIXEL_WALL_GIF_PATH
            if not gif_path.is_file():
                continue
            panel = _GifWallAnimation(
                parent=self,
                position=position,
                gif_path=gif_path,
                width=width,
                height=local_height,
                rotation_y=rotation_y,
            )
            side_name = side.replace("+", "positive_").replace("-", "negative_").lower()
            panel.name = f"enclosure_wall_gif_{side_name}"
            self._wall_gifs[side] = panel

        self._pixel_wall = self._wall_gifs.get("-Z")
        if self._pixel_wall is None:
            self._pixel_wall = _PixelWallAnimation(
                parent=self,
                position=Vec3(0, 1.3, -h + self.WALL_GIF_CLEARANCE),
            )
            self._pixel_wall.rotation_y = 90
            self._pixel_wall.scale_y = 1 / self.scale_y
            self._pixel_wall.scale_z = 1 / self.scale_x

    def _build_bottom_city(self) -> None:
        if self._city_shadow_overlay is not None:
            destroy(self._city_shadow_overlay)
            self._city_shadow_overlay = None
        if self._bottom_city is not None:
            destroy(self._bottom_city)
            self._bottom_city = None
        if not self.has_city_model:
            return

        model = load_model(
            self.CITY_MODEL_PATH.stem,
            folder=self.CITY_MODEL_PATH.parent,
            file_types=(self.CITY_MODEL_PATH.suffix,),
        )
        if model is None:
            raise ValueError(f"Unable to load city model: {self.CITY_MODEL_PATH}")

        city = Entity(
            parent=self,
            name="enclosure_bottom_city",
            model=model,
            position=(0, 0, 0),
            rotation_y=180,
            shader=unlit_shader,
            unlit=True
        )
        ground_geometry = None
        for geometry in city.findAllMatches("**/+GeomNode"):
            geom_node = geometry.node()
            for geom_index in range(geom_node.getNumGeoms()):
                state = geom_node.getGeomState(geom_index)
                material = (
                    state.getAttrib(MaterialAttrib).getMaterial()
                    if state.hasAttrib(MaterialAttrib)
                    else None
                )
                if (
                    material is not None
                    and material.getName() == self.CITY_GROUND_MATERIAL_NAME
                ):
                    ground_geometry = geometry

                if (
                    material is not None
                    and material.hasEmission()
                    and material.getEmission().getXyz().lengthSquared() > 0
                ):
                    rgb = material.getEmission().getXyz()
                elif material is None or not material.hasBaseColor():
                    fallback_color = (
                        self.CITY_GROUND_COLOR
                        if material is not None
                        and material.getName() == self.CITY_GROUND_MATERIAL_NAME
                        else self.CITY_MISSING_COLOR
                    )
                    rgb = Vec3(
                        *(channel / 255 for channel in fallback_color)
                    )
                else:
                    base_color = material.getBaseColor().getXyz()
                    channels = tuple(base_color)
                    if (
                        max(channels) - min(channels)
                        <= self.CITY_NEUTRAL_COLOR_MAX_CHANNEL_DIFFERENCE
                        and max(channels) >= self.CITY_NEUTRAL_COLOR_MIN_BRIGHTNESS
                    ):
                        rgb = Vec3(
                            *(
                                channel / 255
                                for channel in self.CITY_NEUTRAL_ARCHITECTURE_COLOR
                            )
                        )
                    else:
                        rgb = Vec3(
                            *(
                                channel ** self.CITY_BASE_COLOR_GAMMA
                                for channel in channels
                            )
                        )
                color_scale = ColorScaleAttrib.make(
                    Vec4(rgb.x, rgb.y, rgb.z, 1)
                )
                geom_node.setGeomState(
                    geom_index,
                    state.addAttrib(color_scale),
                )

        bounds = city.getTightBounds(self)
        if bounds is None:
            destroy(city)
            raise ValueError(f"City model has no renderable geometry: {self.CITY_MODEL_PATH}")

        minimum, maximum = bounds
        dimensions = maximum - minimum
        footprint = max(dimensions.x, dimensions.z)
        if footprint <= 0 or dimensions.y <= 0:
            destroy(city)
            raise ValueError(f"City model has invalid dimensions: {self.CITY_MODEL_PATH}")

        side_length = self._half_size * 2
        world_floor_y = self.y + self._floor_y * self.scale_y
        world_ceiling_y = self.y + self._ceiling_y * self.scale_y
        base_fit_scale = min(
            side_length * self.CITY_MAX_FOOTPRINT_RATIO / footprint,
            side_length * self.CITY_MAX_HEIGHT_RATIO / dimensions.y,
            max(
                0.0,
                -world_floor_y - self.CITY_BASE_FLOOR_CLEARANCE,
            ) / dimensions.y,
        )
        available_city_height = max(
            0.0,
            world_ceiling_y
            - world_floor_y
            - self.CITY_FLOOR_CLEARANCE,
        )
        available_city_footprint = min(
            2 * self._half_size * self.scale_x,
            2 * self._half_size * self.scale_z,
        )
        fit_scale = min(
            base_fit_scale * self.CITY_MODEL_SCALE,
            available_city_height / dimensions.y,
            available_city_footprint / footprint,
        )
        city.scale = Vec3(
            fit_scale / self.scale_x,
            fit_scale / self.scale_y,
            fit_scale / self.scale_z,
        )
        city.position = (
            -(minimum.x + maximum.x) / 2 * fit_scale / self.scale_x,
            (
                world_floor_y
                + self.CITY_FLOOR_CLEARANCE
                - self.y
                - minimum.y * fit_scale
            ) / self.scale_y,
            -(minimum.z + maximum.z) / 2 * fit_scale / self.scale_z,
        )
        if ground_geometry is not None:
            self._city_shadow_overlay = self._build_city_shadow_overlay(
                city,
                ground_geometry,
            )
        self._bottom_city = city

    def _build_city_shadow_overlay(
        self,
        city: Entity,
        ground_geometry: NodePath,
    ) -> Optional[Entity]:
        bounds = ground_geometry.getTightBounds(self)
        if bounds is None:
            raise ValueError("City ground mesh has no renderable bounds")

        minimum, maximum = bounds
        width = maximum.x - minimum.x
        depth = maximum.z - minimum.z
        if width <= 0 or depth <= 0:
            raise ValueError("City ground mesh has invalid horizontal dimensions")

        ground_y = (minimum.y + maximum.y) / 2
        resolution = self.CITY_SHADOW_RESOLUTION
        shadow_mask = Image.new("L", (resolution, resolution), 0)
        draw = ImageDraw.Draw(shadow_mask)
        direction_x, direction_y, direction_z = self.CITY_SHADOW_DIRECTION
        if direction_y >= 0:
            raise ValueError("City shadow direction must point toward the ground")

        for geometry in city.findAllMatches("**/+GeomNode"):
            if geometry == ground_geometry:
                continue
            geom_node = geometry.node()
            transform = geometry.getMat(self)
            for geom_index in range(geom_node.getNumGeoms()):
                geom = geom_node.getGeom(geom_index)
                vertex_data = geom.getVertexData()
                vertex_reader = GeomVertexReader(vertex_data, "vertex")
                vertices = []
                for row in range(vertex_data.getNumRows()):
                    vertex_reader.setRow(row)
                    vertices.append(
                        transform.xformPoint(vertex_reader.getData3f())
                    )

                for primitive_index in range(geom.getNumPrimitives()):
                    triangles = geom.getPrimitive(primitive_index).decompose()
                    for triangle_index in range(triangles.getNumPrimitives()):
                        start = triangles.getPrimitiveStart(triangle_index)
                        end = triangles.getPrimitiveEnd(triangle_index)
                        if end - start != 3:
                            continue

                        triangle = [
                            vertices[triangles.getVertex(vertex_index)]
                            for vertex_index in range(start, end)
                        ]
                        if max(vertex.y for vertex in triangle) <= ground_y + 0.01:
                            continue

                        projected = []
                        for vertex in triangle:
                            distance = max(
                                0.0,
                                (ground_y - vertex.y) / direction_y,
                            )
                            shadow_x = vertex.x + direction_x * distance
                            shadow_z = vertex.z + direction_z * distance
                            projected.append(
                                (
                                    round(
                                        (shadow_x - minimum.x)
                                        / width
                                        * (resolution - 1)
                                    ),
                                    round(
                                        (maximum.z - shadow_z)
                                        / depth
                                        * (resolution - 1)
                                    ),
                                )
                            )
                        draw.polygon(projected, fill=self.CITY_SHADOW_OPACITY)

        if shadow_mask.getbbox() is None:
            return None

        shadow_mask = shadow_mask.filter(
            ImageFilter.GaussianBlur(self.CITY_SHADOW_BLUR)
        )
        shadow_image = Image.new("RGBA", (resolution, resolution), (0, 0, 0, 0))
        shadow_image.putalpha(shadow_mask)
        shadow_texture = UrsinaTexture(shadow_image, filtering="linear")
        center_x = (minimum.x + maximum.x) / 2
        center_z = (minimum.z + maximum.z) / 2
        overlay = Entity(
            parent=self,
            name="city_ground_shadows",
            model="plane",
            position=(
                center_x / self.scale_x,
                ground_y + self.CITY_SHADOW_CLEARANCE,
                center_z / self.scale_z,
            ),
            scale=(width / self.scale_x, 1, depth / self.scale_z),
            texture=shadow_texture,
            shader=unlit_shader,
            color=color.white,
            transparency=True,
            double_sided=True,
            unlit=True,
        )
        overlay.setDepthWrite(False)
        return overlay

    def _build_face_gradients(self) -> None:
        h = self._half_size
        self._bottom_face = Entity(
            parent=self,
            name="enclosure_bottom_face",
            model="plane",
            position=(0, self._floor_y - self.ENCLOSURE_FACE_CLEARANCE, 0),
            scale=(2 * h, 1, 2 * h),
            color=self.CITY_BOTTOM_FACE_COLOR,
            shader=unlit_shader,
            double_sided=True,
            unlit=True,
        )
        palettes = (
            ("#07131F", "#100B1D", "#080D1C", "#0B1520"),
            ("#100B1D", "#07131F", "#0B1520", "#080D1C"),
        )
        face_specs = (
            (1, self._floor_y, 1.0, 0),
            (1, self._ceiling_y, -1.0, 1),
            (0, -h, 1.0, 0),
            (0, h, -1.0, 1),
            (2, -h, 1.0, 1),
            (2, h, -1.0, 0),
        )
        for index, (normal_axis, plane, inward, palette_index) in enumerate(face_specs):
            if normal_axis == 1 and plane == self._floor_y:
                continue

            first_axis = (normal_axis + 1) % 3
            second_axis = (normal_axis + 2) % 3
            minimum = [-h, -h, -h]
            maximum = [h, h, h]
            minimum[1] = self._wall_floor_y
            maximum[1] = self._ceiling_y
            vertices = []
            for first, second in (
                (minimum[first_axis], minimum[second_axis]),
                (maximum[first_axis], minimum[second_axis]),
                (maximum[first_axis], maximum[second_axis]),
                (minimum[first_axis], maximum[second_axis]),
            ):
                point = [0.0, 0.0, 0.0]
                point[normal_axis] = (
                    plane + inward * self.ENCLOSURE_FACE_CLEARANCE
                )
                point[first_axis] = first
                point[second_axis] = second
                vertices.append(tuple(point))

            colors = []
            for code in palettes[palette_index]:
                base_color = color.hex(code)
                colors.append(
                    color.rgba(
                        base_color.r,
                        base_color.g,
                        base_color.b,
                        self.BACKGROUND_OPACITY,
                    )
                )
            mesh = Mesh(
                vertices=vertices,
                triangles=[(0, 1, 2), (0, 2, 3)],
                colors=colors,
                static=True,
            )
            self._gradient_entities.append(
                self._make_mesh_entity(
                    mesh,
                    f"enclosure_gradient_{index}",
                    transparency=False,
                )
            )
