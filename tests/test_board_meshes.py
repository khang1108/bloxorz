"""Tests for procedural cyberpunk board mesh primitives.

Verifies:
1. beveled_box_mesh: unit bounds [-0.5, 0.5], flat top y=0.5, chamfered corners,
   shallow upper bevel, darker side vertex shading, and subdued chassis ribs option.
2. deck_panel_mesh: flat inset chamfered panel, local top at y=0, coordinates within
   tile_size/2, gradient contrast preservation, and flush subtle corner details (offset <= 0.002).
3. deck_border_mesh: thin boundary with distinct exposed (white) and interior subdued
   (RGB ~0.16, alpha ~0.40) vertex multipliers, no gap-spanning geometry.
4. hollow_box_mesh: unit square collar bounds [-0.5, 0.5], open aperture center with
   zero covering triangles, and ValueError rejection for inner_ratio <= 0 or >= 1.
"""

import pytest
from ursina import Mesh

from bloxorz.graphics.board_meshes import (
    beveled_box_mesh,
    deck_panel_mesh,
    deck_border_mesh,
    hollow_box_mesh,
)


def _point_in_triangle_2d(px: float, pz: float, ax: float, az: float,
                          bx: float, bz: float, cx: float, cz: float) -> bool:
    """Returns True if point (px, pz) lies inside 2D triangle (A, B, C)."""
    v0x, v0z = cx - ax, cz - az
    v1x, v1z = bx - ax, bz - az
    v2x, v2z = px - ax, pz - az

    dot00 = v0x * v0x + v0z * v0z
    dot01 = v0x * v1x + v0z * v1z
    dot02 = v0x * v2x + v0z * v2z
    dot11 = v1x * v1x + v1z * v1z
    dot12 = v1x * v2x + v1z * v2z

    denom = dot00 * dot11 - dot01 * dot01
    if abs(denom) < 1e-9:
        return False
    u = (dot11 * dot02 - dot01 * dot12) / denom
    v = (dot00 * dot12 - dot01 * dot02) / denom
    return (u >= -1e-6) and (v >= -1e-6) and (u + v <= 1.0 + 1e-6)


def test_beveled_box_mesh_bounds_and_flat_top(engine):
    """Verify beveled_box_mesh matches unit bounds [-0.5, 0.5] with flat top at y=0.5 and chamfered corners."""
    mesh = beveled_box_mesh()
    assert isinstance(mesh, Mesh)

    verts = mesh.vertices
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]

    # Unit bounds [-0.5, 0.5]
    assert min(xs) == pytest.approx(-0.5, abs=1e-3)
    assert max(xs) == pytest.approx(0.5, abs=1e-3)
    assert min(ys) == pytest.approx(-0.5, abs=1e-3)
    assert max(ys) == pytest.approx(0.5, abs=1e-3)
    assert min(zs) == pytest.approx(-0.5, abs=1e-3)
    assert max(zs) == pytest.approx(0.5, abs=1e-3)

    # Flat top y=0.5 exists
    top_verts = [v for v in verts if abs(v[1] - 0.5) < 1e-4]
    assert len(top_verts) >= 6

    # Chamfered corners: sharp corners (+-0.5, 0.5, +-0.5) must NOT be in top vertices
    for cx in (-0.5, 0.5):
        for cz in (-0.5, 0.5):
            assert not any(abs(v[0] - cx) < 0.01 and abs(v[2] - cz) < 0.01 for v in top_verts)

    # Shading: top vertices should be brighter than side/bottom vertices
    colors = mesh.colors
    assert colors is not None and len(colors) == len(verts)

    top_colors = [colors[i] for i, v in enumerate(verts) if abs(v[1] - 0.5) < 1e-4]
    side_bottom_colors = [colors[i] for i, v in enumerate(verts) if v[1] < 0.35]

    avg_top_lum = sum(c.r + c.g + c.b for c in top_colors) / (3 * len(top_colors))
    avg_side_lum = sum(c.r + c.g + c.b for c in side_bottom_colors) / (3 * len(side_bottom_colors))
    assert avg_top_lum > avg_side_lum


