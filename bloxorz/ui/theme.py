"""Design System tokens and unified minimalist color palette for Bloxorz 3D."""

from dataclasses import dataclass
from typing import Tuple
from bloxorz.config import CONFIG


class NeonHUD:
    """Cyberpunk accents scoped to solver controls and the minimap."""
    SURFACE = "#0A1020"
    BUTTON = "#121C32"
    HOVER = "#263651"
    PRESSED = "#1B3048"
    TEXT = "#EDF7FF"
    MUTED = "#8BABC4"
    CYAN = "#35F3FF"
    MAGENTA = "#FF3AC8"
    AMBER = "#FFD166"
    VIOLET = "#B48AFF"
    FLOOR = "#385777"
    CLOSED_BRIDGE = "#283044"
    ALGORITHMS = (CYAN, MAGENTA, AMBER, VIOLET)


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
    """Unified Neo-Minimalist Bloxpath Palette."""
    # Background & Atmosphere (Deep Abyssal Void with depth fog)
    BACKGROUND = ColorToken.from_hex("#05070D")
    BACKGROUND_SECONDARY = ColorToken.from_hex("#12161F")

    # Bloxpath Background Matrix Sea (Undulating column ocean)
    SEA_COLUMN_BODY = ColorToken.from_hex("#222630")
    SEA_COLUMN_RIM = ColorToken.from_hex("#00D2FF")
    SEA_COLUMN_CAP = ColorToken.from_hex("#262C38")

    # Board Tiles (Architectural Monoliths - Original Obsidian Slate)
    TILE_NORMAL = ColorToken.from_hex("#080D18")         # Top slate surface
    TILE_PEDESTAL = ColorToken.from_hex("#131720")       # Deep under-slab reaching into abyss
    TILE_INSET = ColorToken.from_hex("#0C1422")          # Inner architectural recessed plate
    TILE_BORDER = ColorToken.from_hex("#168BFF")
    UNDER_RIM = ColorToken.from_hex("#1E293B")

    # Bloxpath Alabaster Theme Tokens (Steam release alternative)
    TILE_ALABASTER = ColorToken.from_hex("#F1F5F9")
    TILE_ALABASTER_PEDESTAL = ColorToken.from_hex("#CBD5E1")
    TILE_ALABASTER_INSET = ColorToken.from_hex("#E2E8F0")
    TILE_ALABASTER_HIGHLIGHT = ColorToken.from_hex("#93C5FD")
    BLOCK_GOLDEN = ColorToken.from_hex("#EAB308")

    # The Block (Hero Element - Frosted Alabaster)
    BLOCK_CORE = ColorToken.from_hex("#F1F5F9")
    BLOCK_SPLIT_ACTIVE = ColorToken.from_hex("#22C55E")   # Emerald green split cube
    BLOCK_SPLIT_PASSIVE = ColorToken.from_hex("#CBD5E1")  # Light granite gray split cube
    BLOCK_SHADOW = ColorToken.from_hex("#040508", 0.5)

    # Interactive / Special Tiles (Distinctive Visual Cues)
    TILE_FRAGILE = ColorToken.from_hex("#FF9A1F")        # Amber-orange fragile surface
    TILE_FRAGILE_INSET = ColorToken.from_hex("#FFD166")  # Fissure highlight
    TILE_TELEPORT = ColorToken.from_hex("#A855F7")        # Purple splitter tile
    TILE_GOAL = ColorToken.from_hex("#040507")           # Absolute Void Hole
    GOAL_RIM = ColorToken.from_hex("#F59E0B")            # Radiant Gold Rim
    GOAL_GLOW = ColorToken.from_hex("#D97706")
    GOAL_BEAM = ColorToken.from_hex("#FFD21F")
    BRIDGE_ACTIVE = ColorToken.from_hex("#FFD21F")       # Gold active bridge
    BRIDGE_BORDER = ColorToken.from_hex("#FF3434")       # Red neon bridge outline
    SWITCH_SOFT = ColorToken.from_hex("#168BFF")         # Electric blue (Soft Touch)
    SWITCH_HEAVY = ColorToken.from_hex("#EF4444")        # Vivid Crimson (Heavy 'X' Cross)
    BRIDGE_INACTIVE = ColorToken.from_hex("#0F131A", 0.2)

    # Typography & HUD
    TEXT_PRIMARY = ColorToken.from_hex("#F8FAFC")        # Pure Chalk
    TEXT_MUTED = ColorToken.from_hex("#94A3B8")          # Soft Slate
    TEXT_ACCENT = ColorToken.from_hex("#38BDF8")         # Cyan Accent

    # UI Surface & Overlays
    SURFACE_OVERLAY = ColorToken.from_hex("#07090D", 0.90)
    SURFACE_BORDER = ColorToken.from_hex("#1E293B")

    # VFX & Particles Palette
    GHOST_TRAIL = ColorToken.from_hex("#38BDF8", 0.35)   # Cyan mờ cho bóng ma
    DUST_PARTICLE = ColorToken.from_hex("#FF8C00", 0.85) # Bụi tro lửa rực rỡ
    EMBER_ASH = ColorToken.from_hex("#FF5722", 0.90)     # Ánh lửa tro đỏ cam nóng rực
    EMBER_ASH_GLOW = ColorToken.from_hex("#FFAA00", 0.95)# Ánh lửa tro vàng cam hổ phách
    EMBER_ASH_SPARK = ColorToken.from_hex("#FFD54F", 1.00)# Đốm tàn tro rực sáng
    TILE_HIGHLIGHT = ColorToken.from_hex("#CBD5E1")      # Xung sáng tiếp đất rực rỡ (Platinum slate)
    SHOCKWAVE_RING = ColorToken.from_hex("#38BDF8", 0.60)# Vòng sóng xung kích
    CRUMBLE_FRAGMENT = ColorToken.from_hex("#E06D28")    # Mảnh vụn ô nứt
    VICTORY_GOLD = ColorToken.from_hex("#F59E0B")        # Vàng hoàng kim chiến thắng
    VICTORY_CYAN = ColorToken.from_hex("#38BDF8")        # Cyan chiến thắng
    VICTORY_WHITE = ColorToken.from_hex("#FFFFFF")       # Trắng ánh sáng
    TELEPORT_ENERGY = ColorToken.from_hex("#818CF8")     # Tím lam năng lượng

    # Cyberpunk Neon Magma Palette (Nham thạch neon cuộn chảy)
    LAVA_CORE = ColorToken.from_hex("#FF3C00")           # Neon Magma Orange
    LAVA_HOT = ColorToken.from_hex("#FF8800")            # Radiant Heat Amber
    LAVA_NEON_PINK = ColorToken.from_hex("#FF0055")      # Cyberpunk Neon Pink fissure
    LAVA_UNDERGLOW = ColorToken.from_hex("#FF4500", 0.85)# Radiant under-rim glow
    MAGMA_EMBER = ColorToken.from_hex("#FF5722", 0.75)   # Molten cinder spark
    MAGMA_SPARK = ColorToken.from_hex("#FFC107", 0.90)   # Electric heat spark

    # Teleport Sci-Fi Warp & Footstep VFX Tokens
    TELEPORT_BEAM = ColorToken.from_hex("#00F0FF", 0.80)     # Luminous Cyan Beam
    TELEPORT_BEAM_DST = ColorToken.from_hex("#38BDF8", 0.80) # Sky Descent Beam
    TELEPORT_PAD = ColorToken.from_hex("#00F0FF", 0.90)      # Holographic Runic Circle
    TELEPORT_RING = ColorToken.from_hex("#818CF8", 0.85)     # Ascent Energy Ring
    TELEPORT_GLOW = ColorToken.from_hex("#E0F2FE", 1.00)     # Dematerialization Flash
    FOOTSTEP_GLOW = ColorToken.from_hex("#00F0FF", 0.85)     # Neon Footstep Glow
    SEISMIC_RIPPLE = ColorToken.from_hex("#38BDF8", 0.60)    # Concentric ground wave


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
    TELEPORT_FLIGHT_DURATION = getattr(CONFIG.motion, "teleport_flight_duration", 1.10)
    FADE_TRANSITION = CONFIG.motion.fade_transition

    # Animation & VFX Motion Constants
    WAVE_ENABLED = getattr(CONFIG.animation, "wave_enabled", True)
    WAVE_AMPLITUDE = getattr(CONFIG.animation, "wave_amplitude", 0.04)
    CUSHION_DEPTH = getattr(CONFIG.animation, "cushion_depth", 0.0)
    GHOST_ALPHA = getattr(CONFIG.animation, "ghost_alpha", 0.18)
    GHOST_FADE_SPEED = getattr(CONFIG.animation, "ghost_fade_speed", 2.5)

