"""Prebuilt continuous block silhouettes for the architectural minimap."""

from ursina import Entity, Mesh, color

from bloxorz.ui.neon import chamfered_mesh
from bloxorz.ui.theme import NeonHUD


def corner_brackets(width: float, height: float, arm_length: float | None = None) -> Mesh:
    """Build four open corner marks without drawing a distracting full grid."""
    vertices = []
    length = min(width, height) * .16 if arm_length is None else min(arm_length, min(width, height) / 2)
    for sx, sy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        x, y = sx * width / 2, sy * height / 2
        vertices.extend([(x - sx * length, y, 0), (x, y, 0),
                         (x, y, 0), (x, y - sy * length, 0)])
    segments = [(index, index + 1) for index in range(0, len(vertices), 2)]
    return Mesh(vertices=vertices, triangles=segments, mode="line", thickness=1.5, static=True)


class BlockMarker(Entity):
    """Morph between cached footprints; only a genuinely split block gets two actors."""

    PASSIVE = "#B48AFF"

    def __init__(self, parent: Entity) -> None:
        super().__init__(parent=parent, enabled=False, z=-.04)
        self._shapes = {}
        self._signature = None
        self._lock_time = .12
        for footprint in ((1, 1), (2, 1), (1, 2)):
            w, h = footprint
            group = Entity(parent=self, enabled=False)
            rim = Entity(parent=group, model=chamfered_mesh(w - .12, h - .12, .12),
                         scale=(w - .12, h - .12), color=color.hex(NeonHUD.CYAN),
                         double_sided=True, z=.005)
            body = Entity(parent=group, model=chamfered_mesh(w - .26, h - .26, .10),
                          scale=(w - .26, h - .26), color=color.hex(NeonHUD.TEXT),
                          double_sided=True, z=-.005)
            reticle = Entity(parent=group, model=corner_brackets(w + .08, h + .08),
                             color=color.hex(NeonHUD.CYAN), z=-.015)
            self._shapes[footprint] = (group, rim, body, reticle)
        _, _, self.body, self.reticle = self._shapes[(1, 1)]

    def configure(self, position: tuple, cell_size: float, footprint: tuple, active: bool) -> None:
        signature = (position, footprint, active)
        if signature != self._signature:
            self._lock_time = 0.
            self._signature = signature
        self.position = (*position, -.04)
        self.scale = (cell_size, cell_size, 1)
        self.color = color.hex(NeonHUD.TEXT if active else self.PASSIVE)
        for size, (group, rim, body, reticle) in self._shapes.items():
            group.enabled = size == footprint
            if group.enabled:
                self.body, self.reticle = body, reticle
                rim.color = color.hex(NeonHUD.CYAN if active else self.PASSIVE)
                body.color = color.hex(NeonHUD.TEXT if active else "#101127")
                reticle.enabled = active
        self.tick(0)

    def tick(self, dt: float) -> None:
        self._lock_time = min(.12, self._lock_time + dt)
        lock = 1 + .15 * (1 - self._lock_time / .12) ** 3
        self.reticle.scale = (lock, lock, 1)