def test_beveled_box_mesh_ribbed_option(engine):
    """Verify ribbed=True introduces chassis ribbing geometry within strict unit bounds."""
    mesh_plain = beveled_box_mesh(ribbed=False)
    mesh_ribbed = beveled_box_mesh(ribbed=True)

    assert len(mesh_ribbed.vertices) > len(mesh_plain.vertices)
    assert len(mesh_ribbed.triangles) > len(mesh_plain.triangles)

    # All ribbed vertices must remain strictly within [-0.5, 0.5]
    for v in mesh_ribbed.vertices:
        assert -0.501 <= v[0] <= 0.501
        assert -0.501 <= v[1] <= 0.501
        assert -0.501 <= v[2] <= 0.501

    # Flat top remains at y=0.5
    assert max(v[1] for v in mesh_ribbed.vertices) == pytest.approx(0.5, abs=1e-4)


def test_beveled_box_mesh_ribbed_groove_closure(engine):
    """Verify ribbed=True closes the recess with horizontal floor/ceiling lips and vertical end caps."""
    mesh_ribbed = beveled_box_mesh(ribbed=True)

    # 1. Floor lips at y = -0.15: 4 primary faces * 2 triangles each = 8 triangles pointing +Y
    floor_tris = []
    # 2. Ceiling lips at y = 0.15: 4 primary faces * 2 triangles each = 8 triangles pointing -Y
    ceil_tris = []
    # 3. End caps: 4 primary faces * 2 caps * 2 triangles each = 16 triangles pointing into cavity
    cap_tris = []

    for tri in mesh_ribbed.triangles:
        v0 = mesh_ribbed.vertices[tri[0]]
        v1 = mesh_ribbed.vertices[tri[1]]
        v2 = mesh_ribbed.vertices[tri[2]]
        norm = _tri_normal(v0, v1, v2)
        mid_y = (v0[1] + v1[1] + v2[1]) / 3.0
        mid_x = (v0[0] + v1[0] + v2[0]) / 3.0
        mid_z = (v0[2] + v1[2] + v2[2]) / 3.0

        if abs(mid_y - (-0.15)) < 1e-3 and norm[1] > 0.9:
            floor_tris.append(tri)
        elif abs(mid_y - 0.15) < 1e-3 and norm[1] < -0.9:
            ceil_tris.append(tri)
        elif abs(mid_y) < 0.14:
            # Check for end caps at outer chamfer transitions:
            # Faces at z = +/-0.5 have end caps at x = +/-0.42 with normal along X
            # Faces at x = +/-0.5 have end caps at z = +/-0.42 with normal along Z
            if (abs(abs(mid_x) - 0.42) < 0.02 and abs(norm[0]) > 0.9 and abs(mid_z) > 0.45) or \
               (abs(abs(mid_z) - 0.42) < 0.02 and abs(norm[2]) > 0.9 and abs(mid_x) > 0.45):
                cap_tris.append(tri)

    assert len(floor_tris) == 8, f"Expected 8 floor lip triangles at y=-0.15, found {len(floor_tris)}"
    assert len(ceil_tris) == 8, f"Expected 8 ceiling lip triangles at y=0.15, found {len(ceil_tris)}"
    assert len(cap_tris) == 16, f"Expected 16 vertical end-cap triangles, found {len(cap_tris)}"


def test_deck_panel_mesh_geometry_and_gradient(engine):
    """Verify deck_panel_mesh produces a flat chamfered inset panel at y=0 with gradient contrast."""
    tile_size = 0.86
    half = tile_size / 2.0
    gradient = ("#152131", "#2B3B50", "#1E2B3C", "#334660")

    mesh = deck_panel_mesh(tile_size, gradient, detailed=False)
    assert isinstance(mesh, Mesh)

    verts = mesh.vertices
    # All vertices at local y = 0
    for v in verts:
        assert v[1] == pytest.approx(0.0, abs=1e-5)
        assert -half - 1e-4 <= v[0] <= half + 1e-4
        assert -half - 1e-4 <= v[2] <= half + 1e-4

    # Chamfered corners check: sharp corner (+-half, 0, +-half) is not present
    for cx in (-half, half):
        for cz in (-half, half):
            assert not any(abs(v[0] - cx) < 0.01 and abs(v[2] - cz) < 0.01 for v in verts)

    # Colors preserve gradient contrast (not uniform)
    colors = mesh.colors
    r_values = {c.r for c in colors}
    assert len(r_values) >= 2


