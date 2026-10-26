"""Design System tokens and unified minimalist color palette for Bloxorz 3D."""

from dataclasses import dataclass
from typing import Tuple
from bloxorz.config import CONFIG


@dataclass(frozen=True)
class ColorToken:
    """Hex and RGB definitions for a single design token."""
    hex_code: str
    r: float
    g: float
    b: float
    a: float = 1.0

    @classmethod
    def from_hex(cls, hex_str: str, alpha: float = 1.0) -> "ColorToken":
        cleaned = hex_str.lstrip("#")
        r = int(cleaned[0:2], 16) / 255.0
        g = int(cleaned[2:4], 16) / 255.0
        b = int(cleaned[4:6], 16) / 255.0
        return cls(hex_code=hex_str, r=r, g=g, b=b, a=alpha)

    @property
    def rgb_tuple(self) -> Tuple[float, float, float]:
        return (self.r, self.g, self.b)

    @property
    def rgba_tuple(self) -> Tuple[float, float, float, float]:
        return (self.r, self.g, self.b, self.a)


class Palette:
    """Unified Neo-Minimalist 'Obsidian & Frosted Mineral' Palette."""
    # Background & Atmosphere (Deep Abyssal Void)
    BACKGROUND = ColorToken.from_hex("#090B0F")
    BACKGROUND_SECONDARY = ColorToken.from_hex("#12161F")

    # Board Tiles (Architectural Floating Monoliths)
    TILE_NORMAL = ColorToken.from_hex("#262F3D")         # Top slate surface
    TILE_PEDESTAL = ColorToken.from_hex("#131720")       # Deep under-slab reaching into abyss
    TILE_INSET = ColorToken.from_hex("#1A202A")          # Inner architectural recessed plate
    TILE_BORDER = ColorToken.from_hex("#3B4759")

    # The Block (Hero Element - Frosted Alabaster)
    BLOCK_CORE = ColorToken.from_hex("#F1F5F9")
    BLOCK_SHADOW = ColorToken.from_hex("#040508", 0.5)

    # Interactive / Special Tiles (Distinctive Visual Cues)
    TILE_FRAGILE = ColorToken.from_hex("#E06D28")        # Vivid Terracotta
    TILE_FRAGILE_INSET = ColorToken.from_hex("#9A3412")  # Warning inner core
    TILE_GOAL = ColorToken.from_hex("#040507")           # Absolute Void Hole
    GOAL_RIM = ColorToken.from_hex("#F59E0B")            # Radiant Gold Rim
    GOAL_GLOW = ColorToken.from_hex("#D97706")
    SWITCH_SOFT = ColorToken.from_hex("#38BDF8")         # Electric Cyan (Soft Touch)
    SWITCH_HEAVY = ColorToken.from_hex("#EF4444")        # Vivid Crimson (Heavy 'X' Cross)
    BRIDGE_ACTIVE = ColorToken.from_hex("#334155")       # Structural Slate Bridge
    BRIDGE_INACTIVE = ColorToken.from_hex("#0F131A", 0.2)

    # Typography & HUD
    TEXT_PRIMARY = ColorToken.from_hex("#F8FAFC")        # Pure Chalk
    TEXT_MUTED = ColorToken.from_hex("#94A3B8")          # Soft Slate
    TEXT_ACCENT = ColorToken.from_hex("#38BDF8")         # Cyan Accent

    # UI Surface & Overlays
    SURFACE_OVERLAY = ColorToken.from_hex("#07090D", 0.90)
    SURFACE_BORDER = ColorToken.from_hex("#1E293B")


class Typography:
    """Scale and font sizing tokens."""
    SIZE_TITLE = 36
    SIZE_SUBTITLE = 20
    SIZE_BODY = 14
    SIZE_CAPTION = 11

    # Letter spacing and line height
    LETTER_SPACING_WIDE = 0.15
    LETTER_SPACING_NORMAL = 0.05


class Motion:
    """Motion curves and duration constants for 60-120fps animations."""
    ROLL_DURATION = CONFIG.motion.roll_duration
    FALL_DURATION = getattr(CONFIG.motion, "fall_duration", 1.30)
    VICTORY_FALL_DURATION = getattr(CONFIG.motion, "victory_fall_duration", 4.50)
    VICTORY_PULSE_DURATION = VICTORY_FALL_DURATION
    TELEPORT_FLIGHT_DURATION = getattr(CONFIG.motion, "teleport_flight_duration", 0.70)
    FADE_TRANSITION = CONFIG.motion.fade_transition
