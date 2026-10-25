"""Compact, collapsible UI widget for selecting and executing search algorithms in Bloxorz."""

from typing import Callable, Optional, Dict
from ursina import Entity, Button, Text, color, camera

from bloxorz.ui.theme import Palette
from bloxorz.ui.constants import SolverWidgetConstants, UIAnchor, MenuConstants
from bloxorz.audio.sound_manager import play_sfx


class SolverWidget:
    """A compact, collapsible neo-minimalist solver widget for selecting and executing search algorithms."""

    ALGORITHMS = ("BFS", "DFS", "UCS", "A*")
    COMING_SOON = ("DFS", "UCS", "A*")

    def __init__(
        self,
        parent: Optional[Entity] = None,
        on_select_algorithm: Optional[Callable[[str], None]] = None,
        on_run_solver: Optional[Callable[[], None]] = None,
        initial_algorithm: str = "BFS",
    ):

        if parent is not None and not isinstance(parent, Entity):
            parent = None

        if parent is None:
            try:
                parent = camera.ui
            except Exception:
                parent = None

        self.parent = parent

        self.on_select_algorithm = on_select_algorithm
        self.on_run_solver = on_run_solver
        self.current_algorithm: str = initial_algorithm.upper().strip()
        self.is_expanded: bool = False
        self.is_running: bool = False

        # Root entity
        self.root = Entity(parent=parent, name="solver_widget_root", z=-0.1)

        # --- Collapsed State Entity (Pill Button) ---
        self.collapsed_btn = Button(
            parent=self.root,
            text=self._format_collapsed_label(),
            position=SolverWidgetConstants.COLLAPSED_POS,
            scale=SolverWidgetConstants.COLLAPSED_SCALE,
            color=color.hex(Palette.BACKGROUND_SECONDARY.hex_code),
            highlight_color=color.hex(Palette.TILE_INSET.hex_code),
            pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
            text_color=color.hex(Palette.TEXT_ACCENT.hex_code),
            highlight_text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            text_size=SolverWidgetConstants.COLLAPSED_TEXT_SCALE,
            highlight_text_size=SolverWidgetConstants.COLLAPSED_TEXT_SCALE,
            on_click=self.expand,
        )

        # --- Expanded State Entity (Card Panel) ---
        self.expanded_root = Entity(
            parent=self.root,
            position=SolverWidgetConstants.EXPANDED_POS,
            visible=False,
        )

        # Background Surface and Border
        self.panel_surface = Entity(
            parent=self.expanded_root,
            model="quad",
            scale=SolverWidgetConstants.EXPANDED_CONTAINER_SCALE,
            color=color.hex(Palette.BACKGROUND_SECONDARY.hex_code),
            z=MenuConstants.Z_CONTAINER_SURFACE,
        )
        self.panel_border = Entity(
            parent=self.expanded_root,
            model="quad",
            scale=SolverWidgetConstants.EXPANDED_BORDER_SCALE,
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=MenuConstants.Z_CONTAINER_BORDER,
        )

        # Header: Title & Collapse Button
        self.header_title = Text(
            parent=self.expanded_root,
            text="SOLVER ALGORITHM",
            position=(SolverWidgetConstants.HEADER_TITLE_X, SolverWidgetConstants.HEADER_Y),
            scale=SolverWidgetConstants.HEADER_TITLE_SCALE,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=UIAnchor.MIDDLE_LEFT,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )

        self.collapse_btn = Button(
            parent=self.expanded_root,
            text="^",
            position=(SolverWidgetConstants.COLLAPSE_BTN_X, SolverWidgetConstants.HEADER_Y),
            scale=SolverWidgetConstants.COLLAPSE_BTN_SCALE,
            color=color.hex(Palette.TILE_INSET.hex_code),
            highlight_color=color.hex(Palette.TILE_NORMAL.hex_code),
            pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
            text_color=color.hex(Palette.TEXT_MUTED.hex_code),
            highlight_text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            text_size=SolverWidgetConstants.COLLAPSE_BTN_TEXT_SCALE,
            highlight_text_size=SolverWidgetConstants.COLLAPSE_BTN_TEXT_SCALE,
            on_click=self.collapse,
        )

        # Top Divider
        Entity(
            parent=self.expanded_root,
            model="quad",
            scale=SolverWidgetConstants.DIVIDER_SCALE,
            position=(0.0, SolverWidgetConstants.DIVIDER_TOP_Y),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=MenuConstants.Z_DIVIDER,
        )

        # Radio Buttons for BFS, DFS, UCS, A*
        self.option_buttons: Dict[str, Button] = {}
        for idx, algo in enumerate(self.ALGORITHMS):
            y_pos = SolverWidgetConstants.OPTION_START_Y - (idx * SolverWidgetConstants.OPTION_SPACING_Y)
            is_sel = (algo == self.current_algorithm)
            btn = Button(
                parent=self.expanded_root,
                text=self._format_option_label(algo, is_selected=is_sel),
                position=(0.0, y_pos),
                scale=SolverWidgetConstants.OPTION_BTN_SCALE,
                color=self._get_option_bg_color(is_sel),
                highlight_color=color.hex(Palette.TILE_NORMAL.hex_code),
                pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
                text_color=self._get_option_text_color(is_sel),
                highlight_text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
                text_size=SolverWidgetConstants.OPTION_TEXT_SCALE,
                highlight_text_size=SolverWidgetConstants.OPTION_TEXT_SCALE,
                on_click=lambda a=algo: self.select_algorithm(a),
            )
            self.option_buttons[algo] = btn

        # Bottom Divider
        Entity(
            parent=self.expanded_root,
            model="quad",
            scale=SolverWidgetConstants.DIVIDER_SCALE,
            position=(0.0, SolverWidgetConstants.DIVIDER_BOTTOM_Y),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=MenuConstants.Z_DIVIDER,
        )

        # Run / Stop Action Button
        self.action_btn = Button(
            parent=self.expanded_root,
            text="RUN SOLVER · P",
            position=(0.0, SolverWidgetConstants.ACTION_BTN_Y),
            scale=SolverWidgetConstants.ACTION_BTN_SCALE,
            color=color.hex(Palette.TILE_INSET.hex_code),
            highlight_color=color.hex(Palette.TILE_NORMAL.hex_code),
            pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
            text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            highlight_text_color=color.hex(Palette.TEXT_ACCENT.hex_code),
            text_size=SolverWidgetConstants.ACTION_BTN_TEXT_SCALE,
            highlight_text_size=SolverWidgetConstants.ACTION_BTN_TEXT_SCALE,
            on_click=self._handle_action_click,
        )

    def _format_collapsed_label(self) -> str:
        suffix = " [SOON]" if self.current_algorithm in self.COMING_SOON else ""
        return f"SOLVER: {self.current_algorithm}{suffix}  v"

    def _format_option_label(self, algo: str, is_selected: bool) -> str:
        indicator = "(*)" if is_selected else "( )"
        suffix = "  [SOON]" if algo in self.COMING_SOON else ""
        return f"{indicator} {algo}{suffix}"

    def _get_option_bg_color(self, is_selected: bool):

        if is_selected:
            return color.rgba(0.22, 0.74, 0.97, 0.15)
        return color.clear

    def _get_option_text_color(self, is_selected: bool):
        if is_selected:
            return color.hex(Palette.TEXT_ACCENT.hex_code)
        return color.hex(Palette.TEXT_MUTED.hex_code)

    def expand(self):
        """Expands the algorithm selection panel."""
        play_sfx("click")
        self.is_expanded = True
        self.collapsed_btn.visible = False
        self.expanded_root.visible = True

    def collapse(self):
        """Collapses into a single minimal pill button."""
        play_sfx("click")
        self.is_expanded = False
        self.expanded_root.visible = False
        self.collapsed_btn.visible = True

    def toggle_collapse(self):
        """Toggles between collapsed and expanded state."""
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def select_algorithm(self, algo: str):
        """Selects an algorithm, updates visual radio buttons, and calls callback."""
        play_sfx("click")
        algo_clean = algo.upper().strip()
        if algo_clean not in self.option_buttons:
            return
        self.current_algorithm = algo_clean
        self.collapsed_btn.text = self._format_collapsed_label()

        for a, btn in self.option_buttons.items():
            selected = (a == algo_clean)
            btn.text = self._format_option_label(a, selected)
            btn.color = self._get_option_bg_color(selected)
            if hasattr(btn, "text_entity") and btn.text_entity:
                btn.text_entity.color = self._get_option_text_color(selected)

        if callable(self.on_select_algorithm):
            self.on_select_algorithm(self.current_algorithm)

    def set_running_state(self, is_running: bool):
        """Updates UI action button when solver starts or finishes."""
        self.is_running = is_running
        if is_running:
            self.action_btn.text = "STOP SOLVER"
            if hasattr(self.action_btn, "text_entity") and self.action_btn.text_entity:
                self.action_btn.text_entity.color = color.hex(Palette.SWITCH_HEAVY.hex_code)
        else:
            self.action_btn.text = "RUN SOLVER · P"
            if hasattr(self.action_btn, "text_entity") and self.action_btn.text_entity:
                self.action_btn.text_entity.color = color.hex(Palette.TEXT_PRIMARY.hex_code)

    def _handle_action_click(self):
        play_sfx("click")
        if callable(self.on_run_solver):
            self.on_run_solver()

    def set_visible(self, visible: bool):
        """Shows or hides the entire solver widget root."""
        self.root.visible = visible
