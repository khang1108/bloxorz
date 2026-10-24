"""Menu systems, pause overlays, and minimalist stage selection matrix."""

from typing import Callable, Optional, Any
from ursina import Entity, Button, Text, color, camera, destroy, application

from bloxorz.config import CONFIG
from bloxorz.ui.theme import Palette


def format_volume_gauge(volume: float) -> str:
    """Formats a volume level (0.0 - 1.0) into a percentage and precision VU-meter gauge."""
    pct = int(round(volume * 100))
    filled_bars = int(round(volume * 10))
    empty_bars = max(0, 10 - filled_bars)
    return f"{pct:3d}%  [ {'|' * filled_bars}{'-' * empty_bars} ]"


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
    """Bottom action button for Pause, Stage Select, and Settings screens."""

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


class SettingToggleButton(Button):
    """Minimalist stateful toggle button for enabling/muting audio channels."""

    def __init__(
        self,
        is_active: bool,
        on_toggle: Callable[[], bool],
        parent: Entity,
        x: float,
        y: float,
        scale: tuple = (0.16, 0.046),
    ):
        self.is_active = is_active
        self.on_toggle_cb = on_toggle
        super().__init__(
            parent=parent,
            text="ENABLED" if is_active else "MUTED",
            x=x,
            y=y,
            scale=scale,
            color=(
                color.rgba(0.22, 0.74, 0.97, 0.22)
                if is_active
                else color.hex(Palette.BACKGROUND_SECONDARY.hex_code)
            ),
            highlight_color=color.hex(Palette.TILE_NORMAL.hex_code),
            pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
            on_click=self._handle_click,
        )
        self.text_entity.scale *= 0.85
        self._update_label()

    def _update_label(self):
        if self.is_active:
            self.text = "ENABLED"
            self.color = color.rgba(0.22, 0.74, 0.97, 0.22)
            self.text_entity.color = color.hex(Palette.TEXT_ACCENT.hex_code)
        else:
            self.text = "MUTED"
            self.color = color.hex(Palette.BACKGROUND_SECONDARY.hex_code)
            self.text_entity.color = color.hex(Palette.TEXT_MUTED.hex_code)

    def _handle_click(self):
        self.is_active = self.on_toggle_cb()
        self._update_label()


class SettingStepperButton(Button):
    """Compact precision stepper button for incrementing or decrementing volume."""

    def __init__(
        self,
        text: str,
        on_step: Callable[[], None],
        parent: Entity,
        x: float,
        y: float,
        scale: tuple = (0.046, 0.044),
    ):
        super().__init__(
            parent=parent,
            text=text,
            x=x,
            y=y,
            scale=scale,
            color=color.hex(Palette.BACKGROUND_SECONDARY.hex_code),
            highlight_color=color.hex(Palette.TILE_NORMAL.hex_code),
            pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
            on_click=on_step,
        )
        self.text_entity.scale *= 0.95
        self.text_entity.color = color.hex(Palette.TEXT_PRIMARY.hex_code)


