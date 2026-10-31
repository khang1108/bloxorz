"""Procedural cyberpunk board mesh primitives.

Provides code-native procedural geometry for the Bloxorz industrial titanium deck:
1. beveled_box_mesh: Unit box with chamfered vertical edges and upper bevel.
2. deck_panel_mesh: Flat inset chamfered panel with gradient contrast.
3. deck_border_mesh: Thin boundary distinguishing exposed and subdued interior edges.
4. hollow_box_mesh: Unit square collar with open vertical aperture.
"""

from typing import Iterable, List, Tuple
from ursina import Mesh, color


def _add_quad(
    vertices: List[Tuple[float, float, float]],
    triangles: List[Tuple[int, int, int]],
    colors: List[color.Color],
    v0: Tuple[float, float, float],
    v1: Tuple[float, float, float],
    v2: Tuple[float, float, float],
    v3: Tuple[float, float, float],
    c0: color.Color,
    c1: color.Color = None,
    c2: color.Color = None,
    c3: color.Color = None,
) -> None:
    """Appends two counter-clockwise triangles forming a planar or contoured quad."""
    base = len(vertices)
    vertices.extend((v0, v1, v2, v3))
    c1 = c0 if c1 is None else c1
    c2 = c0 if c2 is None else c2
    c3 = c0 if c3 is None else c3
    colors.extend((c0, c1, c2, c3))
    triangles.extend(((base, base + 1, base + 2), (base, base + 2, base + 3)))