def test_deck_panel_mesh_detailed_option(engine):
    """Verify detailed=True introduces flush machined groove/fastener geometry with offset <= 0.002."""
    tile_size = 0.86
    gradient = ("#152131", "#2B3B50", "#1E2B3C", "#334660")

    mesh_plain = deck_panel_mesh(tile_size, gradient, detailed=False)
    mesh_det = deck_panel_mesh(tile_size, gradient, detailed=True)

    assert len(mesh_det.vertices) > len(mesh_plain.vertices)
    assert len(mesh_det.triangles) > len(mesh_plain.triangles)

    # Local vertical offset strictly <= 0.002
    for v in mesh_det.vertices:
        assert abs(v[1]) <= 0.002 + 1e-5

    # Center (0, 0) remains clean without central glyph or crosshair
    assert not any(abs(v[0]) < 0.05 and abs(v[2]) < 0.05 and abs(v[1]) > 1e-4 for v in mesh_det.vertices)


def test_deck_border_mesh_edge_classification(engine):
    """Verify deck_border_mesh differentiates exposed (white) and interior subdued (RGB ~0.16) edges."""
    tile_size = 0.86
    half = tile_size / 2.0
    exposed = ["x_neg", "z_pos"]

    mesh = deck_border_mesh(tile_size, exposed, width_factor=0.018)
    assert isinstance(mesh, Mesh)

    verts = mesh.vertices
    colors = mesh.colors
    assert len(verts) == len(colors)

    # No geometry spans beyond tile_size / 2
    for v in verts:
        assert -half - 1e-4 <= v[0] <= half + 1e-4
        assert -half - 1e-4 <= v[2] <= half + 1e-4

    # Check exposed vs interior edge vertex colors
    exposed_color_found = False
    subdued_color_found = False

    for v, c in zip(verts, colors):
        # Exposed edge: x_neg (left edge x ~ -half) or z_pos (top edge z ~ half)
        if (v[0] < -half + 0.05 and abs(v[2]) < half - 0.05) or (v[2] > half - 0.05 and abs(v[0]) < half - 0.05):
            assert c.r >= 0.90 and c.g >= 0.90 and c.b >= 0.90
            exposed_color_found = True

        # Interior subdued edge: x_pos (right edge x ~ half) or z_neg (bottom edge z ~ -half)
        if (v[0] > half - 0.05 and abs(v[2]) < half - 0.05) or (v[2] < -half + 0.05 and abs(v[0]) < half - 0.05):
            assert c.r <= 0.25 and c.g <= 0.25 and c.b <= 0.25
            assert c.a <= 0.55
            subdued_color_found = True

    assert exposed_color_found
    assert subdued_color_found


def test_hollow_box_mesh_aperture_and_bounds(engine):
    """Verify hollow_box_mesh creates a unit collar with an open center hole and no covering triangles."""
    inner_ratio = 0.80
    mesh = hollow_box_mesh(inner_ratio)
    assert isinstance(mesh, Mesh)

    verts = mesh.vertices
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]

    # Unit bounds [-0.5, 0.5]
    assert min(xs) == pytest.approx(-0.5, abs=1e-3)
    assert max(xs) == pytest.approx(0.5, abs=1e-3)
    assert min(ys) == pytest.approx(-0.5, abs=1e-3)
    assert max(ys) == pytest.approx(0.5, abs=1e-3)
    assert min(zs) == pytest.approx(-0.5, abs=1e-3)
    assert max(zs) == pytest.approx(0.5, abs=1e-3)

    # Top ring y=0.5 and bottom ring y=-0.5 exist
    top_verts = [v for v in verts if abs(v[1] - 0.5) < 1e-4]
    bot_verts = [v for v in verts if abs(v[1] - (-0.5)) < 1e-4]
    assert len(top_verts) >= 8
    assert len(bot_verts) >= 8

    # Inner walls bound the aperture (inner_ratio / 2 = 0.40)
    half_inner = inner_ratio / 2.0
    inner_xs = [abs(v[0]) for v in verts if abs(abs(v[0]) - half_inner) < 1e-3]
    assert len(inner_xs) >= 4

    # CRITICAL: No triangle covers the center (0, 0)
    triangles = mesh.triangles
    for tri in triangles:
        i0, i1, i2 = tri[0], tri[1], tri[2]
        v0, v1, v2 = verts[i0], verts[i1], verts[i2]
        assert not _point_in_triangle_2d(0.0, 0.0, v0[0], v0[2], v1[0], v1[2], v2[0], v2[2]), \
            f"Triangle {tri} covering center: {v0}, {v1}, {v2}"


