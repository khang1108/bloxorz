"""Menu systems, pause overlays, and minimalist stage selection matrix."""

from typing import Callable, Optional
from ursina import Entity, Button, Text, color, camera, destroy, application

from bloxorz.ui.theme import Palette


class MinimalistButton(Button):
    """Clean typography-only button with subtle hover micro-interactions."""

    def __init__(
        self,
        text: str,
        parent: Entity,
        y: float,
        on_click: Optional[Callable[[], None]] = None,
        scale: tuple = (0.45, 0.065),
    ):
        c_text = color.hex(Palette.TEXT_MUTED.hex_code)
        c_hover = color.hex(Palette.TEXT_PRIMARY.hex_code)

        kwargs = {}
        if callable(on_click):
            kwargs["on_click"] = on_click

        super().__init__(
            parent=parent,
            text=text.upper(),
            y=y,
            scale=scale,
            color=color.clear,
            highlight_color=color.clear,
            pressed_color=color.clear,
            **kwargs,
        )

        self.text_entity.color = c_text
        self.text_entity.scale *= 1.25
        self.default_x = self.x
        self.c_text = c_text
        self.c_hover = c_hover

    def on_mouse_enter(self):
        super().on_mouse_enter()
        self.text_entity.color = self.c_hover
        self.animate_x(self.default_x + 0.015, duration=0.1)

    def on_mouse_exit(self):
        super().on_mouse_exit()
        self.text_entity.color = self.c_text
        self.animate_x(self.default_x, duration=0.1)


class StageCardButton(Button):
    """Architectural stage card for the stage selection grid."""

    def __init__(
        self,
        stage_idx: int,
        is_current: bool,
        parent: Entity,
        x: float,
        y: float,
        on_click: Optional[Callable[[], None]] = None,
        scale: tuple = (0.142, 0.050),
    ):
        c_bg = (
            color.rgba(0.22, 0.74, 0.97, 0.20)
            if is_current
            else color.hex(Palette.BACKGROUND_SECONDARY.hex_code)
        )
        c_highlight = color.hex(Palette.TILE_NORMAL.hex_code)
        c_pressed = color.hex(Palette.TILE_PEDESTAL.hex_code)

        kwargs = {}
        if callable(on_click):
            kwargs["on_click"] = on_click

        super().__init__(
            parent=parent,
            text=f"STAGE {stage_idx:02d}",
            x=x,
            y=y,
            scale=scale,
            color=c_bg,
            highlight_color=c_highlight,
            pressed_color=c_pressed,
            **kwargs,
        )

        self.text_entity.scale *= 0.82
        self.text_entity.color = (
            color.hex(Palette.TEXT_ACCENT.hex_code)
            if is_current
            else color.hex(Palette.TEXT_MUTED.hex_code)
        )
        self.is_current = is_current

    def on_mouse_enter(self):
        super().on_mouse_enter()
        self.text_entity.color = color.hex(Palette.TEXT_PRIMARY.hex_code)

    def on_mouse_exit(self):
        super().on_mouse_exit()
        self.text_entity.color = (
            color.hex(Palette.TEXT_ACCENT.hex_code)
            if self.is_current
            else color.hex(Palette.TEXT_MUTED.hex_code)
        )


class MenuActionButton(Button):
    """Bottom action button for Pause and Stage Select screens."""

    def __init__(
        self,
        text: str,
        parent: Entity,
        x: float,
        y: float,
        on_click: Optional[Callable[[], None]] = None,
        scale: tuple = (0.24, 0.050),
    ):
        kwargs = {}
        if callable(on_click):
            kwargs["on_click"] = on_click

        super().__init__(
            parent=parent,
            text=text.upper(),
            x=x,
            y=y,
            scale=scale,
            color=color.hex(Palette.BACKGROUND_SECONDARY.hex_code),
            highlight_color=color.hex(Palette.TILE_NORMAL.hex_code),
            pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
            **kwargs,
        )
        self.text_entity.scale *= 0.85
        self.text_entity.color = color.hex(Palette.TEXT_PRIMARY.hex_code)