def beveled_box_mesh(*, ribbed: bool = False) -> Mesh:
    """Constructs a unit box mesh bounds [-0.5, 0.5] with flat top y=0.5 and upper/corner chamfers."""
    c, b_inset, y_top, y_bevel, y_bot = 0.08, 0.035, 0.5, 0.42, -0.5
    outer_2d = [
        (-0.5 + c, -0.5), (0.5 - c, -0.5), (0.5, -0.5 + c), (0.5, 0.5 - c),
        (0.5 - c, 0.5), (-0.5 + c, 0.5), (-0.5, 0.5 - c), (-0.5, -0.5 + c),
    ]
    top_2d = [(x * (1.0 - 2 * b_inset), z * (1.0 - 2 * b_inset)) for x, z in outer_2d]

    vertices: List[Tuple[float, float, float]] = []
    triangles: List[Tuple[int, int, int]] = []
    colors: List[color.Color] = []

    c_top = color.rgba(1.0, 1.0, 1.0, 1.0)
    c_bevel = color.rgba(0.78, 0.78, 0.78, 1.0)
    c_side = color.rgba(0.55, 0.55, 0.55, 1.0)
    c_bot = color.rgba(0.35, 0.35, 0.35, 1.0)

    # 1. Flat top face at y=0.5 (triangulated fan from center, normal +Y)
    center_idx = len(vertices)
    vertices.append((0.0, y_top, 0.0))
    colors.append(c_top)
    top_base = len(vertices)
    for x, z in top_2d:
        vertices.append((x, y_top, z))
        colors.append(c_top)
    for i in range(8):
        triangles.append((center_idx, top_base + (i + 1) % 8, top_base + i))

    # 2. Shallow upper bevel ring (normal +Y and outward)
    for i in range(8):
        ni = (i + 1) % 8
        _add_quad(
            vertices, triangles, colors,
            (outer_2d[ni][0], y_bevel, outer_2d[ni][1]), (outer_2d[i][0], y_bevel, outer_2d[i][1]),
            (top_2d[i][0], y_top, top_2d[i][1]), (top_2d[ni][0], y_top, top_2d[ni][1]),
            c_bevel, c_bevel, c_top, c_top,
        )

    # 3. Vertical side walls (normal outward)
    if not ribbed:
        for i in range(8):
            ni = (i + 1) % 8
            _add_quad(
                vertices, triangles, colors,
                (outer_2d[ni][0], y_bot, outer_2d[ni][1]), (outer_2d[i][0], y_bot, outer_2d[i][1]),
                (outer_2d[i][0], y_bevel, outer_2d[i][1]), (outer_2d[ni][0], y_bevel, outer_2d[ni][1]),
                c_bot, c_bot, c_side, c_side,
            )
    else:
        c_rib = color.rgba(0.38, 0.38, 0.38, 1.0)
        y_rlo, y_rhi, inset = -0.15, 0.15, 0.02
        for i in range(8):
            ni = (i + 1) % 8
            if i % 2 != 0:
                _add_quad(
                    vertices, triangles, colors,
                    (outer_2d[ni][0], y_bot, outer_2d[ni][1]), (outer_2d[i][0], y_bot, outer_2d[i][1]),
                    (outer_2d[i][0], y_bevel, outer_2d[i][1]), (outer_2d[ni][0], y_bevel, outer_2d[ni][1]),
                    c_bot, c_bot, c_side, c_side,
                )
            else:
                p_a, p_b = outer_2d[i], outer_2d[ni]
                nx = 0.0 if abs(p_a[0] - p_b[0]) > 0.01 else (1.0 if p_a[0] > 0 else -1.0)
                nz = 0.0 if abs(p_a[1] - p_b[1]) > 0.01 else (1.0 if p_a[1] > 0 else -1.0)
                r_a = (p_a[0] - nx * inset, p_a[1] - nz * inset)
                r_b = (p_b[0] - nx * inset, p_b[1] - nz * inset)
                _add_quad(
                    vertices, triangles, colors,
                    (p_b[0], y_bot, p_b[1]), (p_a[0], y_bot, p_a[1]),
                    (p_a[0], y_rlo, p_a[1]), (p_b[0], y_rlo, p_b[1]),
                    c_bot, c_bot, c_side, c_side,
                )
                _add_quad(
                    vertices, triangles, colors,
                    (r_b[0], y_rlo, r_b[1]), (r_a[0], y_rlo, r_a[1]),
                    (r_a[0], y_rhi, r_a[1]), (r_b[0], y_rhi, r_b[1]),
                    c_rib,
                )
                _add_quad(
                    vertices, triangles, colors,
                    (p_b[0], y_rhi, p_b[1]), (p_a[0], y_rhi, p_a[1]),
                    (p_a[0], y_bevel, p_a[1]), (p_b[0], y_bevel, p_b[1]),
                    c_side,
                )
                # Horizontal floor and ceiling lips closing the recess groove
                _add_quad(
                    vertices, triangles, colors,
                    (p_a[0], y_rlo, p_a[1]), (r_a[0], y_rlo, r_a[1]),
                    (r_b[0], y_rlo, r_b[1]), (p_b[0], y_rlo, p_b[1]),
                    c_rib,
                )
                _add_quad(
                    vertices, triangles, colors,
                    (p_b[0], y_rhi, p_b[1]), (r_b[0], y_rhi, r_b[1]),
                    (r_a[0], y_rhi, r_a[1]), (p_a[0], y_rhi, p_a[1]),
                    c_rib,
                )
                # Vertical end caps at outer chamfer transitions closing groove endpoints
                _add_quad(
                    vertices, triangles, colors,
                    (p_a[0], y_rlo, p_a[1]), (p_a[0], y_rhi, p_a[1]),
                    (r_a[0], y_rhi, r_a[1]), (r_a[0], y_rlo, r_a[1]),
                    c_rib,
                )
                _add_quad(
                    vertices, triangles, colors,
                    (r_b[0], y_rlo, r_b[1]), (r_b[0], y_rhi, r_b[1]),
                    (p_b[0], y_rhi, p_b[1]), (p_b[0], y_rlo, p_b[1]),
                    c_rib,
                )

    # 4. Bottom face at y=-0.5 (triangulated fan, normal -Y)
    bot_center = len(vertices)
    vertices.append((0.0, y_bot, 0.0))
    colors.append(c_bot)
    bot_base = len(vertices)
    for x, z in outer_2d:
        vertices.append((x, y_bot, z))
        colors.append(c_bot)
    for i in range(8):
        triangles.append((bot_center, bot_base + i, bot_base + (i + 1) % 8))

    return Mesh(vertices=vertices, triangles=triangles, colors=colors, static=True)


