import pytest
from PIL import Image
from panda3d.core import ColorScaleAttrib, Material, MaterialAttrib, RenderState
from ursina import Mesh, Vec3, camera, scene, time
from ursina.shaders import unlit_shader

from bloxorz.graphics.cyber_grid_background import _GifWallAnimation, CyberGridBackground


def test_background_assets_use_package_asset_directory():
    gif_directory = CyberGridBackground.PIXEL_WALL_GIF_PATH.parent

    assert CyberGridBackground.PIXEL_WALL_GIF_PATH.name == "wall_front.gif"
    assert CyberGridBackground.PIXEL_WALL_GIF_PATH.is_file()
    assert all(
        (gif_directory / filename).is_file()
        for filename in CyberGridBackground.WALL_GIF_FILENAMES.values()
    )
    assert CyberGridBackground.CITY_MODEL_PATH.is_file()


def test_cyber_grid_background_has_purple_grid_except_front_gif(game_app):
    background = game_app.background_view

    assert background.parent == scene
    assert len(background._grid_entities) == 2
    assert all(entity.model.vertices for entity in background._grid_entities)
    assert background._runners == []
    assert background._runner_entities == []
    assert background._half_size >= game_app.camera_ctrl.max_zoom_distance
    assert background.position == Vec3(
        background._board_center_world[0],
        0,
        background._board_center_world[2],
    )
    assert background.scale_x == pytest.approx(
        background.CITY_HORIZONTAL_SCALE
    )
    assert background.scale_z == pytest.approx(
        background.CITY_HORIZONTAL_SCALE
    )
    assert background.scale_y == pytest.approx(
        background.ENCLOSURE_HEIGHT_SCALE
    )
    assert background.CITY_HORIZONTAL_SCALE == pytest.approx(3.0)
    assert background.ENCLOSURE_HEIGHT_SCALE == pytest.approx(1.0)
    assert background.CITY_MODEL_SCALE == pytest.approx(1.6)
    assert background.rotation == Vec3(0, 0, 0)
    assert background._bottom_face is not None
    assert background._bottom_face.color == background.CITY_BOTTOM_FACE_COLOR
    assert background._spacing == background._half_size * 2 / background.MAX_GRID_INTERVALS
    assert background._spacing >= background._half_size * 2 / 48 * 1.29
    for entity in background._grid_entities:
        assert all(
            (vertex_color.r, vertex_color.g, vertex_color.b)
            == pytest.approx(
                (
                    background.PURPLE.r,
                    background.PURPLE.g,
                    background.PURPLE.b,
                )
            )
            for vertex_color in entity.model.colors
        )
        assert all(
            background._floor_y - 1e-5
            <= vertex[1]
            <= background._floor_y + 0.026
            for vertex in entity.model.vertices
        )
        assert all(
            max(vertex[1] for vertex in entity.model.vertices[index:index + 4])
            - min(vertex[1] for vertex in entity.model.vertices[index:index + 4])
            < 1e-5
            for index in range(0, len(entity.model.vertices), 4)
        )


def test_cyber_grid_background_recenters_and_resizes_for_each_board(
    game_app, monkeypatch, tmp_path
):
    background = game_app.background_view
    assert background.CITY_ENCLOSURE_SCALE == pytest.approx(1.2)
    model_path = tmp_path / "city.glb"
    model_path.touch()
    monkeypatch.setattr(CyberGridBackground, "CITY_MODEL_PATH", model_path)

    background.set_board_bounds(0, 8, 2, 10, camera_distance=12)

    assert background._board_center_world == (4, 0.0, -6)
    base_side_length = max(
        background.MIN_SIZE,
        9 + background.BOARD_MARGIN * 2,
        9 + background.BOARD_MARGIN * 2,
        12 * 2 * background.CAMERA_MARGIN,
    )
    assert background._half_size * 2 == pytest.approx(
        base_side_length * background.CITY_ENCLOSURE_SCALE
    )
    assert background._floor_y * background.scale_y == pytest.approx(
        -background._half_size * background.CITY_BOTTOM_FACE_HEIGHT_RATIO
        + background.BOTTOM_FACE_RAISE
    )
    assert background._wall_floor_y * background.scale_y == pytest.approx(
        -background._half_size * background.CITY_BOTTOM_FACE_HEIGHT_RATIO
    )
    assert background.scale_x == pytest.approx(background.CITY_HORIZONTAL_SCALE)
    assert background.scale_z == pytest.approx(background.CITY_HORIZONTAL_SCALE)
    assert background.scale_y == pytest.approx(1.0)


