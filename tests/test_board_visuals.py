import pytest
from ursina import Vec3, destroy, time

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
    assert safe_color.r < 0.1 and safe_color.b < 0.15
    assert fragile_color.r > 0.2 and fragile_color.g > 0.1
    assert soft_color.b > soft_color.r
    assert heavy_color.r > heavy_color.b
    assert teleport_color.r > teleport_color.g and teleport_color.b > teleport_color.g
    safe_border = next(
        entity for entity in view.root.children
        if entity.name == "tile_neon_border" and entity.x == 0
    )
    border_width = max(vertex[2] for vertex in safe_border.model.vertices[:4]) - min(
        vertex[2] for vertex in safe_border.model.vertices[:4]
    )
    assert border_width > 0.05
    assert safe_border.model.colors[0].a > 0.95
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


def test_block_mesh_is_solid_gold(game_app):
    view = BlockView()
    assert view.mesh.model.name == "cube"
    assert tuple(view.mesh.color)[:3] == pytest.approx((1.0, 210 / 255, 31 / 255))
    assert view.split_mesh_1.color.r > 0.9
    assert view.split_mesh_1.color.g > 0.8
    destroy(view)


def test_open_bridge_is_gold_with_red_outline(game_app):
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
    outline_color = outline.model.colors[0]
    assert bridge.color.r > 0.9 and bridge.color.g > 0.7
    assert outline_color.r > 0.9 and outline_color.g < 0.3
    destroy(view.root)


def test_landing_highlight_fades_back_to_the_board(game_app, monkeypatch):
    view = BoardView()
    board = Board(
        tiles={(0, 0): TileType.NORMAL},
        goal_pos=(0, 0),
        spawn_state=NormalBlockState(0, 0, BlockOrientation.STANDING),
    )
    view.build(board)
    view.animate_landing([(0, 0)])

    flash = next(
        entity for entity in view.root.children if entity.name == "tile_landing_flash"
    )
    initial_alpha = flash.color.a
    monkeypatch.setattr(time, "dt", 0.2, raising=False)
    flash.update()
    assert 0 < flash.color.a < initial_alpha
    monkeypatch.setattr(time, "dt", 0.2, raising=False)
    flash.update()
    assert flash not in view.root.children
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
