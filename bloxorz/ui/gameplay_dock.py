"""Reserve a right sidebar for controls without covering the 3D world."""

import math

from ursina import Entity, Mesh, camera, color, window

from bloxorz.ui.theme import NeonHUD


class GameplayDock(Entity):
    """Keep the world in its own viewport and the HUD in a full-screen UI region."""

    WIDTH = .43
    FRAMING_MARGIN = 1.12

    def __init__(self) -> None:
        super().__init__(parent=camera.ui, name="gameplay_dock", z=.2)
        self._base_hfov = camera.perspective_lens.get_hfov()
        self._last_aspect = None
        self._visible = True
        gradient = Mesh(
            vertices=[(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)],
            triangles=[(0, 1, 2), (0, 2, 3)],
            colors=[color.hex("#050912"), color.hex("#050912"),
                    color.hex("#101F31"), color.hex("#101F31")],
            static=True,
        )
        self.backplate = Entity(parent=self, model=gradient, scale=(self.WIDTH, 1), double_sided=True)
        self.seam = Entity(parent=self, model="quad", scale=(.001, 1),
                           color=color.hex(NeonHUD.CYAN), alpha=.35, z=-.01)
        self.update()

    def _apply_viewport(self) -> None:
        self.backplate.x = window.aspect_ratio / 2 - self.WIDTH / 2
        self.seam.x = window.aspect_ratio / 2 - self.WIDTH
        right = max(.2, 1 - self.WIDTH / window.aspect_ratio) if self._visible else 1
        camera.display_region.set_dimensions(0, right, 0, 1)
        aspect = window.aspect_ratio * right
        horizontal_tangent = math.tan(math.radians(self._base_hfov / 2))
        if self._visible:
            horizontal_tangent *= self.FRAMING_MARGIN
        # Expand the vertical field to preserve both original scene extents.
        vertical_tangent = max(horizontal_tangent / window.aspect_ratio, horizontal_tangent / aspect)
        camera.perspective_lens.set_fov(
            math.degrees(2 * math.atan(vertical_tangent * aspect)),
            math.degrees(2 * math.atan(vertical_tangent)),
        )
        self._last_aspect = window.aspect_ratio

    def update(self) -> None:
        right = max(.2, 1 - self.WIDTH / window.aspect_ratio) if self._visible else 1
        target_aspect = window.aspect_ratio * right
        if (self._last_aspect != window.aspect_ratio
                or abs(camera.perspective_lens.get_aspect_ratio() - target_aspect) > .0001):
            self._apply_viewport()

    def set_visible(self, visible: bool) -> None:
        """Menus regain the full world viewport while their UI remains full screen."""
        self._visible = visible
        self.enabled = visible
        self._apply_viewport()