def test_enclosure_ceiling_clears_board_height(game_app):
    background = game_app.background_view
    board_height = game_app.BOARD_WORLD_OFFSET[1]
    enclosure_floor_y = background.y + background._floor_y * background.scale_y
    enclosure_ceiling_y = (
        background.y + background._ceiling_y * background.scale_y
    )
    board_bounds = game_app.board_view.root.getTightBounds(scene)
    block_bounds = game_app.block_view.getTightBounds(scene)

    assert board_bounds is not None
    assert block_bounds is not None
    assert board_bounds[0].y >= enclosure_floor_y
    assert block_bounds[1].y < enclosure_ceiling_y
    assert enclosure_ceiling_y >= (
        board_height + background.BOARD_VERTICAL_MARGIN
    )


def test_raising_bottom_keeps_wall_and_ceiling_positions(game_app, monkeypatch):
    background = game_app.background_view
    bounds = game_app.game.board
    camera_distance = game_app.camera_ctrl.max_zoom_distance

    def fixed_face_bounds():
        return tuple(
            coordinate
            for entity in background._gradient_entities
            for point in entity.getTightBounds(scene)
            for coordinate in point
        )

    def wall_gif_transform():
        panel = background._pixel_wall
        assert panel is not None
        return tuple(panel.position) + tuple(panel.scale) + tuple(panel.rotation)

    monkeypatch.setattr(CyberGridBackground, "BOTTOM_FACE_RAISE", 0.0)
    background.set_board_bounds(
        bounds.min_x,
        bounds.max_x,
        bounds.min_y,
        bounds.max_y,
        camera_distance,
        board_height=game_app.BOARD_WORLD_OFFSET[1],
    )
    initial_floor = background.y + background._floor_y * background.scale_y
    initial_fixed_faces = fixed_face_bounds()
    initial_wall_gif_transform = wall_gif_transform()
    initial_wall_floor = background._wall_floor_y
    initial_ceiling = background.y + background._ceiling_y * background.scale_y

    monkeypatch.setattr(CyberGridBackground, "BOTTOM_FACE_RAISE", 5.0)
    background.set_board_bounds(
        bounds.min_x,
        bounds.max_x,
        bounds.min_y,
        bounds.max_y,
        camera_distance,
        board_height=game_app.BOARD_WORLD_OFFSET[1],
    )

    raised_floor = background.y + background._floor_y * background.scale_y
    assert raised_floor - initial_floor == pytest.approx(5.0)
    assert background._wall_floor_y == pytest.approx(initial_wall_floor)
    assert (
        background.y + background._ceiling_y * background.scale_y
    ) == pytest.approx(initial_ceiling)
    assert fixed_face_bounds() == pytest.approx(initial_fixed_faces)
    assert wall_gif_transform() == pytest.approx(initial_wall_gif_transform)
    assert all(
        background._floor_y - 1e-5
        <= vertex[1]
        <= background._floor_y + 0.026
        for entity in background._grid_entities
        for vertex in entity.model.vertices
    )


def test_city_shrinks_when_enclosure_size_is_reduced(game_app, monkeypatch):
    background = game_app.background_view
    if not background.CITY_MODEL_PATH.is_file():
        pytest.skip("City model is not available")

    monkeypatch.setattr(CyberGridBackground, "CITY_ENCLOSURE_SCALE", 2.0)
    background.set_board_bounds(0, 8, 2, 10, camera_distance=12)
    previous_enclosure_side = background._half_size * 2
    previous_city_bounds = background._bottom_city.getTightBounds(background)
    assert previous_city_bounds is not None
    previous_city_size = previous_city_bounds[1] - previous_city_bounds[0]

    monkeypatch.setattr(CyberGridBackground, "CITY_ENCLOSURE_SCALE", 1.2)
    background.set_board_bounds(0, 8, 2, 10, camera_distance=12)
    enclosure_ratio = background._half_size * 2 / previous_enclosure_side
    current_city_bounds = background._bottom_city.getTightBounds(background)
    assert current_city_bounds is not None
    current_city_size = current_city_bounds[1] - current_city_bounds[0]

    assert enclosure_ratio == pytest.approx(0.6)
    city_shrink_ratios = (
        current_city_size.x / previous_city_size.x,
        current_city_size.y / previous_city_size.y,
        current_city_size.z / previous_city_size.z,
    )
    assert all(0.4 < ratio < enclosure_ratio for ratio in city_shrink_ratios)


