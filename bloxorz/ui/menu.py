"""Menu systems, pause overlays, and minimalist stage selection matrix."""

from typing import Callable, Optional, Any
from ursina import Entity, Button, Text, color, camera, destroy, application

from bloxorz.config import CONFIG
from bloxorz.ui.theme import Palette
from bloxorz.ui.constants import MenuConstants, UIAnchor
from bloxorz.audio.sound_manager import play_sfx


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
        scale: tuple = MenuConstants.MINIMALIST_BTN_SCALE,
    ):
        c_text = color.hex(Palette.TEXT_MUTED.hex_code)
        c_hover = color.hex(Palette.TEXT_PRIMARY.hex_code)

        def _click_wrapper():
            play_sfx("click")
            if callable(on_click):
                on_click()

        kwargs = {}
        if callable(on_click):
            kwargs["on_click"] = _click_wrapper

        super().__init__(
            parent=parent,
            text=text.upper(),
            y=y,
            scale=scale,
            color=color.clear,
            highlight_color=color.clear,
            pressed_color=color.clear,
            text_color=c_text,
            highlight_text_color=c_hover,
            text_size=MenuConstants.MINIMALIST_BTN_TEXT_SCALE_FACTOR,
            highlight_text_size=MenuConstants.MINIMALIST_BTN_TEXT_SCALE_FACTOR,
            **kwargs,
        )

        self.default_x = self.x
        self.c_text = c_text
        self.c_hover = c_hover

    def on_mouse_enter(self):
        super().on_mouse_enter()
        self.text_entity.color = self.c_hover
        self.animate_x(
            self.default_x + MenuConstants.BTN_HOVER_OFFSET_X,
            duration=MenuConstants.BTN_ANIM_DURATION,
        )

    def on_mouse_exit(self):
        super().on_mouse_exit()
        self.text_entity.color = self.c_text
        self.animate_x(self.default_x, duration=MenuConstants.BTN_ANIM_DURATION)


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
        scale: tuple = MenuConstants.STAGE_CARD_SCALE,
    ):
        c_bg = (
            color.rgba(0.22, 0.74, 0.97, 0.20)
            if is_current
            else color.hex(Palette.BACKGROUND_SECONDARY.hex_code)
        )
        c_highlight = color.hex(Palette.TILE_NORMAL.hex_code)
        c_pressed = color.hex(Palette.TILE_PEDESTAL.hex_code)
        c_text = (
            color.hex(Palette.TEXT_ACCENT.hex_code)
            if is_current
            else color.hex(Palette.TEXT_MUTED.hex_code)
        )
        c_hover = color.hex(Palette.TEXT_PRIMARY.hex_code)

        def _click_wrapper():
            play_sfx("click")
            if callable(on_click):
                on_click()

        kwargs = {}
        if callable(on_click):
            kwargs["on_click"] = _click_wrapper

        super().__init__(
            parent=parent,
            text=f"STAGE {stage_idx:02d}",
            x=x,
            y=y,
            scale=scale,
            color=c_bg,
            highlight_color=c_highlight,
            pressed_color=c_pressed,
            text_color=c_text,
            highlight_text_color=c_hover,
            text_size=MenuConstants.STAGE_CARD_TEXT_SCALE_FACTOR,
            highlight_text_size=MenuConstants.STAGE_CARD_TEXT_SCALE_FACTOR,
            **kwargs,
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
        scale: tuple = MenuConstants.MENU_ACTION_BTN_SCALE,
    ):
        def _click_wrapper():
            play_sfx("click")
            if callable(on_click):
                on_click()

        kwargs = {}
        if callable(on_click):
            kwargs["on_click"] = _click_wrapper

        super().__init__(
            parent=parent,
            text=text.upper(),
            x=x,
            y=y,
            scale=scale,
            color=color.hex(Palette.BACKGROUND_SECONDARY.hex_code),
            highlight_color=color.hex(Palette.TILE_NORMAL.hex_code),
            pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
            text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            highlight_text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            text_size=MenuConstants.MENU_ACTION_BTN_TEXT_SCALE_FACTOR,
            highlight_text_size=MenuConstants.MENU_ACTION_BTN_TEXT_SCALE_FACTOR,
            **kwargs,
        )


