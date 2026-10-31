import pytest
from panda3d.core import GeomVertexReader
from ursina import Vec3, application, destroy, time

from bloxorz.config import CONFIG
from bloxorz.core.block.normal import NormalBlockState
from bloxorz.core.board import Board, BridgeGroup
from bloxorz.core.constants import BlockOrientation, TileType
from bloxorz.graphics.board_view import BoardView
from bloxorz.graphics.block_view import BlockView


def test_board_tile_visuals_match_their_types(game_app, monkeypatch):
    tiles = {
        (0, 0): TileType.NORMAL,
        (1, 0): TileType.FRAGILE,
        (2, 0): TileType.SWITCH_SOFT,
        (3, 0): TileType.SWITCH_HEAVY,
        (4, 0): TileType.TELEPORT,
        (5, 0): TileType.GOAL,
    }
    board = Board(
        tiles=tiles,
        goal_pos=(5, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view = BoardView()
    view.build(board)

    surfaces = {
        entity.position.x: entity
        for entity in view.root.children
        if entity.name == "tile_gradient_surface"
    }
    assert set(surfaces) == {0, 1, 2, 3, 4}
    safe_color = surfaces[0].model.colors[0]
    fragile_color = surfaces[1].model.colors[0]
    soft_color = surfaces[2].model.colors[0]
    heavy_color = surfaces[3].model.colors[0]
    teleport_color = surfaces[4].model.colors[0]
    # The machined deck stays dark enough for the hero block, while its
    # metal surface remains visible instead of disappearing into the void.
    assert 0.07 < sum(tuple(safe_color)[:3]) / 3 < 0.30
    assert safe_color.b > safe_color.r
    assert fragile_color.r > 0.2 and fragile_color.g > 0.1
    assert soft_color.b > soft_color.r
    assert heavy_color.r > heavy_color.b
    assert teleport_color.r > teleport_color.g and teleport_color.b > teleport_color.g
    safe_border = next(
        entity for entity in view.root.children
        if entity.name == "tile_neon_border" and entity.x == 0
    )
    vertices = safe_border.model.vertices
    border_area = 0.0
    for triangle in safe_border.model.triangles:
        a, b, c = [vertices[index] for index in triangle]
        border_area += abs((b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0])) / 2
    assert 0.015 < border_area < 0.09, 'Thin trims must not dominate the entire deck'
    border_colors = {tuple(value) for value in safe_border.model.colors}
    assert len(border_colors) > 1, 'Interior seams should be quieter than edges facing the void'
    assert max(value[3] for value in border_colors) > 0.95
    crack_mesh = next(
        entity for entity in view.root.children if entity.name == "fragile_crack_mesh"
    )
    assert len(crack_mesh.model.vertices) == 24
    pulse_ring = next(
        entity for entity in view.root.children if entity.name == "soft_switch_pulse"
    )
    monkeypatch.setattr(time, "dt", 0.25, raising=False)
    pulse_ring.update()
    assert pulse_ring.scale_x > 1
    assert set(view.switch_entities) == {(2, 0), (3, 0)}
    teleport = next(
        entity for entity in view.root.children if entity.name == "teleport_orbit"
    )
    teleport_nodes = [
        entity for entity in teleport.children if entity.name == "teleport_node"
    ]
    assert len(teleport_nodes) == 2
    assert [node.x for node in teleport_nodes] == pytest.approx([-0.19, 0.19])
    assert teleport_nodes[0].model is not teleport_nodes[1].model
    assert all(len(node.model.vertices) == 25 for node in teleport_nodes)
    assert all(len(node.model.triangles) == 24 for node in teleport_nodes)
    assert all(
        (0.0, 0.0, 0.0) in node.model.vertices
        and all(
            max(abs(vertex[0]), abs(vertex[2])) > 0
            for vertex in node.model.vertices[1:]
        )
        for node in teleport_nodes
    )
    assert any(entity.name == "teleport_connector" for entity in teleport.children)
    teleport_rotation = teleport.rotation_y
    teleport.update()
    assert teleport.rotation_y != teleport_rotation

    heavy_switch = view.switch_entities[(3, 0)]
    heavy_bar = heavy_switch.children[0]
    original_bar_color = Vec3(
        heavy_bar.color.r,
        heavy_bar.color.g,
        heavy_bar.color.b,
    )
    heavy_switch.update()
    assert Vec3(heavy_bar.color.r, heavy_bar.color.g, heavy_bar.color.b) != original_bar_color

    beacon = next(
        entity for entity in view.root.children if entity.name == "goal_beacon"
    )
    core = next(
        entity for entity in beacon.children if entity.name == "goal_beacon_core"
    )
    beam_heights = [vertex[1] for vertex in core.model.vertices]
    assert max(beam_heights) - min(beam_heights) == 1.7
    tip = next(
        entity for entity in beacon.children if entity.name == "goal_beacon_tip"
    )
    tip_heights = [vertex[1] for vertex in tip.model.vertices]
    assert tip_heights.count(max(tip_heights)) == 1
    assert max(tip_heights) == pytest.approx(0.3)
    particle = next(
        entity for entity in beacon.children if entity.name == "goal_particle"
    )
    initial_particle_position = Vec3(particle.position)
    monkeypatch.setattr(time, "dt", 0.25, raising=False)
    beacon.update()
    assert Vec3(particle.position) != initial_particle_position
    assert particle.color.a > 0

    view.clear()
    destroy(view.root)


def test_block_mesh_uses_two_titanium_modules(game_app):
    view = BlockView()
    try:
        modules = [child for child in view.mesh.children if child.model is not None]
        assert len(modules) == 2
        assert all(module.texture is not None for module in modules)
        assert tuple(view.mesh.color)[:3] == pytest.approx((1.0, 1.0, 1.0))
        assert view.split_mesh_1.color != view.split_mesh_2.color
    finally:
        destroy(view)


def test_open_bridge_is_gold_with_red_outline(game_app, monkeypatch):
    monkeypatch.setattr(CONFIG.animation, 'stage_intro_anim', False)
    board = Board(
        tiles={(0, 0): TileType.NORMAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
        bridges={
            "gold": BridgeGroup(
                group_id="gold",
                tiles=[(1, 0)],
                initially_open=False,
                is_open=False,
            )
        },
    )
    view = BoardView()
    view.build(board)

    bridge = view.bridge_entities[(1, 0)]
    board.bridges["gold"].open()
    view.update_bridges(board)
    assert bridge.visible
    outline = next(
        entity for entity in bridge.children if entity.name == "tile_neon_border"
    )
    # The visible tint combines the vertex color with the entity color scale.
    outline_color = tuple(a * b for a, b in zip(outline.color, outline.model.colors[0]))
    assert bridge.color.r > 0.9 and bridge.color.g > 0.7
    assert outline_color[0] > 0.9 and outline_color[1] < 0.3
    destroy(view.root)


def test_landing_highlight_fades_back_to_the_board(game_app, monkeypatch):
    monkeypatch.setattr(CONFIG.animation, 'stage_intro_anim', False)
    view = BoardView()
    board = Board(
        tiles={(0, 0): TileType.NORMAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view.build(board)
    border = next(part for part in view.tile_parts[(0, 0)] if part.name == 'tile_neon_border')
    baseline = tuple(border.color)
    view.animate_landing([(0, 0)])
    lifted = tuple(border.color)
    assert sum(lifted[:3]) > sum(baseline[:3])

    monkeypatch.setattr(time, 'dt', 0.04, raising=False)
    for sequence in list(application.sequences):
        sequence.update()
    view.update()
    halfway = tuple(border.color)
    assert sum(baseline[:3]) < sum(halfway[:3]) < sum(lifted[:3])
    for _ in range(4):
        for sequence in list(application.sequences):
            sequence.update()
        view.update()
    assert tuple(border.color) == pytest.approx(baseline)
    assert not any(child.name == 'tile_landing_flash' for child in view.root.children)
    view.clear()
    destroy(view.root)


def test_fragile_cracks_are_batched_into_one_mesh(game_app):
    fragile_tiles = {(x, 0): TileType.FRAGILE for x in range(11)}
    fragile_tiles[(11, 0)] = TileType.GOAL
    board = Board(
        tiles=fragile_tiles,
        goal_pos=(11, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view = BoardView()
    view.build(board)

    crack_meshes = [
        entity for entity in view.root.children if entity.name == "fragile_crack_mesh"
    ]
    assert len(crack_meshes) == 1
    assert len(crack_meshes[0].model.vertices) == 11 * 6 * 4
    destroy(view.root)


@pytest.mark.parametrize('block_width', [0.86, 0.94])
def test_goal_is_open_for_the_full_width_of_the_standing_block(engine, monkeypatch, block_width):
    """The goal rim and shaft must not visually plug the block's descent path."""
    monkeypatch.setattr(CONFIG.animation, 'stage_intro_anim', False)
    monkeypatch.setattr(CONFIG.block, 'unit_scale_1', block_width)
    board = Board(
        tiles={(0, 0): TileType.NORMAL, (1, 0): TileType.GOAL},
        goal_pos=(1, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view = BoardView()
    view.build(board)
    try:
        well = view.goal_entity
        rim = next(part for part in view.tile_parts[(1, 0)]
                   if part.model is not None and part is not well
                   and abs(part.y - CONFIG.board.goal_rim_y) < 1e-6)
        half_block_with_clearance = CONFIG.block.unit_scale_1 / 2 + 0.01
        aperture_points = [(0, 0), (half_block_with_clearance, 0), (-half_block_with_clearance, 0),
                           (0, half_block_with_clearance), (0, -half_block_with_clearance),
                           (half_block_with_clearance, half_block_with_clearance)]

        def projected_triangle_contains(point, a, b, c):
            def signed_area(p, q, r):
                return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
            if abs(signed_area(a, b, c)) < 1e-8:
                return False
            signs = [signed_area(a, b, point), signed_area(b, c, point), signed_area(c, a, point)]
            return min(signs) >= -1e-8 or max(signs) <= 1e-8

        for part in (rim, well):
            rendered_triangles = []
            # Inspect render geometry, including asset-backed solid cubes, so the
            # test measures an open descent path rather than a particular model API.
            for node_path in part.model.find_all_matches('**/+GeomNode'):
                node = node_path.node()
                for geom_index in range(node.get_num_geoms()):
                    geom = node.get_geom(geom_index)
                    reader = GeomVertexReader(geom.get_vertex_data(), 'vertex')
                    vertices = []
                    while not reader.is_at_end():
                        vertices.append(view.root.get_relative_point(node_path, reader.get_data3()))
                    assert all(abs(vertex.x - 1) < 0.5 and abs(vertex.z) < 0.5 for vertex in vertices)
                    for primitive_index in range(geom.get_num_primitives()):
                        primitive = geom.get_primitive(primitive_index).decompose()
                        for triangle_index in range(primitive.get_num_primitives()):
                            start = primitive.get_primitive_start(triangle_index)
                            end = primitive.get_primitive_end(triangle_index)
                            rendered_triangles.append([vertices[primitive.get_vertex(i)] for i in range(start, end)])
            assert rendered_triangles, 'Missing goal geometry must not pass the aperture check'
            for triangle in rendered_triangles:
                points = [(vertex.x - 1, vertex.z) for vertex in triangle]
                assert not any(projected_triangle_contains(point, *points) for point in aperture_points), (
                    'A goal triangle covers the descent opening'
                )
    finally:
        view.clear()
        destroy(view.root)