def test_enclosure_expansion_preserves_city_board_block_and_camera(game_app, monkeypatch):
    background = game_app.background_view
    if not background.CITY_MODEL_PATH.is_file():
        pytest.skip("City model is not available")

    board = game_app.game.board
    board_bounds = (
        board.min_x,
        board.max_x,
        board.min_y,
        board.max_y,
        game_app.camera_ctrl.max_zoom_distance,
    )

    def world_bounds(entity):
        bounds = entity.getTightBounds(scene)
        assert bounds is not None
        return tuple(bounds[0]) + tuple(bounds[1])

    monkeypatch.setattr(CyberGridBackground, "CITY_HORIZONTAL_SCALE", 3.5)
    monkeypatch.setattr(CyberGridBackground, "ENCLOSURE_HEIGHT_SCALE", 2.0)
    monkeypatch.setattr(CyberGridBackground, "CITY_MODEL_SCALE", 2.0)
    background.set_board_bounds(*board_bounds[:4], camera_distance=board_bounds[4])

    city_before = world_bounds(background._bottom_city)
    city_center_before = tuple(
        (city_before[index] + city_before[index + 3]) / 2
        for index in range(3)
    )
    board_before = world_bounds(game_app.board_view.root)
    block_before = Vec3(game_app.block_view.world_position)
    camera_before = Vec3(camera.position)
    floor_before = background.y + background._floor_y * background.scale_y
    monkeypatch.setattr(CyberGridBackground, "CITY_HORIZONTAL_SCALE", 1.75)
    monkeypatch.setattr(CyberGridBackground, "ENCLOSURE_HEIGHT_SCALE", 1.0)
    monkeypatch.setattr(CyberGridBackground, "CITY_MODEL_SCALE", 1.0)
    background.set_board_bounds(*board_bounds[:4], camera_distance=board_bounds[4])

    assert background.scale_x == pytest.approx(1.75)
    assert background.scale_z == pytest.approx(1.75)
    assert background.scale_y == pytest.approx(1.0)
    city_after = world_bounds(background._bottom_city)
    city_center_after = tuple(
        (city_after[index] + city_after[index + 3]) / 2
        for index in range(3)
    )
    assert city_center_after[:1] + city_center_after[2:] == pytest.approx(
        city_center_before[:1] + city_center_before[2:],
        abs=1e-4,
    )
    city_size_before = tuple(
        city_before[index + 3] - city_before[index]
        for index in range(3)
    )
    city_size_after = tuple(
        city_after[index + 3] - city_after[index]
        for index in range(3)
    )
    assert city_size_before == pytest.approx(
        tuple(size * 2 for size in city_size_after),
        rel=1e-4,
    )
    world_floor_y = background.y + background._floor_y * background.scale_y
    assert city_after[1] - world_floor_y == pytest.approx(1.0, abs=1e-4)
    assert world_floor_y == pytest.approx(floor_before)
    vertical_span_after = (
        background.y
        + background._ceiling_y * background.scale_y
        - world_floor_y
    )
    base_floor_y = floor_before - background.BOTTOM_FACE_RAISE
    expected_ceiling_after = (
        base_floor_y
        + (2 * background._half_size - base_floor_y) / 2
    )
    assert vertical_span_after == pytest.approx(
        expected_ceiling_after - floor_before
    )
    assert world_bounds(game_app.board_view.root) == pytest.approx(board_before)
    assert tuple(game_app.block_view.world_position) == pytest.approx(block_before)
    assert tuple(camera.position) == pytest.approx(camera_before)


def test_cyber_grid_background_is_static_while_camera_rotates(game_app):
    background = game_app.background_view
    original_camera_rotation = Vec3(camera.rotation)
    original_transform = (Vec3(background.position), Vec3(background.rotation))

    try:
        camera.rotation_y += 30
        camera.rotation_x += 20
        assert Vec3(background.position) == original_transform[0]
        assert Vec3(background.rotation) == original_transform[1]
    finally:
        camera.rotation = original_camera_rotation


