from typing import Callable, Optional
from ursina import Entity, Button, Text, color, camera, destroy

from bloxorz.ui.theme import Palette


class MinimalistButton(Button):
    """Clean typography-only button with subtle hover micro-interactions."""

    def __init__(
        self,
        text: str,
        parent: Entity,
        y: float,
        on_click: Optional[Callable[[], None]] = None,
        scale: tuple = (0.35, 0.05),
    ):
        c_text = color.hex(Palette.TEXT_MUTED.hex_code)
        c_hover = color.hex(Palette.TEXT_PRIMARY.hex_code)

        super().__init__(
            parent=parent,
            text=text.upper(),
            y=y,
            scale=scale,
            color=color.clear,
            highlight_color=color.clear,
            pressed_color=color.clear,
            on_click=on_click,
        )

        self.text_entity.color = c_text
        self.text_entity.scale = 1.1
        self.default_x = self.x
        self.c_text = c_text
        self.c_hover = c_hover

    def on_mouse_enter(self):
        self.text_entity.color = self.c_hover
        self.animate_x(self.default_x + 0.015, duration=0.1)

    def on_mouse_exit(self):
        self.text_entity.color = self.c_text
        self.animate_x(self.default_x, duration=0.1)


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
        stages_count: int = 5,
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

    def show_pause_menu(self):
        """Displays the sleek dark pause overlay."""
        self.close_all()

        root = Entity(parent=camera.ui, name="pause_menu")
        # Translucent dark backdrop
        Entity(
            parent=root,
            model='quad',
            scale=(2.5, 2.0),
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=1,
        )

        # Title
        Text(
            parent=root,
            text="PAUSED",
            position=(0.0, 0.22),
            scale=2.2,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        # Action Buttons
        MinimalistButton(
            text="CONTINUE",
            parent=root,
            y=0.08,
            on_click=self.on_resume_cb,
        )
        MinimalistButton(
            text="RESTART STAGE",
            parent=root,
            y=0.01,
            on_click=self.on_restart_cb,
        )
        MinimalistButton(
            text="STAGE SELECT",
            parent=root,
            y=-0.06,
            on_click=self.show_stage_select_menu,
        )

        # Audio Toggle
        is_audio_on = self.get_audio_status_cb()
        audio_btn = MinimalistButton(
            text=f"AUDIO: {'ON' if is_audio_on else 'OFF'}",
            parent=root,
            y=-0.13,
            on_click=lambda: self._toggle_audio_label(audio_btn),
        )

        MinimalistButton(
            text="QUIT GAME",
            parent=root,
            y=-0.22,
            on_click=lambda: from_ursina_quit(),
        )

        def from_ursina_quit():
            from ursina import application
            application.quit()

        self.pause_root = root

    def _toggle_audio_label(self, button: MinimalistButton):
        new_state = self.on_toggle_audio_cb()
        button.text = f"AUDIO: {'ON' if new_state else 'OFF'}"

    def show_victory_menu(self, stage_name: str, moves: int):
        """Displays the stage clear screen."""
        self.close_all()

        root = Entity(parent=camera.ui, name="victory_menu")
        Entity(
            parent=root,
            model='quad',
            scale=(2.5, 2.0),
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=1,
        )

        Text(
            parent=root,
            text="STAGE CLEARED",
            position=(0.0, 0.22),
            scale=2.4,
            color=color.hex(Palette.GOAL_RIM.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        Text(
            parent=root,
            text=f"{stage_name.upper()}  ·  {moves} MOVES",
            position=(0.0, 0.12),
            scale=1.1,
            color=color.hex(Palette.TEXT_MUTED.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        MinimalistButton(
            text="NEXT STAGE  [ SPACE ]",
            parent=root,
            y=0.01,
            on_click=self.on_next_stage_cb,
        )

        MinimalistButton(
            text="REPLAY STAGE",
            parent=root,
            y=-0.06,
            on_click=self.on_restart_cb,
        )

        MinimalistButton(
            text="STAGE SELECT",
            parent=root,
            y=-0.13,
            on_click=self.show_stage_select_menu,
        )

        self.victory_root = root

    def show_stage_select_menu(self):
        """Displays minimalist grid of available stages."""
        self.close_all()

        root = Entity(parent=camera.ui, name="stage_select_menu")
        Entity(
            parent=root,
            model='quad',
            scale=(2.5, 2.0),
            color=color.hex(Palette.SURFACE_OVERLAY.hex_code),
            z=1,
        )

        Text(
            parent=root,
            text="SELECT STAGE",
            position=(0.0, 0.26),
            scale=2.0,
            color=color.hex(Palette.TEXT_PRIMARY.hex_code),
            origin=(0.0, 0.0),
            z=0,
        )

        # Build Stage Cards
        for idx in range(1, self.stages_count + 1):
            y_pos = 0.14 - (idx - 1) * 0.075
            stage_idx = idx

            def make_handler(s_idx=stage_idx):
                return lambda: self.on_select_stage_cb(s_idx)

            MinimalistButton(
                text=f"STAGE {stage_idx:02d}",
                parent=root,
                y=y_pos,
                on_click=make_handler(),
            )

        # Back button
        MinimalistButton(
            text="BACK TO GAME",
            parent=root,
            y=-0.32,
            on_click=self.on_resume_cb,
        )

        self.stage_select_root = root