class MenuManager:
    """Controls transitions between Gameplay, Pause, Stage Select, and Victory."""

    def __init__(
        self,
        on_resume: Callable[[], None],
        on_restart: Callable[[], None],
        on_select_stage: Callable[[int], None],
        on_next_stage: Callable[[], None],
        on_toggle_audio: Callable[[], bool],
        get_audio_status: Callable[[], bool],
        stages_count: int = 33,
    ):
        self.on_resume_cb = on_resume
        self.on_restart_cb = on_restart
        self.on_select_stage_cb = on_select_stage
        self.on_next_stage_cb = on_next_stage
        self.on_toggle_audio_cb = on_toggle_audio
        self.get_audio_status_cb = get_audio_status
        self.stages_count = stages_count

        self.pause_root: Optional[Entity] = None
        self.victory_root: Optional[Entity] = None
        self.stage_select_root: Optional[Entity] = None
        self._audio_btn: Optional[MenuActionButton] = None

    def is_any_menu_open(self) -> bool:
        """Returns True if any modal overlay is currently visible."""
        return bool(self.pause_root or self.stage_select_root or self.victory_root)

    def close_all(self):
        """Removes all active modal overlays."""
        if self.pause_root:
            destroy(self.pause_root)
            self.pause_root = None
        if self.victory_root:
            destroy(self.victory_root)
            self.victory_root = None
        if self.stage_select_root:
            destroy(self.stage_select_root)
            self.stage_select_root = None
        self._audio_btn = None

    def show_pause_menu(self, current_stage: int = 1):
        """Displays the unified Stage Select & Pause overlay."""
        self.show_stage_select_menu(current_stage=current_stage)

    def show_stage_select_menu(self, current_stage: int = 1):
        """Displays minimalist 7-column grid of all available stages."""
        self.close_all()

        root = Entity(parent=camera.ui, name="stage_select_menu")
        # Translucent dark backdrop
        Entity(
            parent=root,
            model="quad",
            scale=(2.5, 2.0),
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=1,
        )

        # Header Title & Subtitle
        Text(
            parent=root,
            text="SELECT STAGE",
            position=(0.0, 0.38),
            scale=2.4,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )
        Text(
            parent=root,
            text=f"ACTIVE: STAGE {current_stage:02d}  ·  {self.stages_count} ARCHITECTURAL PUZZLES",
            position=(0.0, 0.30),
            scale=1.1,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        # 7-column grid layout
        dx = 0.155
        dy = 0.064
        y_start = 0.18

        for idx in range(1, self.stages_count + 1):
            row = (idx - 1) // 7
            col = (idx - 1) % 7
            items_in_row = 7 if row < 4 else (self.stages_count - 28)
            if row < 4:
                x_pos = (col - 3.0) * dx
            else:
                x_pos = (col - (items_in_row - 1) / 2.0) * dx
            y_pos = y_start - row * dy
            is_current = (idx == current_stage)

            stage_idx = idx

            def make_handler(s_idx=stage_idx):
                return lambda: self.on_select_stage_cb(s_idx)

            StageCardButton(
                stage_idx=stage_idx,
                is_current=is_current,
                parent=root,
                x=x_pos,
                y=y_pos,
                on_click=make_handler(),
            )

        # Bottom action bar: CONTINUE, RESTART, AUDIO, QUIT
        is_audio_on = self.get_audio_status_cb()
        actions = [
            ("CONTINUE", self.on_resume_cb),
            ("RESTART", self.on_restart_cb),
            (f"AUDIO: {'ON' if is_audio_on else 'OFF'}", self._toggle_audio),
            ("QUIT GAME", self._quit_game),
        ]
        dx_bar = 0.26
        for i, (label, cb) in enumerate(actions):
            x_pos = (i - 1.5) * dx_bar
            btn = MenuActionButton(
                text=label,
                parent=root,
                x=x_pos,
                y=-0.21,
                on_click=cb,
            )
            if i == 2:
                self._audio_btn = btn

        # Footer keyboard navigation hints
        Text(
            parent=root,
            text="[ ESC ] RESUME    ·    [ R ] RESTART    ·    [ U ] UNDO    ·    [ P ] SOLVER",
            position=(0.0, -0.29),
            scale=0.95,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        self.stage_select_root = root

    def _toggle_audio(self):
        new_state = self.on_toggle_audio_cb()
        if self._audio_btn:
            self._audio_btn.text = f"AUDIO: {'ON' if new_state else 'OFF'}"

    def _quit_game(self):
        application.quit()

    def show_victory_menu(self, stage_name: str, moves: int, current_stage: int = 1):
        """Displays the stage clear screen."""
        self.close_all()

        root = Entity(parent=camera.ui, name="victory_menu")
        Entity(
            parent=root,
            model="quad",
            scale=(2.5, 2.0),
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=1,
        )

        Text(
            parent=root,
            text="STAGE CLEARED",
            position=(0.0, 0.25),
            scale=2.8,
            color=color.hex(Palette.GOAL_RIM.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        Text(
            parent=root,
            text=f"{stage_name.upper()}  ·  {moves} MOVES",
            position=(0.0, 0.14),
            scale=1.35,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        MinimalistButton(
            text="NEXT STAGE  [ SPACE ]",
            parent=root,
            y=0.01,
            on_click=self.on_next_stage_cb,
            scale=(0.48, 0.065),
        )

        MinimalistButton(
            text="REPLAY STAGE",
            parent=root,
            y=-0.08,
            on_click=self.on_restart_cb,
            scale=(0.42, 0.065),
        )

        MinimalistButton(
            text="STAGE SELECT",
            parent=root,
            y=-0.17,
            on_click=lambda: self.show_stage_select_menu(current_stage=current_stage),
            scale=(0.42, 0.065),
        )

        self.victory_root = root