def test_cyber_grid_background_uses_opaque_face_gradients(game_app):
    background = game_app.background_view

    assert len(background._gradient_entities) == 5
    assert background._bottom_face is not None
    assert background._bottom_face.name == "enclosure_bottom_face"
    assert background._bottom_face.color == background.CITY_BOTTOM_FACE_COLOR
    assert background._bottom_face.unlit is True
    assert all(entity.transparency is False for entity in background._gradient_entities)
    assert all(entity.getDepthWrite() is True for entity in background._gradient_entities)
    for wall_entity in background._gradient_entities[1:]:
        vertex_y = [vertex[1] for vertex in wall_entity.model.vertices]
        assert min(vertex_y) == pytest.approx(background._wall_floor_y)
        assert max(vertex_y) == pytest.approx(background._ceiling_y)
    assert all(
        vertex_color.a == pytest.approx(background.BACKGROUND_OPACITY)
        for entity in background._gradient_entities
        for vertex_color in entity.model.colors
    )


def test_pixel_wall_animation_displays_on_the_front_face(game_app, monkeypatch):
    background = game_app.background_view
    pixel_wall = background._pixel_wall

    assert pixel_wall is not None
    assert pixel_wall.parent == background
    assert pixel_wall.position.z == pytest.approx(
        -background._half_size + background.WALL_GIF_CLEARANCE
    )
    assert pixel_wall.rotation_y == pytest.approx(
        180 if isinstance(pixel_wall, _GifWallAnimation) else 90
    )
    update_interval = (
        pixel_wall._durations[0]
        if isinstance(pixel_wall, _GifWallAnimation)
        else pixel_wall.FRAME_DURATION
    )

    monkeypatch.setattr(time, "dt", update_interval, raising=False)
    pixel_wall.update()
    if isinstance(pixel_wall, _GifWallAnimation):
        assert pixel_wall.texture is pixel_wall._frames[1]
    else:
        assert pixel_wall.model is pixel_wall._frames[1]

def test_background_loads_independent_gifs_on_each_wall(game_app, monkeypatch, tmp_path):
    wall_gif_filenames = {
        "-X": "wall_left.gif",
        "+X": "wall_right.gif",
        "-Z": "wall_front.gif",
        "+Z": "wall_back.gif",
    }
    for index, filename in enumerate(wall_gif_filenames.values()):
        frames = (
            Image.new("RGBA", (32, 16), (255, index * 40, 0, 255)),
            Image.new("RGBA", (32, 16), (0, 0, 255, 255)),
        )
        frames[0].save(
            tmp_path / filename,
            save_all=True,
            append_images=frames[1:],
            duration=(100, 100),
            loop=0,
        )
    monkeypatch.setattr(CyberGridBackground, "PIXEL_WALL_GIF_PATH", tmp_path / "pixel_wall.gif")
    monkeypatch.setattr(
        CyberGridBackground,
        "WALL_GIF_FILENAMES",
        wall_gif_filenames,
    )
    background = game_app.background_view
    background._build_pixel_wall()
    assert set(background._wall_gifs) == set(wall_gif_filenames)
    assert background._pixel_wall is background._wall_gifs["-Z"]
    assert len({panel._frames[0] for panel in background._wall_gifs.values()}) == 4
    expected_wall_height = background._ceiling_y - background._wall_floor_y
    for side, panel in background._wall_gifs.items():
        assert isinstance(panel, _GifWallAnimation)
        assert len(panel._frames) == 2
        assert panel._frames[0].width == 32
        assert panel._frames[0].height == 16
        assert panel.scale_y == pytest.approx(expected_wall_height)
        assert panel.scale_x == pytest.approx(2 * background._half_size)
        expected_axis = 0 if side.endswith("X") else 2
        expected_coordinate = (
            -background._half_size + background.WALL_GIF_CLEARANCE
            if side.startswith("-")
            else background._half_size - background.WALL_GIF_CLEARANCE
        )
        assert panel.position[expected_axis] == pytest.approx(expected_coordinate)

    monkeypatch.setattr(time, "dt", 0.11, raising=False)
    panel = background._wall_gifs["-Z"]
    panel.update()
    assert panel._frame_index == 1
    assert panel.texture is panel._frames[1]