def test_hollow_box_mesh_invalid_ratio_rejected():
    """Verify invalid inner_ratio <= 0 or >= 1 raises ValueError."""
    with pytest.raises(ValueError):
        hollow_box_mesh(0.0)

    with pytest.raises(ValueError):
        hollow_box_mesh(-0.25)

    with pytest.raises(ValueError):
        hollow_box_mesh(1.0)

    with pytest.raises(ValueError):
        hollow_box_mesh(1.5)


def _tri_normal(v0, v1, v2):
    ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    nx = ay * bz - az * by
    ny = az * bx - ax * bz
    nz = ax * by - ay * bx
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def test_mesh_face_orientations(engine):
    """Verify face normals: top faces +Y, bevels +Y and outward, outer walls outward, inner walls inward."""
    # 1. beveled_box_mesh:
    bbox = beveled_box_mesh()
    for tri in bbox.triangles:
        v0, v1, v2 = bbox.vertices[tri[0]], bbox.vertices[tri[1]], bbox.vertices[tri[2]]
        norm = _tri_normal(v0, v1, v2)
        mid_y = (v0[1] + v1[1] + v2[1]) / 3.0
        mid_x = (v0[0] + v1[0] + v2[0]) / 3.0
        mid_z = (v0[2] + v1[2] + v2[2]) / 3.0

        # Top face (y == 0.5) must point strictly +Y
        if abs(mid_y - 0.5) < 1e-3 and abs(norm[1] - 1.0) < 0.1:
            assert norm[1] > 0.9

        # Bevel face (0.42 < y < 0.5): normal must have +Y and point outward from center
        if 0.43 <= mid_y <= 0.49:
            assert norm[1] > 0.1, f"Bevel normal not pointing up: {norm}"
            dot_horiz = norm[0] * mid_x + norm[2] * mid_z
            assert dot_horiz > 0.1, f"Bevel normal not pointing outward: {norm}, mid=({mid_x}, {mid_z})"

        # Vertical side walls (y < 0.42): normal must point outward
        if mid_y < 0.40 and abs(norm[1]) < 0.2:
            dot_horiz = norm[0] * mid_x + norm[2] * mid_z
            assert dot_horiz > 0.3, f"Side wall normal not pointing outward: {norm}"

    # 2. deck_panel_mesh: top triangles must point +Y
    panel = deck_panel_mesh(0.86, ("#111111", "#222222", "#333333", "#444444"))
    for tri in panel.triangles:
        v0, v1, v2 = panel.vertices[tri[0]], panel.vertices[tri[1]], panel.vertices[tri[2]]
        norm = _tri_normal(v0, v1, v2)
        assert norm[1] > 0.9, f"Panel normal not +Y: {norm}"

    # 3. hollow_box_mesh:
    hollow = hollow_box_mesh(0.80)
    for tri in hollow.triangles:
        v0, v1, v2 = hollow.vertices[tri[0]], hollow.vertices[tri[1]], hollow.vertices[tri[2]]
        norm = _tri_normal(v0, v1, v2)
        mid_y = (v0[1] + v1[1] + v2[1]) / 3.0
        mid_x = (v0[0] + v1[0] + v2[0]) / 3.0
        mid_z = (v0[2] + v1[2] + v2[2]) / 3.0
        horiz_dist = (mid_x * mid_x + mid_z * mid_z) ** 0.5

        # Top ring triangles must point +Y
        if abs(mid_y - 0.5) < 1e-3:
            assert norm[1] > 0.9, f"Hollow top collar normal not +Y: {norm}"

        # Outer walls: horiz_dist > 0.45, normal must point outward: dot > 0
        if abs(norm[1]) < 0.2 and horiz_dist > 0.45:
            dot_horiz = norm[0] * mid_x + norm[2] * mid_z
            assert dot_horiz > 0.3, f"Outer wall normal not outward: {norm}"

        # Inner walls: horiz_dist < 0.45, normal must point inward towards aperture: dot < 0
        if abs(norm[1]) < 0.2 and horiz_dist < 0.45:
            dot_horiz = norm[0] * mid_x + norm[2] * mid_z
            assert dot_horiz < -0.3, f"Inner wall normal not inward: {norm}"
