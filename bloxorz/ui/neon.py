"""Native chamfered plates and reusable glow geometry for the tactical HUD."""

from ursina import Entity, Mesh, color

from bloxorz.ui.theme import NeonHUD


def _corners(width: float, height: float, cut: float) -> list:
    x, y = width / 2, height / 2
    return [(-x + cut, -y), (x - cut, -y), (x, -y + cut), (x, y - cut),
            (x - cut, y), (-x + cut, y), (-x, y - cut), (-x, -y + cut)]


def chamfered_mesh(width: float, height: float, cut: float = .01) -> Mesh:
    """Return a normalized quad whose corner cuts retain equal physical lengths."""
    points = _corners(width, height, min(cut, height / 3, width / 3))
    vertices = [(0, 0, 0)] + [(x / width, y / height, 0) for x, y in points]
    triangles = [(0, index + 1, (index + 1) % 8 + 1) for index in range(8)]
    return Mesh(vertices=vertices, triangles=triangles, static=True)


def _ring_mesh(width: float, height: float, border: float, cut: float) -> Mesh:
    outside = _corners(width, height, cut)
    inside = _corners(width - 2 * border, height - 2 * border, max(.001, cut - border))
    vertices = [(x / width, y / height, 0) for x, y in outside + inside]
    triangles = []
    for index in range(8):
        following = (index + 1) % 8
        triangles.extend([(index, following, index + 8), (following, following + 8, index + 8)])
    return Mesh(vertices=vertices, triangles=triangles, static=True)


class NeonPanel(Entity):
    """Create the plate once; hover and busy effects only adjust existing colors."""

    def __init__(self, parent: Entity, width: float, height: float, accent: str, **kwargs) -> None:
        super().__init__(parent=parent, **kwargs)
        self.surface = Entity(parent=self, model=chamfered_mesh(width, height), scale=(width, height),
                              color=color.hex(NeonHUD.SURFACE), alpha=.97, double_sided=True, z=.025)
        self.glow = Entity(parent=self, model=_ring_mesh(width + .012, height + .012, .006, .015),
                           scale=(width + .012, height + .012), color=color.hex(accent),
                           alpha=.10, double_sided=True, z=.03)
        self.outline = Entity(parent=self, model=_ring_mesh(width, height, .0014, .01),
                              scale=(width, height), color=color.hex(accent),
                              alpha=.65, double_sided=True, z=-.025)
        self.rail = Entity(parent=self, model="quad", scale=(.0025, height * .48),
                           position=(-width / 2 + .006, 0, -.026), color=color.hex(accent))

    def set_intensity(self, intensity: float) -> None:
        self.glow.alpha = .025 + .15 * intensity
        self.outline.alpha = .15 + .8 * intensity
        self.rail.alpha = .15 + .85 * intensity