def test_bottom_city_is_centered_fitted_and_rebuilt(game_app, monkeypatch, tmp_path):
    model_path = tmp_path / "city.glb"
    model_path.touch()
    monkeypatch.setattr(CyberGridBackground, "CITY_MODEL_PATH", model_path)
    loaded_models = []

    def fake_load_model(name, folder, file_types):
        assert name == "city"
        assert folder == tmp_path
        assert file_types == (".glb",)
        model = Mesh(
            vertices=[
                (-2, -1, -3),
                (2, -1, -3),
                (2, 3, -3),
                (-2, 3, -3),
                (-2, -1, 3),
                (2, -1, 3),
                (2, 3, 3),
                (-2, 3, 3),
            ],
            triangles=[
                (0, 1, 2), (0, 2, 3),
                (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1),
                (3, 2, 6), (3, 6, 7),
                (0, 3, 7), (0, 7, 4),
                (1, 5, 6), (1, 6, 2),
            ],
            static=True,
        )
        material = Material("city_color_test")
        material.setBaseColor((0.2, 0.4, 0.6, 1))
        material.setEmission((0.1, 0.2, 0.3, 0))
        model.find("**/+GeomNode").node().setGeomState(
            0,
            RenderState.make(MaterialAttrib.make(material)),
        )
        loaded_models.append(model)
        return model

    monkeypatch.setattr(
        "bloxorz.graphics.cyber_grid_background.load_model",
        fake_load_model,
    )
    background = game_app.background_view
    background._build_bottom_city()
    city = background._bottom_city

    assert city is not None
    assert city.name == "enclosure_bottom_city"
    assert city.rotation_y == pytest.approx(180)
    assert city.shader == unlit_shader
    base_fit_scale = min(
        background._half_size * 2 * background.CITY_MAX_FOOTPRINT_RATIO / 6,
        background._half_size * 2 * background.CITY_MAX_HEIGHT_RATIO / 4,
        (
            -background._floor_y * background.scale_y
            - background.CITY_BASE_FLOOR_CLEARANCE
        ) / 4,
    )
    expected_scale = min(
        base_fit_scale * background.CITY_MODEL_SCALE,
        (
            background._ceiling_y * background.scale_y
            - background._floor_y * background.scale_y
            - background.CITY_FLOOR_CLEARANCE
        ) / 4,
        min(
            background._half_size * 2 * background.scale_x,
            background._half_size * 2 * background.scale_z,
        ) / 6,
    )
    assert city.scale_x == pytest.approx(
        expected_scale / background.scale_x
    )
    assert city.scale_y == pytest.approx(expected_scale / background.scale_y)
    assert city.scale_z == pytest.approx(
        expected_scale / background.scale_z
    )
    assert city.x == pytest.approx(0)
    assert city.z == pytest.approx(0)
    assert (
        background.y + background.scale_y * city.y
        == pytest.approx(
            background.y
            + background.scale_y * background._floor_y
            + background.CITY_FLOOR_CLEARANCE
            + expected_scale
        )
    )
    city_bounds = city.getTightBounds(background)
    assert city_bounds is not None
    assert (
        background.scale_y
        * (city_bounds[0].y - background._floor_y)
    ) == pytest.approx(background.CITY_FLOOR_CLEARANCE, abs=1e-4)
    geometry = city.find("**/+GeomNode")
    geometry_state = geometry.node().getGeomState(0)
    material = geometry_state.getAttrib(MaterialAttrib).getMaterial()
    color_scale = geometry_state.getAttrib(ColorScaleAttrib).getScale()
    assert tuple(color_scale) == pytest.approx((0.1, 0.2, 0.3, 1), abs=0.001)
    assert tuple(material.getBaseColor()) == pytest.approx((0.2, 0.4, 0.6, 1))
    assert tuple(material.getEmission()) == pytest.approx((0.1, 0.2, 0.3, 0))

    original_city_scale = city.scale_x
    background._half_size *= 1.5
    background._floor_y = (
        -background._half_size
        * background.CITY_BOTTOM_FACE_HEIGHT_RATIO
        + background.BOTTOM_FACE_RAISE
    ) / background.scale_y
    background._wall_floor_y = (
        -background._half_size
        * background.CITY_BOTTOM_FACE_HEIGHT_RATIO
        / background.scale_y
    )
    background._build_bottom_city()
    assert background._bottom_city is not None
    rebuilt_base_scale = min(
        background._half_size * 2 * background.CITY_MAX_FOOTPRINT_RATIO / 6,
        background._half_size * 2 * background.CITY_MAX_HEIGHT_RATIO / 4,
        (
            -background._floor_y * background.scale_y
            - background.CITY_BASE_FLOOR_CLEARANCE
        ) / 4,
    )
    expected_rebuilt_scale = min(
        rebuilt_base_scale * background.CITY_MODEL_SCALE,
        (
            background._ceiling_y * background.scale_y
            - background._floor_y * background.scale_y
            - background.CITY_FLOOR_CLEARANCE
        ) / 4,
        min(
            background._half_size * 2 * background.scale_x,
            background._half_size * 2 * background.scale_z,
        ) / 6,
    )
    assert background._bottom_city.scale_x == pytest.approx(
        expected_rebuilt_scale / background.scale_x
    )
    assert expected_rebuilt_scale > original_city_scale
    assert len(loaded_models) == 2
    assert city not in background.children


