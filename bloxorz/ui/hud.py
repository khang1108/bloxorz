from typing import Optional
from ursina import Entity, Text, color, camera, invoke
from bloxorz.ui.theme import Palette
from bloxorz.ui.constants import HUDConstants


class HUD:
    """Manages clean, icon-less HUD elements positioned at viewport boundaries."""

    def __init__(self):
        self.root = Entity(parent=camera.ui, name="hud_root")
        self._banner_id = 0

        c_text_primary = color.hex(Palette.TEXT_PRIMARY.hex_code)
        c_text_muted = color.hex(Palette.TEXT_MUTED.hex_code)
        c_accent = color.hex(Palette.TEXT_ACCENT.hex_code)

        # Top-Left: Stage & Info
        self.stage_text = Text(
            parent=self.root,
            text="STAGE 01",
            position=HUDConstants.STAGE_POS,
            scale=HUDConstants.STAGE_SCALE,
            color=c_text_primary,
            origin=HUDConstants.STAGE_ORIGIN,
        )
        self.subtitle_text = Text(
            parent=self.root,
            text="MINIMALIST ARCHITECTURE",
            position=HUDConstants.SUBTITLE_POS,
            scale=HUDConstants.SUBTITLE_SCALE,
            color=c_text_muted,
            origin=HUDConstants.SUBTITLE_ORIGIN,
        )

        # Top-Right: Moves count & Audio indicator
        self.moves_text = Text(
            parent=self.root,
            text="MOVES  00",
            position=HUDConstants.MOVES_POS,
            scale=HUDConstants.MOVES_SCALE,
            color=c_accent,
            origin=HUDConstants.MOVES_ORIGIN,
        )

        # Bottom-Center: Minimalist hotkey guide (delicate and unobtrusive)
        self.guide_text = Text(
            parent=self.root,
            text=(
                "[ WASD / ARROWS ] ROLL   ·   [ RMB DRAG ] ORBIT   ·   "
                "[ SCROLL ] ZOOM   ·   [ Q/E ] ROTATE   ·   [ C ] RESET   ·   [ O ] SETTINGS   ·   [ ESC ] MENU"
            ),
            position=HUDConstants.GUIDE_POS,
            scale=HUDConstants.GUIDE_SCALE,
            color=c_text_muted,
            origin=HUDConstants.GUIDE_ORIGIN,
        )

        # Center Status message (e.g. STAGE CLEAR, FELL OFF)
        self.banner_text = Text(
            parent=self.root,
            text="",
            position=HUDConstants.BANNER_POS,
            scale=HUDConstants.BANNER_SCALE,
            color=c_text_primary,
            origin=HUDConstants.BANNER_ORIGIN,
            visible=False,
        )

    def update_stage(self, stage_name: str, subtitle: str = ""):
        """Updates stage header information."""
        self.stage_text.text = stage_name.upper()
        if subtitle:
            self.subtitle_text.text = subtitle.upper()

    def update_moves(self, count: int):
        """Updates move counter with monospaced padding."""
        self.moves_text.text = f"MOVES  {count:02d}"

    def show_banner(
        self,
        message: str,
        color_token: str = Palette.TEXT_PRIMARY.hex_code,
        duration: Optional[float] = 1.5,
    ):
        """Displays a prominent minimal banner in the center.

        If duration is provided (> 0), automatically dismisses the banner after the duration.
        """
        self._banner_id += 1
        current_id = self._banner_id

        self.banner_text.text = message.upper()
        self.banner_text.color = color.hex(color_token)
        self.banner_text.visible = True

        if duration is not None and duration > 0:
            try:
                def _auto_hide():
                    if self._banner_id == current_id:
                        self.hide_banner()

                invoke(_auto_hide, delay=duration)
            except Exception:
                pass

    def hide_banner(self):
        """Hides the center message banner."""
        self._banner_id += 1
        self.banner_text.visible = False

    def set_split_mode(self, is_split: bool):
        """Updates guide text to emphasize SPACE for switching blocks when split."""
        if is_split:
            self.guide_text.text = (
                "[ SPACE ] SWITCH CUBE   ·   [ WASD / ARROWS ] ROLL   ·   "
                "[ RMB DRAG ] ORBIT   ·   [ SCROLL ] ZOOM   ·   [ ESC ] MENU"
            )
        else:
            self.guide_text.text = (
                "[ WASD / ARROWS ] ROLL   ·   [ RMB DRAG ] ORBIT   ·   "
                "[ SCROLL ] ZOOM   ·   [ Q/E ] ROTATE   ·   [ C ] RESET   ·   [ O ] SETTINGS   ·   [ ESC ] MENU"
            )

    def set_visible(self, visible: bool):
        """Toggles HUD visibility."""
        self.root.visible = visible