def deck_panel_mesh(tile_size: float, gradient: Tuple[str, str, str, str], *, detailed: bool = False) -> Mesh:
    """Constructs a flat inset chamfered panel mesh at y=0 with bilinear gradient colors and normal +Y."""
    half, c = tile_size / 2.0, tile_size * 0.06
    c00, c10, c11, c01 = (color.hex(h) for h in gradient)

    def interp_color(x: float, z: float, mul: float = 1.0) -> color.Color:
        u = max(0.0, min(1.0, (x + half) / tile_size))
        v = max(0.0, min(1.0, (z + half) / tile_size))
        r = ((1 - u) * (1 - v) * c00.r + u * (1 - v) * c10.r + u * v * c11.r + (1 - u) * v * c01.r) * mul
        g = ((1 - u) * (1 - v) * c00.g + u * (1 - v) * c10.g + u * v * c11.g + (1 - u) * v * c01.g) * mul
        b = ((1 - u) * (1 - v) * c00.b + u * (1 - v) * c10.b + u * v * c11.b + (1 - u) * v * c01.b) * mul
        a = (1 - u) * (1 - v) * c00.a + u * (1 - v) * c10.a + u * v * c11.a + (1 - u) * v * c01.a
        return color.rgba(min(1.0, r), min(1.0, g), min(1.0, b), a)

    corners = [
        (-half + c, -half), (half - c, -half), (half, -half + c), (half, half - c),
        (half - c, half), (-half + c, half), (-half, half - c), (-half, -half + c),
    ]

    vertices: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.0)]
    triangles: List[Tuple[int, int, int]] = []
    colors: List[color.Color] = [interp_color(0.0, 0.0)]

    base_idx = len(vertices)
    for x, z in corners:
        vertices.append((x, 0.0, z))
        colors.append(interp_color(x, z))
    for i in range(8):
        triangles.append((0, base_idx + (i + 1) % 8, base_idx + i))

    if detailed:
        f_sz, f_dist, f_y = tile_size * 0.024, half - c * 1.6, 0.0015
        for fx in (-f_dist, f_dist):
            for fz in (-f_dist, f_dist):
                f_col = interp_color(fx, fz, mul=1.18)
                _add_quad(
                    vertices, triangles, colors,
                    (fx - f_sz, f_y, fz - f_sz), (fx - f_sz, f_y, fz + f_sz),
                    (fx + f_sz, f_y, fz + f_sz), (fx + f_sz, f_y, fz - f_sz),
                    f_col,
                )

    return Mesh(vertices=vertices, triangles=triangles, colors=colors, static=True)


def deck_border_mesh(tile_size: float, exposed_edges: Iterable[str], *, width_factor: float = 0.018) -> Mesh:
    """Constructs a thin chamfer-aware boundary with white exposed and subdued interior edges and normal +Y."""
    half, bw, c = tile_size / 2.0, tile_size * width_factor, tile_size * 0.06
    exposed = set(exposed_edges)
    c_white = color.rgba(1.0, 1.0, 1.0, 1.0)
    c_subdued = color.rgba(0.16, 0.16, 0.16, 0.40)

    vertices: List[Tuple[float, float, float]] = []
    triangles: List[Tuple[int, int, int]] = []
    colors: List[color.Color] = []

    # 4 straight edges (wound to face +Y)
    straights = [
        ("z_neg", (-half + c, 0.0, -half), (half - c, 0.0, -half),
         (half - c, 0.0, -half + bw), (-half + c, 0.0, -half + bw)),
        ("x_pos", (half, 0.0, -half + c), (half, 0.0, half - c),
         (half - bw, 0.0, half - c), (half - bw, 0.0, -half + c)),
        ("z_pos", (half - c, 0.0, half), (-half + c, 0.0, half),
         (-half + c, 0.0, half - bw), (half - c, 0.0, half - bw)),
        ("x_neg", (-half, 0.0, half - c), (-half, 0.0, -half + c),
         (-half + bw, 0.0, -half + c), (-half + bw, 0.0, half - c)),
    ]
    for edge_name, v0, v1, v2, v3 in straights:
        col = c_white if edge_name in exposed else c_subdued
        _add_quad(vertices, triangles, colors, v0, v3, v2, v1, col)

    # 4 corner chamfers with edge-facing vertex attribution (wound to face +Y)
    corners = [
        ("x_neg", "z_neg", (-half, 0.0, -half + c), (-half + c, 0.0, -half),
         (-half + c, 0.0, -half + bw), (-half + bw, 0.0, -half + c)),
        ("z_neg", "x_pos", (half - c, 0.0, -half), (half, 0.0, -half + c),
         (half - bw, 0.0, -half + c), (half - c, 0.0, -half + bw)),
        ("x_pos", "z_pos", (half, 0.0, half - c), (half - c, 0.0, half),
         (half - c, 0.0, half - bw), (half - bw, 0.0, half - c)),
        ("z_pos", "x_neg", (-half + c, 0.0, half), (-half, 0.0, half - c),
         (-half + bw, 0.0, half - c), (-half + c, 0.0, half - bw)),
    ]
    for e1, e2, v0, v1, v2, v3 in corners:
        ce1 = c_white if e1 in exposed else c_subdued
        ce2 = c_white if e2 in exposed else c_subdued
        _add_quad(vertices, triangles, colors, v0, v3, v2, v1, ce1, ce1, ce2, ce2)

    return Mesh(vertices=vertices, triangles=triangles, colors=colors, static=True)