class SettingToggleButton(Button):
    """Minimalist stateful toggle button for enabling/muting audio channels."""

    def __init__(
        self,
        is_active: bool,
        on_toggle: Callable[[], bool],
        parent: Entity,
        x: float,
        y: float,
        scale: tuple = MenuConstants.SETTING_TOGGLE_BTN_SCALE,
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
            text_color=(
                color.hex(Palette.TEXT_ACCENT.hex_code)
                if is_active
                else color.hex(Palette.TEXT_MUTED.hex_code)
            ),
            highlight_text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            text_size=MenuConstants.SETTING_TOGGLE_TEXT_SCALE_FACTOR,
            highlight_text_size=MenuConstants.SETTING_TOGGLE_TEXT_SCALE_FACTOR,
            on_click=self._handle_click,
        )
        self._update_label()

    def _update_label(self):
        if self.is_active:
            self.text = "ENABLED"
            self.color = color.rgba(0.22, 0.74, 0.97, 0.22)
            self.text_color = color.hex(Palette.TEXT_ACCENT.hex_code)
            if self.text_entity:
                self.text_entity.color = color.hex(Palette.TEXT_ACCENT.hex_code)
        else:
            self.text = "MUTED"
            self.color = color.hex(Palette.BACKGROUND_SECONDARY.hex_code)
            self.text_color = color.hex(Palette.TEXT_MUTED.hex_code)
            if self.text_entity:
                self.text_entity.color = color.hex(Palette.TEXT_MUTED.hex_code)

    def _handle_click(self):
        play_sfx("click")
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
        scale: tuple = MenuConstants.SETTING_STEPPER_BTN_SCALE,
    ):
        def _step_wrapper():
            play_sfx("click")
            if callable(on_step):
                on_step()

        super().__init__(
            parent=parent,
            text=text,
            x=x,
            y=y,
            scale=scale,
            color=color.hex(Palette.BACKGROUND_SECONDARY.hex_code),
            highlight_color=color.hex(Palette.TILE_NORMAL.hex_code),
            pressed_color=color.hex(Palette.TILE_PEDESTAL.hex_code),
            text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            highlight_text_color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            text_size=MenuConstants.SETTING_STEPPER_TEXT_SCALE_FACTOR,
            highlight_text_size=MenuConstants.SETTING_STEPPER_TEXT_SCALE_FACTOR,
            on_click=_step_wrapper,
        )


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
            scale=MenuConstants.BACKDROP_SCALE,
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=MenuConstants.Z_BACKDROP,
        )

        # Header Title & Subtitle
        Text(
            parent=root,
            text="SELECT STAGE",
            position=MenuConstants.STAGE_SELECT_TITLE_POS,
            scale=MenuConstants.STAGE_SELECT_TITLE_SCALE,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )
        Text(
            parent=root,
            text=f"ACTIVE: STAGE {current_stage:02d}  ·  {self.stages_count} ARCHITECTURAL PUZZLES",
            position=MenuConstants.STAGE_SELECT_SUBTITLE_POS,
            scale=MenuConstants.STAGE_SELECT_SUBTITLE_SCALE,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )

        # 7-column grid layout
        dx = MenuConstants.GRID_SPACING_X
        dy = MenuConstants.GRID_SPACING_Y
        y_start = MenuConstants.GRID_START_Y
        cols = MenuConstants.GRID_COLUMNS

        for idx in range(1, self.stages_count + 1):
            row = (idx - 1) // cols
            col = (idx - 1) % cols
            items_in_row = cols if row < 4 else (self.stages_count - (cols * 4))
            if row < 4:
                x_pos = (col - (cols - 1) / 2.0) * dx
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
        dx_bar = MenuConstants.STAGE_SELECT_BOTTOM_BAR_SPACING
        for i, (label, cb) in enumerate(actions):
            x_pos = (i - (len(actions) - 1) / 2.0) * dx_bar
            btn = MenuActionButton(
                text=label,
                parent=root,
                x=x_pos,
                y=MenuConstants.STAGE_SELECT_BOTTOM_BAR_Y,
                on_click=cb,
            )
            if i == 2:
                self._audio_btn = btn

        # Footer keyboard navigation hints
        Text(
            parent=root,
            text="[ ESC ] RESUME    ·    [ R ] RESTART    ·    [ O ] SETTINGS    ·    [ U ] UNDO    ·    [ P ] SOLVER",
            position=MenuConstants.STAGE_SELECT_HINT_POS,
            scale=MenuConstants.STAGE_SELECT_HINT_SCALE,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
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
            scale=MenuConstants.BACKDROP_SCALE,
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=MenuConstants.Z_BACKDROP,
        )

        # Monolithic Card Container
        Entity(
            parent=root,
            model="quad",
            scale=MenuConstants.SETTINGS_CONTAINER_SCALE,
            color=color.hex(Palette.BACKGROUND_SECONDARY.hex_code),
            z=MenuConstants.Z_CONTAINER_SURFACE,
        )
        # Subtle architectural border frame
        Entity(
            parent=root,
            model="quad",
            scale=MenuConstants.SETTINGS_BORDER_SCALE,
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=MenuConstants.Z_CONTAINER_BORDER,
        )

        # Header Title & Subtitle
        Text(
            parent=root,
            text="SETTINGS",
            position=MenuConstants.SETTINGS_TITLE_POS,
            scale=MenuConstants.SETTINGS_TITLE_SCALE,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )
        Text(
            parent=root,
            text="AUDIO, SOUND EFFECTS & STEERING CONFIGURATION",
            position=MenuConstants.SETTINGS_SUBTITLE_POS,
            scale=MenuConstants.SETTINGS_SUBTITLE_SCALE,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )

        # Divider line
        Entity(
            parent=root,
            model="quad",
            scale=MenuConstants.SETTINGS_DIVIDER_SCALE,
            position=(0.0, MenuConstants.SETTINGS_DIVIDER_1_Y),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=MenuConstants.Z_DIVIDER,
        )

        # --- SECTION 1: BACKGROUND MUSIC (BGM) ---
        Text(
            parent=root,
            text="BACKGROUND MUSIC",
            position=MenuConstants.SETTINGS_BGM_TITLE_POS,
            scale=MenuConstants.SETTINGS_BGM_TITLE_SCALE,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=UIAnchor.MIDDLE_LEFT,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )
        theme_name = (
            getattr(self.sound_mgr, "theme_track", "background.mp3").upper()
            if self.sound_mgr
            else "BACKGROUND.MP3"
        )
        Text(
            parent=root,
            text=f"THEME: {theme_name}",
            position=MenuConstants.SETTINGS_BGM_THEME_POS,
            scale=MenuConstants.SETTINGS_BGM_THEME_SCALE,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=UIAnchor.MIDDLE_LEFT,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )

        bgm_active = getattr(self.sound_mgr, "bgm_enabled", True) if self.sound_mgr else True
        SettingToggleButton(
            is_active=bgm_active,
            on_toggle=self.sound_mgr.toggle_bgm if self.sound_mgr else lambda: True,
            parent=root,
            x=MenuConstants.SETTINGS_BGM_TOGGLE_POS[0],
            y=MenuConstants.SETTINGS_BGM_TOGGLE_POS[1],
            scale=MenuConstants.SETTING_TOGGLE_BTN_SCALE,
        )

        # BGM Volume Gauge & Stepper
        initial_bgm_vol = getattr(self.sound_mgr, "bgm_volume", 0.5) if self.sound_mgr else 0.5
        bgm_vol_gauge = Text(
            parent=root,
            text=format_volume_gauge(initial_bgm_vol),
            position=MenuConstants.SETTINGS_BGM_GAUGE_POS,
            scale=MenuConstants.SETTINGS_BGM_GAUGE_SCALE,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
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
            x=MenuConstants.SETTINGS_BGM_STEP_MINUS_X,
            y=MenuConstants.SETTINGS_BGM_STEP_Y,
        )
        SettingStepperButton(
            text="+",
            on_step=lambda: step_bgm_vol(+0.1),
            parent=root,
            x=MenuConstants.SETTINGS_BGM_STEP_PLUS_X,
            y=MenuConstants.SETTINGS_BGM_STEP_Y,
        )

        # Divider line
        Entity(
            parent=root,
            model="quad",
            scale=MenuConstants.SETTINGS_DIVIDER_SCALE,
            position=(0.0, MenuConstants.SETTINGS_DIVIDER_2_Y),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=MenuConstants.Z_DIVIDER,
        )

        # --- SECTION 2: SOUND EFFECTS (SFX) ---
        Text(
            parent=root,
            text="SOUND EFFECTS (SFX)",
            position=MenuConstants.SETTINGS_SFX_TITLE_POS,
            scale=MenuConstants.SETTINGS_SFX_TITLE_SCALE,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=UIAnchor.MIDDLE_LEFT,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )
        Text(
            parent=root,
            text="TACTILE ROLLS, SWITCHES, FALLS & WIN CHORDS",
            position=MenuConstants.SETTINGS_SFX_DESC_POS,
            scale=MenuConstants.SETTINGS_SFX_DESC_SCALE,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=UIAnchor.MIDDLE_LEFT,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )

        sfx_active = getattr(self.sound_mgr, "sfx_enabled", True) if self.sound_mgr else True
        SettingToggleButton(
            is_active=sfx_active,
            on_toggle=self.sound_mgr.toggle_sfx if self.sound_mgr else lambda: True,
            parent=root,
            x=MenuConstants.SETTINGS_SFX_TOGGLE_POS[0],
            y=MenuConstants.SETTINGS_SFX_TOGGLE_POS[1],
            scale=MenuConstants.SETTING_TOGGLE_BTN_SCALE,
        )

        # SFX Volume Gauge & Stepper
        initial_sfx_vol = getattr(self.sound_mgr, "sfx_volume", 0.8) if self.sound_mgr else 0.8
        sfx_vol_gauge = Text(
            parent=root,
            text=format_volume_gauge(initial_sfx_vol),
            position=MenuConstants.SETTINGS_SFX_GAUGE_POS,
            scale=MenuConstants.SETTINGS_SFX_GAUGE_SCALE,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
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
            x=MenuConstants.SETTINGS_SFX_STEP_MINUS_X,
            y=MenuConstants.SETTINGS_SFX_STEP_Y,
        )
        SettingStepperButton(
            text="+",
            on_step=lambda: step_sfx_vol(+0.1),
            parent=root,
            x=MenuConstants.SETTINGS_SFX_STEP_PLUS_X,
            y=MenuConstants.SETTINGS_SFX_STEP_Y,
        )

        # Preview SFX Button
        def test_sfx():
            if self.sound_mgr:
                self.sound_mgr.play("roll")

        MenuActionButton(
            text="PREVIEW SFX",
            parent=root,
            x=MenuConstants.SETTINGS_SFX_PREVIEW_POS[0],
            y=MenuConstants.SETTINGS_SFX_PREVIEW_POS[1],
            scale=MenuConstants.SETTING_PREVIEW_BTN_SCALE,
            on_click=test_sfx,
        )

        # Divider line
        Entity(
            parent=root,
            model="quad",
            scale=MenuConstants.SETTINGS_DIVIDER_SCALE,
            position=(0.0, MenuConstants.SETTINGS_DIVIDER_3_Y),
            color=color.hex(Palette.SURFACE_BORDER.hex_code),
            z=MenuConstants.Z_DIVIDER,
        )

        # --- SECTION 3: STEERING CONTROLS & NAVIGATION ---
        scheme = getattr(CONFIG.controls, "arrow_scheme", "isometric").upper()
        scheme_btn = MenuActionButton(
            text=f"STEERING: {scheme}",
            parent=root,
            x=MenuConstants.SETTINGS_STEERING_BTN_POS[0],
            y=MenuConstants.SETTINGS_STEERING_BTN_POS[1],
            scale=MenuConstants.SETTING_STEERING_BTN_SCALE,
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
            x=MenuConstants.SETTINGS_BACK_BTN_POS[0],
            y=MenuConstants.SETTINGS_BACK_BTN_POS[1],
            scale=MenuConstants.SETTING_BACK_BTN_SCALE,
            on_click=lambda: self.show_stage_select_menu(current_stage=current_stage),
        )

        # Footer hints
        Text(
            parent=root,
            text="[ ESC ] BACK    ·    [ M ] MASTER MUTE    ·    [ R ] RESTART STAGE",
            position=MenuConstants.SETTINGS_FOOTER_HINT_POS,
            scale=MenuConstants.SETTINGS_FOOTER_HINT_SCALE,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
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
            scale=MenuConstants.BACKDROP_SCALE,
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=MenuConstants.Z_BACKDROP,
        )

        Text(
            parent=root,
            text="STAGE CLEARED",
            position=MenuConstants.VICTORY_TITLE_POS,
            scale=MenuConstants.VICTORY_TITLE_SCALE,
            color=color.hex(Palette.GOAL_RIM.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )

        Text(
            parent=root,
            text=f"{stage_name.upper()}  ·  {moves} MOVES",
            position=MenuConstants.VICTORY_INFO_POS,
            scale=MenuConstants.VICTORY_INFO_SCALE,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=UIAnchor.CENTER,
            z=MenuConstants.Z_FOREGROUND_TEXT,
        )

        MinimalistButton(
            text="NEXT STAGE  [ SPACE ]",
            parent=root,
            y=MenuConstants.VICTORY_NEXT_BTN_Y,
            on_click=self.on_next_stage_cb,
            scale=MenuConstants.VICTORY_NEXT_BTN_SCALE,
        )

        MinimalistButton(
            text="REPLAY STAGE",
            parent=root,
            y=MenuConstants.VICTORY_REPLAY_BTN_Y,
            on_click=self.on_restart_cb,
            scale=MenuConstants.VICTORY_REPLAY_BTN_SCALE,
        )

        MinimalistButton(
            text="STAGE SELECT",
            parent=root,
            y=MenuConstants.VICTORY_SELECT_BTN_Y,
            on_click=lambda: self.show_stage_select_menu(current_stage=current_stage),
            scale=MenuConstants.VICTORY_SELECT_BTN_SCALE,
        )

        self.victory_root = root