class MenuManager:
    """Controls transitions between Gameplay, Pause, Stage Select, Settings, and Victory."""

    def __init__(
        self,
        on_resume: Callable[[], None],
        on_restart: Callable[[], None],
        on_select_stage: Callable[[int], None],
        on_next_stage: Callable[[], None],
        on_toggle_audio: Callable[[], bool],
        get_audio_status: Callable[[], bool],
        stages_count: int = 33,
        sound_mgr: Optional[Any] = None,
    ):
        self.on_resume_cb = on_resume
        self.on_restart_cb = on_restart
        self.on_select_stage_cb = on_select_stage
        self.on_next_stage_cb = on_next_stage
        self.on_toggle_audio_cb = on_toggle_audio
        self.get_audio_status_cb = get_audio_status
        self.stages_count = stages_count
        self.sound_mgr = sound_mgr

        self.pause_root: Optional[Entity] = None
        self.victory_root: Optional[Entity] = None
        self.stage_select_root: Optional[Entity] = None
        self.settings_root: Optional[Entity] = None
        self._audio_btn: Optional[MenuActionButton] = None

    def is_any_menu_open(self) -> bool:
        """Returns True if any modal overlay is currently visible."""
        return bool(self.pause_root or self.stage_select_root or self.victory_root or self.settings_root)

    def is_settings_open(self) -> bool:
        """Returns True if settings modal overlay is currently visible."""
        return self.settings_root is not None

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
        if self.settings_root:
            destroy(self.settings_root)
            self.settings_root = None
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

        # Bottom action bar: CONTINUE, RESTART, SETTINGS, QUIT
        actions = [
            ("CONTINUE", self.on_resume_cb),
            ("RESTART", self.on_restart_cb),
            ("SETTINGS", lambda: self.show_settings_menu(current_stage=current_stage)),
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
            text="[ ESC ] RESUME    ·    [ R ] RESTART    ·    [ O ] SETTINGS    ·    [ U ] UNDO    ·    [ P ] SOLVER",
            position=(0.0, -0.29),
            scale=0.95,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        self.stage_select_root = root

    def show_settings_menu(self, current_stage: int = 1):
        """Displays the Swiss minimalist Settings & Preferences overlay."""
        self.close_all()

        root = Entity(parent=camera.ui, name="settings_menu")
        # Translucent dark backdrop
        Entity(
            parent=root,
            model="quad",
            scale=(2.5, 2.0),
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=1,
        )

        # Monolithic Card Container
        Entity(
            parent=root,
            model="quad",
            scale=(1.02, 0.74),
            color=color.hex(Palette.BACKGROUND_SECONDARY.hex_code),
            z=0.8,
        )
        # Subtle architectural border frame
        Entity(
            parent=root,
            model="quad",
            scale=(1.026, 0.746),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=0.9,
        )

        # Header Title & Subtitle
        Text(
            parent=root,
            text="SETTINGS",
            position=(0.0, 0.30),
            scale=2.2,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )
        Text(
            parent=root,
            text="AUDIO, SOUND EFFECTS & STEERING CONFIGURATION",
            position=(0.0, 0.245),
            scale=0.95,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        # Divider line
        Entity(
            parent=root,
            model="quad",
            scale=(0.88, 0.002),
            position=(0.0, 0.205),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=0.5,
        )

        # --- SECTION 1: BACKGROUND MUSIC (BGM) ---
        Text(
            parent=root,
            text="BACKGROUND MUSIC",
            position=(-0.41, 0.145),
            scale=1.05,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=(-0.5, 0.0),
            z=0,
        )
        theme_name = (
            getattr(self.sound_mgr, "theme_track", "background.mp3").upper()
            if self.sound_mgr
            else "BACKGROUND.MP3"
        )
        Text(
            parent=root,
            text=f"THEME: {theme_name}",
            position=(-0.41, 0.095),
            scale=0.78,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(-0.5, 0.0),
            z=0,
        )

        bgm_active = getattr(self.sound_mgr, "bgm_enabled", True) if self.sound_mgr else True
        SettingToggleButton(
            is_active=bgm_active,
            on_toggle=self.sound_mgr.toggle_bgm if self.sound_mgr else lambda: True,
            parent=root,
            x=0.31,
            y=0.145,
            scale=(0.17, 0.044),
        )

        # BGM Volume Gauge & Stepper
        initial_bgm_vol = getattr(self.sound_mgr, "bgm_volume", 0.5) if self.sound_mgr else 0.5
        bgm_vol_gauge = Text(
            parent=root,
            text=format_volume_gauge(initial_bgm_vol),
            position=(0.21, 0.085),
            scale=0.95,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        def step_bgm_vol(delta: float):
            if not self.sound_mgr:
                return
            new_v = max(0.0, min(1.0, round(self.sound_mgr.bgm_volume + delta, 1)))
            self.sound_mgr.set_bgm_volume(new_v)
            bgm_vol_gauge.text = format_volume_gauge(new_v)

        SettingStepperButton(
            text="-",
            on_step=lambda: step_bgm_vol(-0.1),
            parent=root,
            x=0.06,
            y=0.085,
        )
        SettingStepperButton(
            text="+",
            on_step=lambda: step_bgm_vol(+0.1),
            parent=root,
            x=0.36,
            y=0.085,
        )

        # Divider line
        Entity(
            parent=root,
            model="quad",
            scale=(0.88, 0.002),
            position=(0.0, 0.025),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=0.5,
        )

        # --- SECTION 2: SOUND EFFECTS (SFX) ---
        Text(
            parent=root,
            text="SOUND EFFECTS (SFX)",
            position=(-0.41, -0.04),
            scale=1.05,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=(-0.5, 0.0),
            z=0,
        )
        Text(
            parent=root,
            text="TACTILE ROLLS, SWITCHES, FALLS & WIN CHORDS",
            position=(-0.41, -0.09),
            scale=0.78,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(-0.5, 0.0),
            z=0,
        )

        sfx_active = getattr(self.sound_mgr, "sfx_enabled", True) if self.sound_mgr else True
        SettingToggleButton(
            is_active=sfx_active,
            on_toggle=self.sound_mgr.toggle_sfx if self.sound_mgr else lambda: True,
            parent=root,
            x=0.31,
            y=-0.04,
            scale=(0.17, 0.044),
        )

        # SFX Volume Gauge & Stepper
        initial_sfx_vol = getattr(self.sound_mgr, "sfx_volume", 0.8) if self.sound_mgr else 0.8
        sfx_vol_gauge = Text(
            parent=root,
            text=format_volume_gauge(initial_sfx_vol),
            position=(0.21, -0.10),
            scale=0.95,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        def step_sfx_vol(delta: float):
            if not self.sound_mgr:
                return
            new_v = max(0.0, min(1.0, round(self.sound_mgr.sfx_volume + delta, 1)))
            self.sound_mgr.set_sfx_volume(new_v)
            sfx_vol_gauge.text = format_volume_gauge(new_v)
            self.sound_mgr.play("switch")

        SettingStepperButton(
            text="-",
            on_step=lambda: step_sfx_vol(-0.1),
            parent=root,
            x=0.06,
            y=-0.10,
        )
        SettingStepperButton(
            text="+",
            on_step=lambda: step_sfx_vol(+0.1),
            parent=root,
            x=0.36,
            y=-0.10,
        )

        # Preview SFX Button
        def test_sfx():
            if self.sound_mgr:
                self.sound_mgr.play("roll")

        MenuActionButton(
            text="PREVIEW SFX",
            parent=root,
            x=-0.28,
            y=-0.155,
            scale=(0.24, 0.042),
            on_click=test_sfx,
        )

        # Divider line
        Entity(
            parent=root,
            model="quad",
            scale=(0.88, 0.002),
            position=(0.0, -0.205),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=0.5,
        )

        # --- SECTION 3: STEERING CONTROLS & NAVIGATION ---
        scheme = getattr(CONFIG.controls, "arrow_scheme", "isometric").upper()
        scheme_btn = MenuActionButton(
            text=f"STEERING: {scheme}",
            parent=root,
            x=-0.17,
            y=-0.26,
            scale=(0.38, 0.046),
        )

        def toggle_scheme():
            current = getattr(CONFIG.controls, "arrow_scheme", "isometric")
            new_s = "classic" if current == "isometric" else "isometric"
            CONFIG.controls.arrow_scheme = new_s
            scheme_btn.text = f"STEERING: {new_s.upper()}"

        scheme_btn.on_click = toggle_scheme

        MenuActionButton(
            text="BACK TO MENU",
            parent=root,
            x=0.25,
            y=-0.26,
            scale=(0.28, 0.046),
            on_click=lambda: self.show_stage_select_menu(current_stage=current_stage),
        )

        # Footer hints
        Text(
            parent=root,
            text="[ ESC ] BACK    ·    [ M ] MASTER MUTE    ·    [ R ] RESTART STAGE",
            position=(0.0, -0.33),
            scale=0.90,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        self.settings_root = root

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
