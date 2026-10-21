from ursina import Entity, Text, color, camera
from bloxorz.ui.theme import Palette


class HUD:
    """Manages clean, icon-less HUD elements positioned at viewport boundaries."""

    def __init__(self):
        self.root = Entity(parent=camera.ui, name="hud_root")

        c_text_primary = color.hex(Palette.TEXT_PRIMARY.hex_code)
        c_text_muted = color.hex(Palette.TEXT_MUTED.hex_code)
        c_accent = color.hex(Palette.TEXT_ACCENT.hex_code)

        # Top-Left: Stage & Info
        self.stage_text = Text(
            parent=self.root,
            text="STAGE 01",
            position=(-0.82, 0.44),
            scale=1.35,
            color=c_text_primary,
            origin=(-0.5, 0.5),
        )
        self.subtitle_text = Text(
            parent=self.root,
            text="MINIMALIST ARCHITECTURE",
            position=(-0.82, 0.39),
            scale=0.85,
            color=c_text_muted,
            origin=(-0.5, 0.5),
        )

        # Top-Right: Moves count & Audio indicator
        self.moves_text = Text(
            parent=self.root,
            text="MOVES  00",
            position=(0.82, 0.44),
            scale=1.2,
            color=c_accent,
            origin=(0.5, 0.5),
        )

        # Bottom-Center: Minimalist hotkey guide (delicate and unobtrusive)
        self.guide_text = Text(
            parent=self.root,
            text="[ WASD / ARROWS ] ROLL   ·   [ U ] UNDO   ·   [ R ] RESTART   ·   [ P ] SOLVE   ·   [ ESC ] MENU",
            position=(0.0, -0.46),
            scale=0.58,
            color=c_text_muted,
            origin=(0.0, -0.5),
        )

        # Center Status message (e.g. STAGE CLEAR, FELL OFF)
        self.banner_text = Text(
            parent=self.root,
            text="",
            position=(0.0, 0.15),
            scale=2.2,
            color=c_text_primary,
            origin=(0.0, 0.0),
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

    def show_banner(self, message: str, color_token: str = Palette.TEXT_PRIMARY.hex_code):
        """Displays a prominent minimal banner in the center."""
        self.banner_text.text = message.upper()
        self.banner_text.color = color.hex(color_token)
        self.banner_text.visible = True

    def hide_banner(self):
        """Hides the center message banner."""
        self.banner_text.visible = False

    def set_visible(self, visible: bool):
        """Toggles HUD visibility."""
        self.root.visible = visible