def test_city_glb_renders_material_colors_and_emission(game_app):
    city = game_app.background_view._bottom_city
    assert city is not None
    assert city.shader == unlit_shader
    city_bounds = city.getTightBounds(game_app.background_view)
    assert city_bounds is not None
    city_size = city_bounds[1] - city_bounds[0]
    assert city.scale_x * game_app.background_view.scale_x == pytest.approx(
        city.scale_y * game_app.background_view.scale_y
    )
    assert city.scale_z * game_app.background_view.scale_z == pytest.approx(
        city.scale_y * game_app.background_view.scale_y
    )
    enclosure_side = game_app.background_view._half_size * 2
    assert max(city_size.x, city_size.z) <= (
        enclosure_side * game_app.background_view.CITY_MAX_FOOTPRINT_RATIO
    )
    assert city_size.y <= (
        enclosure_side * game_app.background_view.CITY_MAX_HEIGHT_RATIO
    )
    background = game_app.background_view
    checked_emission = False
    checked_neutral = False
    checked_chromatic = False
    ground_mesh_found = False
    for geometry in city.findAllMatches("**/+GeomNode"):
        geom_node = geometry.node()
        for geom_index in range(geom_node.getNumGeoms()):
            state = geom_node.getGeomState(geom_index)
            material = (
                state.getAttrib(MaterialAttrib).getMaterial()
                if state.hasAttrib(MaterialAttrib)
                else None
            )
            color_scale = state.getAttrib(ColorScaleAttrib).getScale()
            if (
                material is not None
                and material.getName() == background.CITY_GROUND_MATERIAL_NAME
            ):
                ground_mesh_found = True
                expected_color = tuple(
                    channel / 255 for channel in background.CITY_GROUND_COLOR
                )
            elif (
                material is not None
                and material.hasEmission()
                and material.getEmission().getXyz().lengthSquared() > 0
            ):
                expected_color = tuple(material.getEmission().getXyz())
                checked_emission = True
            elif material is None or not material.hasBaseColor():
                fallback = (
                    background.CITY_MISSING_COLOR
                    if material is None
                    or material.getName() != background.CITY_GROUND_MATERIAL_NAME
                    else background.CITY_GROUND_COLOR
                )
                expected_color = tuple(channel / 255 for channel in fallback)
            else:
                base_color = tuple(material.getBaseColor().getXyz())
                if (
                    max(base_color) - min(base_color)
                    <= background.CITY_NEUTRAL_COLOR_MAX_CHANNEL_DIFFERENCE
                    and max(base_color)
                    >= background.CITY_NEUTRAL_COLOR_MIN_BRIGHTNESS
                ):
                    expected_color = tuple(
                        channel / 255
                        for channel in background.CITY_NEUTRAL_ARCHITECTURE_COLOR
                    )
                    checked_neutral = True
                else:
                    expected_color = tuple(
                        channel ** background.CITY_BASE_COLOR_GAMMA
                        for channel in base_color
                    )
                    checked_chromatic = True
            assert tuple(color_scale) == pytest.approx(
                expected_color + (1,),
                abs=0.001,
            )

    assert checked_emission
    assert checked_neutral
    assert checked_chromatic
    shadow_overlay = background._city_shadow_overlay
    assert (shadow_overlay is not None) == ground_mesh_found
    if shadow_overlay is not None:
        assert shadow_overlay.parent == background
        assert shadow_overlay.transparency is True
        assert shadow_overlay.getDepthTest() is True
        assert shadow_overlay.getDepthWrite() is False
        shadow_pixels = bytes(shadow_overlay.texture._texture.getRamImageAs("RGBA"))
        shadow_alpha = shadow_pixels[3::4]
        assert max(shadow_alpha) == background.CITY_SHADOW_OPACITY
        assert 0 < sum(alpha > 0 for alpha in shadow_alpha) < len(shadow_alpha)