def hollow_box_mesh(inner_ratio: float) -> Mesh:
    """Constructs a unit square tube collar bounds [-0.5, 0.5] with hollow vertical aperture."""
    if inner_ratio <= 0.0 or inner_ratio >= 1.0:
        raise ValueError(f"inner_ratio must be strictly between 0.0 and 1.0 exclusive, got {inner_ratio}")

    ro, ri, y_top, y_bot = 0.5, inner_ratio / 2.0, 0.5, -0.5
    vertices: List[Tuple[float, float, float]] = []
    triangles: List[Tuple[int, int, int]] = []
    colors: List[color.Color] = []

    c_top = color.rgba(1.0, 1.0, 1.0, 1.0)
    c_bot = color.rgba(0.40, 0.40, 0.40, 1.0)
    c_outer = color.rgba(0.65, 0.65, 0.65, 1.0)
    c_inner = color.rgba(0.45, 0.45, 0.45, 1.0)

    # 1. Top ring at y=0.5 (normal +Y)
    top_sectors = [
        ((-ro, -ro), (ro, -ro), (ri, -ri), (-ri, -ri)),
        ((ro, -ro), (ro, ro), (ri, ri), (ri, -ri)),
        ((ro, ro), (-ro, ro), (-ri, ri), (ri, ri)),
        ((-ro, ro), (-ro, -ro), (-ri, -ri), (-ri, ri)),
    ]
    for (o0x, o0z), (o1x, o1z), (i1x, i1z), (i0x, i0z) in top_sectors:
        _add_quad(
            vertices, triangles, colors,
            (o0x, y_top, o0z), (i0x, y_top, i0z), (i1x, y_top, i1z), (o1x, y_top, o1z),
            c_top,
        )

    # 2. Bottom ring at y=-0.5 (normal -Y, facing downward)
    for (o0x, o0z), (o1x, o1z), (i1x, i1z), (i0x, i0z) in top_sectors:
        _add_quad(
            vertices, triangles, colors,
            (o1x, y_bot, o1z), (i1x, y_bot, i1z), (i0x, y_bot, i0z), (o0x, y_bot, o0z),
            c_bot,
        )

    # 3. Outer side walls (normal outward: dot(normal, center) > 0)
    outer_corners = [(-ro, -ro), (ro, -ro), (ro, ro), (-ro, ro)]
    for i in range(4):
        p0, p1 = outer_corners[i], outer_corners[(i + 1) % 4]
        _add_quad(
            vertices, triangles, colors,
            (p1[0], y_bot, p1[1]), (p0[0], y_bot, p0[1]), (p0[0], y_top, p0[1]), (p1[0], y_top, p1[1]),
            c_outer,
        )

    # 4. Inner aperture walls (normal inward towards central shaft: dot(normal, center) < 0)
    inner_corners = [(-ri, -ri), (ri, -ri), (ri, ri), (-ri, ri)]
    for i in range(4):
        p0, p1 = inner_corners[i], inner_corners[(i + 1) % 4]
        _add_quad(
            vertices, triangles, colors,
            (p0[0], y_bot, p0[1]), (p1[0], y_bot, p1[1]), (p1[0], y_top, p1[1]), (p0[0], y_top, p0[1]),
            c_inner,
        )

    return Mesh(vertices=vertices, triangles=triangles, colors=colors, static=True)
