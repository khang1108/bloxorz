"""One-click search controls styled as a neon command console."""

import math
from typing import Callable, Dict, Optional

from ursina import Button, Entity, Text, camera, color, time, window

from bloxorz.audio.sound_manager import play_sfx
from bloxorz.ui.constants import SolverWidgetConstants as Layout
from bloxorz.ui.neon import NeonPanel, chamfered_mesh
from bloxorz.ui.theme import NeonHUD


class SolverWidget:
    """Four independent solver keys with hover, selected, running and stop states."""

    ALGORITHMS = ("BFS", "DFS", "UCS", "A*")
    CAPTIONS = ("BREADTH", "DEPTH", "UNIFORM", "HEURISTIC")

    def __init__(
        self,
        parent: Optional[Entity] = None,
        on_select_algorithm: Optional[Callable[[str], None]] = None,
        on_run_solver: Optional[Callable[[], None]] = None,
        initial_algorithm: str = "BFS",
    ) -> None:
        self.on_select_algorithm = on_select_algorithm
        self.on_run_solver = on_run_solver
        self.current_algorithm = initial_algorithm.upper().strip()
        self.is_running = False
        self._hovered_algorithm = None
        self._elapsed = 0.
        self.root = Entity(parent=parent if parent is not None else camera.ui, name="solver_widget_root", z=-.1)
        self.root.update = self._update
        self._update_position()
        width, height = Layout.PANEL_SIZE
        self.frame = NeonPanel(parent=self.root, width=width, height=height, accent=NeonHUD.CYAN)
        Text(parent=self.root, text="SEARCH CONTROL", position=(-.15, .111), origin=(-.5, 0),
             scale=.70, color=color.hex(NeonHUD.TEXT), z=-.02)
        self.status_light = Entity(parent=self.root, model="circle", position=(.080, .111, -.02),
                                   scale=.006, color=color.hex(NeonHUD.CYAN))
        self.state_label = Text(parent=self.root, text="READY", position=(.153, .111), origin=(.5, 0),
                                scale=.54, color=color.hex(NeonHUD.CYAN), z=-.02)
        self.option_buttons: Dict[str, Button] = {}
        self.button_frames: Dict[str, NeonPanel] = {}
        button_width, button_height = Layout.BUTTON_SIZE
        for index, algorithm in enumerate(self.ALGORITHMS):
            x = -.082 if index % 2 == 0 else .082
            y = .045 if index < 2 else -.047
            accent = NeonHUD.ALGORITHMS[index]
            self.button_frames[algorithm] = NeonPanel(
                parent=self.root, width=button_width, height=button_height, accent=accent, x=x, y=y,
            )
            button = Button(
                parent=self.root, text=algorithm, position=(x, y, -.01), scale=Layout.BUTTON_SIZE,
                model=chamfered_mesh(button_width, button_height), double_sided=True,
                color=color.hex(NeonHUD.BUTTON), highlight_color=color.hex(NeonHUD.HOVER),
                pressed_color=color.hex(NeonHUD.PRESSED), text_color=color.hex(NeonHUD.TEXT),
                highlight_text_color=color.hex(accent), text_size=1.05, highlight_text_size=1.05,
                on_click=lambda name=algorithm: self._activate_algorithm(name),
            )
            button.text_entity.y = .12
            button.on_mouse_enter = lambda name=algorithm: self._set_hover(name, True)
            button.on_mouse_exit = lambda name=algorithm: self._set_hover(name, False)
            self.option_buttons[algorithm] = button
            Text(parent=self.root, text=f"0{index + 1}", position=(x - .055, y + .025),
                 origin=(-.5, 0), scale=.46, color=color.hex(accent), z=-.03)
            Text(parent=self.root, text=self.CAPTIONS[index], position=(x, y - .022),
                 origin=(0, 0), scale=.6, color=color.hex(NeonHUD.MUTED), z=-.03)
        self.status_text = Text(parent=self.root, position=(-.151, -.113), origin=(-.5, 0),
                                scale=.58, color=color.hex(NeonHUD.MUTED), z=-.02)
        self.shortcut_text = Text(parent=self.root, position=(.151, -.113), origin=(.5, 0),
                                   scale=.58, color=color.hex(NeonHUD.MUTED), z=-.02)
        self._refresh_buttons()

    def _update_position(self) -> None:
        self.root.position = (window.aspect_ratio / 2 - Layout.EDGE_MARGIN, Layout.PANEL_Y, -.1)

    def _update(self) -> None:
        self._update_position()
        self._elapsed += getattr(time, "dt", 0.)
        for algorithm, frame in self.button_frames.items():
            active = algorithm == self.current_algorithm
            if self.is_running:
                intensity = .7 + .18 * math.sin(self._elapsed * 2.5) if active else .05
            else:
                intensity = 1. if algorithm == self._hovered_algorithm else .6 if active else .25
            frame.set_intensity(intensity)

    def _set_hover(self, algorithm: str, hovering: bool) -> None:
        if self.is_running and algorithm != self.current_algorithm:
            return
        if hovering:
            self._hovered_algorithm = algorithm
        elif self._hovered_algorithm == algorithm:
            self._hovered_algorithm = None
        button = self.option_buttons[algorithm]
        button.model.setColorScale(button.highlight_color if hovering else button.color)
        button.text_entity.color = button.highlight_text_color if hovering else button.text_color
        self._update()

    def _activate_algorithm(self, algorithm: str) -> None:
        if not self.root.enabled or (self.is_running and algorithm != self.current_algorithm):
            return
        play_sfx("click")
        if not self.is_running:
            self.select_algorithm(algorithm)
            if self.on_select_algorithm:
                self.on_select_algorithm(algorithm)
        if self.on_run_solver:
            self.on_run_solver()

    def select_algorithm(self, algo: str) -> None:
        """Synchronize selection without dispatching the solver."""
        algorithm = algo.upper().strip()
        if algorithm not in self.option_buttons:
            return
        self.current_algorithm = algorithm
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        for index, (algorithm, button) in enumerate(self.option_buttons.items()):
            active = algorithm == self.current_algorithm
            disabled = self.is_running and not active
            accent = NeonHUD.ALGORITHMS[index]
            button.disabled = disabled
            button.text = f"STOP {algorithm}" if self.is_running and active else algorithm
            button.text_size = .8 if self.is_running and active else 1.05
            button.highlight_text_size = button.text_size
            button.color = color.hex(NeonHUD.PRESSED if active else NeonHUD.BUTTON)
            button.text_color = color.hex(NeonHUD.MUTED if disabled else accent if active else NeonHUD.TEXT)
        self.state_label.text = "RUNNING" if self.is_running else "READY"
        self.state_label.color = color.hex(NeonHUD.MAGENTA if self.is_running else NeonHUD.CYAN)
        self.status_light.color = self.state_label.color
        self.status_text.text = (
            f"{self.current_algorithm} ACTIVE" if self.is_running else "SELECT TO RUN"
        )
        self.shortcut_text.text = "[P] STOP" if self.is_running else "[P] RUN"
        self._update()

    def set_running_state(self, is_running: bool) -> None:
        """Keep the running method stoppable and prevent competing searches."""
        self.is_running = is_running
        self._hovered_algorithm = None
        self._refresh_buttons()

    def set_visible(self, visible: bool) -> None:
        self.root.enabled = visible
