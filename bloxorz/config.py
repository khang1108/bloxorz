"""Central configuration loader and dataclass contracts for Bloxorz 3D.

Reads configuration from config.toml (or config.json) to eliminate hardcoded
magic numbers and provide clean, debuggable parameters across graphics,
camera, audio, motion, and solver subsystems.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


@dataclass
class WindowConfig:
    """Window display and screen presentation settings."""
    title: str = "BLOXORZ 3D  ·  ARCHITECTURAL MINIMALISM"  # Application window title
    width: int = 1280         # Initial window width in pixels (16:9 HD standard)
    height: int = 720         # Initial window height in pixels (16:9 HD standard)
    borderless: bool = False  # Borderless window mode (False for standard OS window decorations)
    fullscreen: bool = False  # Fullscreen toggle (False for windowed mode)
    vsync: bool = True        # Vertical synchronization (eliminates tearing, syncs to 60/120/144Hz+)


@dataclass
class CameraConfig:
    """Isometric / dimetric projection, positioning, and framing parameters."""
    fov: float = 34.0         # Field of view in degrees; narrow 34 deg provides architectural isometric feel
    angle_x: float = 52.0     # Elevation pitch angle in degrees (52 deg optimal top-down angle)
    angle_y: float = -40.0    # Azimuthal yaw angle in degrees (-40 deg creates classic diagonal orientation)
    min_distance: float = 15.0  # Minimum camera standoff distance to avoid clipping small boards
    distance_diagonal_scale: float = 1.85  # Standoff multiplier per board diagonal unit (fits wide stages)
    distance_offset: float = 4.0  # Additional safety standoff buffer margin (units)
    transition_duration: float = 0.4  # Camera auto-framing glide duration in seconds (400ms out_cubic)
    orbit_speed_x: float = 120.0  # Orbit yaw sensitivity (degrees / screen drag)
    orbit_speed_y: float = 100.0  # Orbit pitch sensitivity (degrees / screen drag)
    zoom_speed: float = 1.8       # Zoom delta distance per scroll tick
    min_pitch: float = 15.0       # Minimum pitch angle in degrees
    max_pitch: float = 85.0       # Maximum pitch angle in degrees
    min_distance_factor: float = 0.45  # Minimum zoom distance factor
    max_distance_factor: float = 2.2   # Maximum zoom distance factor
    smoothing: float = 12.0       # Exponential damping factor for 60-120fps motion
    step_orbit_angle: float = 45.0  # Step rotation angle for Q/E keys (degrees)


@dataclass
class MotionConfig:
    """Kinematic timings, animation durations, and easing intervals."""
    roll_duration: float = 0.18  # Snappy Bloxpath roll speed (180ms)
    fall_duration: float = 1.30  # Fall animation duration in seconds
    victory_fall_duration: float = 3.50  # Goal plunge fall duration in seconds
    victory_pulse_duration: float = 3.50  # Backward-compatible alias
    teleport_flight_duration: float = 1.10  # Aerial flight duration during teleport split (seconds)
    fade_transition: float = 0.25  # UI modal scene fade transition duration in seconds


@dataclass
class BlockConfig:
    """3D block geometry scaling, descent gravity, and tumbling kinematics."""
    unit_scale_1: float = 0.86  # Dimension for 1-unit block edge; leaves 0.14 gap from 1.0 grid pitch
    unit_scale_2: float = 1.86  # Dimension for 2-unit block edge (2 * 1.0 - 0.14 gap)
    fall_gravity: float = 9.8   # Downward gravitational acceleration g = 9.8 m/s^2
    fall_rot_x: float = 120.0   # Tumbling angular velocity around X axis during fall in deg/sec
    fall_rot_y: float = 80.0    # Tumbling angular velocity around Y axis during fall in deg/sec
    fall_rot_z: float = 60.0    # Tumbling angular velocity around Z axis during fall in deg/sec
    victory_sink_depth: float = 16.0  # Target descent depth into goal hole when won (units)


@dataclass
class BoardConfig:
    """3D architectural monolith dimensions, tile layers, switches, and bridge depths."""
    tile_size: float = 0.86       # Surface tile width and length (grid cell pitch is 1.0; gap is 0.14)
    pedestal_y: float = -0.22     # Y-coordinate center of deep monolithic foundation reaching into abyss
    pedestal_height: float = 0.32  # Thickness of foundation pedestal
    pedestal_inset: float = 0.04  # Margin inset from surface tile (0.86 - 0.04 = 0.82)
    normal_slab_y: float = -0.06  # Y-coordinate center of standard surface tile
    normal_slab_height: float = 0.12  # Thickness of standard surface tile
    normal_inset_y: float = -0.005  # Y-coordinate of recessed decorative plate
    normal_inset_ratio: float = 0.72  # Scale ratio of recessed plate relative to tile_size (72%)
    fragile_slab_y: float = -0.04  # Y-coordinate of fragile orange terracotta tile
    fragile_slab_height: float = 0.08  # Thinner slab (0.08 vs 0.12) visually communicating fragility
    fragile_inset_y: float = 0.005  # Y-coordinate of warning center notch on fragile tile
    fragile_inset_ratio: float = 0.70  # Scale ratio of fragile warning notch (70%)
    goal_well_y: float = -0.55    # Y-coordinate center of deep black goal well
    goal_well_height: float = 0.90  # Depth of goal well chamber (creates bottomless effect)
    goal_rim_y: float = -0.02     # Y-coordinate of metallic gold rim surrounding goal
    goal_rim_height: float = 0.04  # Thickness of gold rim frame
    goal_rim_offset: float = 0.04  # Outer protruding margin of gold rim (0.86 + 0.04 = 0.90)
    goal_floor_y: float = -0.98   # Y-coordinate of glowing core floor at bottom of goal well
    goal_floor_ratio: float = 0.75  # Scale ratio of glowing goal floor (75%)
    goal_floor_height: float = 0.04  # Thickness of glowing goal floor plate
    switch_soft_radius: float = 0.52  # Diameter of round soft-touch switch disc (cyan)
    switch_soft_height: float = 0.08  # Height / thickness of soft switch disc
    switch_soft_y: float = 0.04   # Y-coordinate elevation of soft switch plate above tile
    switch_heavy_long: float = 0.64  # Length of heavy-pressure crossbar plate (crimson rose)
    switch_heavy_short: float = 0.20  # Width of heavy-pressure crossbar plate
    switch_heavy_height: float = 0.08  # Thickness of heavy-pressure crossbar plate
    switch_heavy_y: float = 0.04  # Y-coordinate elevation of heavy switch plate above tile
    bridge_open_y: float = -0.06  # Y-coordinate of bridge planks when deployed/flush with grid
    bridge_closed_y: float = -1.50  # Y-coordinate of bridge planks when sunken/retracted into abyss
    bridge_anim_duration: float = 0.25  # Duration for bridge rising/falling in seconds (250ms)
    switch_press_depth: float = 0.04  # Vertical depression distance when stepped on (units)
    switch_press_down_time: float = 0.08  # Switch depression descent time in seconds (80ms)
    switch_press_up_time: float = 0.12  # Switch rebound spring time in seconds (120ms)


@dataclass
class AudioConfig:
    """Procedural audio synthesis parameters, volume levels, and theme tracks."""
    enabled: bool = True          # Master audio mute toggle (True: enabled, False: muted)
    sample_rate: int = 44100      # Audio synthesis sample rate in Hz (CD quality 44.1 kHz)
    master_headroom: float = 0.75  # Amplitude headroom scaling (75% of max signed 16-bit integer)
    bgm_enabled: bool = True      # Background theme music enabled (True: playing, False: muted)
    bgm_volume: float = 0.50      # Background music playback volume (0.0 to 1.0)
    sfx_enabled: bool = True      # Sound effects enabled (True: playing, False: muted)
    sfx_volume: float = 0.80      # Sound effects playback volume (0.0 to 1.0)
    theme_track: str = "background.mp3"  # BGM theme filename located in assets/sounds/
    roll_duration: float = 0.07   # Duration of slate rolling tap waveform in seconds (70ms)
    switch_duration: float = 0.045  # Duration of mechanical click waveform in seconds (45ms)
    fall_duration: float = 0.40   # Duration of descending abyss whoosh waveform in seconds (400ms)
    win_duration: float = 0.60    # Duration of ambient victory chord waveform in seconds (600ms)
    undo_duration: float = 0.04   # Duration of subtle rewind pop waveform in seconds (40ms)


@dataclass
class SolverConfig:
    """Automated solver playback and bot inspection parameters."""
    default_delay: float = 0.08   # Delay between consecutive moves during solution animation in seconds (80ms)


@dataclass
class ControlsConfig:
    """Player input scheme and directional steering configuration."""
    arrow_scheme: str = "isometric"  # "isometric" (Up/W=+X, Down/S=-X, Left/A=-Y, Right/D=+Y) | "classic"


@dataclass
class AnimationConfig:
    """Tuning parameters for Animation & VFX subsystem - Bloxpath Inspired Polish."""
    # Sóng dập dìu cho các ô đi được (walkable board tiles floating like a raft on water)
    wave_enabled: bool = True
    wave_amplitude: float = 0.09
    wave_freq_x: float = 0.40
    wave_freq_z: float = 0.35
    wave_speed: float = 1.6

    # Bloxpath Column Sea (Ô nền bên ngoài gần như tĩnh, trồi lên sụt xuống bất đối xứng)
    column_sea_enabled: bool = True
    column_sea_padding: int = 8
    column_sea_amplitude: float = 0.50
    column_sea_speed: float = 1.50
    column_sea_freq_x: float = 0.40
    column_sea_freq_z: float = 0.35
    column_sea_base_y: float = -1.25
    palette_mode: str = "obsidian"  # "obsidian" (Chuẩn Bloxpath dark minimal) | "alabaster"

    # Bloxpath Stage Assembly Intro (Gạch trồi lên từ hư không khi vào màn)
    stage_intro_anim: bool = True
    stage_intro_duration: float = 0.32
    stage_intro_stagger: float = 0.025

    # Bloxpath Tile Step Feedback (Ô gạch phát sáng nhẹ khi khối hộp bước lên)
    tile_highlight_enabled: bool = True
    tile_highlight_duration: float = 0.22

    # Mặt sàn vững chãi (Không thụt lún giật)
    cushion_depth: float = 0.0
    cushion_radius: float = 0.0
    cushion_duration: float = 0.0

    # Lăn khối chuẩn Bloxpath: Khối đá cứng nguyên khối, dứt khoát, không cao su
    roll_squash_y: float = 1.0
    roll_stretch_xz: float = 1.0
    micro_bounce_height: float = 0.0
    micro_bounce_duration: float = 0.0
    ghost_trail_enabled: bool = True
    ghost_alpha: float = 0.15
    ghost_fade_speed: float = 3.5

    # Camera tĩnh tại 100%
    screen_shake_enabled: bool = False
    shake_intensity_roll: float = 0.0
    shake_intensity_impact: float = 0.0
    shake_intensity_shatter: float = 0.0
    shake_decay: float = 8.0

    # Hiệu ứng Teleport & Victory
    teleport_particle_count: int = 14
    victory_confetti_count: int = 36
    victory_vortex_speed: float = 140.0

    # Bụi lơ lửng tối giản
    ambient_dust_count: int = 16
    ambient_dust_range: float = 14.0
    ambient_dust_speed: float = 0.20


@dataclass
class BackgroundConfig:
    """Cyber grid environment and 3D background presentation settings."""
    enable_city_model: bool = True   # Set to True to display the 3D dark fantasy city model beneath the floating board
    enable_wall_gifs: bool = True    # Animated cyberpunk wall GIFs


@dataclass
class AppConfig:
    """Root configuration tree aggregating all subsystem configurations."""
    window: WindowConfig = field(default_factory=WindowConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    block: BlockConfig = field(default_factory=BlockConfig)
    board: BoardConfig = field(default_factory=BoardConfig)
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    controls: ControlsConfig = field(default_factory=ControlsConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)


def _apply_dict_to_dataclass(dc_instance: Any, data: Dict[str, Any]):
    """Recursively populates dataclass fields from a dictionary."""
    for key, val in data.items():
        if hasattr(dc_instance, key):
            setattr(dc_instance, key, val)


def load_config(file_path: Optional[Path] = None) -> AppConfig:
    """Finds, parses, and loads configuration from TOML or JSON."""
    cfg = AppConfig()

    # Search candidates
    search_paths = []
    if file_path:
        search_paths.append(Path(file_path))

    root_dir = Path(__file__).parent.parent
    search_paths.extend([
        Path("config.toml"),
        Path("config.json"),
        root_dir / "config.toml",
        root_dir / "config.json",
    ])

    loaded_data: Optional[Dict[str, Any]] = None
    for p in search_paths:
        if p.is_file():
            try:
                if p.suffix.lower() == ".toml":
                    with open(p, "rb") as f:
                        loaded_data = tomllib.load(f)
                    break
                elif p.suffix.lower() == ".json":
                    with open(p, "r", encoding="utf-8") as f:
                        loaded_data = json.load(f)
                    break
            except Exception as e:
                print(f"[Config] Warning: Failed parsing {p}: {e}")

    if not loaded_data:
        return cfg

    # Parse sections
    if "window" in loaded_data and isinstance(loaded_data["window"], dict):
        _apply_dict_to_dataclass(cfg.window, loaded_data["window"])

    if "camera" in loaded_data and isinstance(loaded_data["camera"], dict):
        _apply_dict_to_dataclass(cfg.camera, loaded_data["camera"])

    if "motion" in loaded_data and isinstance(loaded_data["motion"], dict):
        _apply_dict_to_dataclass(cfg.motion, loaded_data["motion"])

    # Graphics subsection
    graphics = loaded_data.get("graphics", {})
    if isinstance(graphics, dict):
        if "block" in graphics and isinstance(graphics["block"], dict):
            _apply_dict_to_dataclass(cfg.block, graphics["block"])
        if "board" in graphics and isinstance(graphics["board"], dict):
            _apply_dict_to_dataclass(cfg.board, graphics["board"])

    if "audio" in loaded_data and isinstance(loaded_data["audio"], dict):
        _apply_dict_to_dataclass(cfg.audio, loaded_data["audio"])

    if "background" in loaded_data and isinstance(loaded_data["background"], dict):
        _apply_dict_to_dataclass(cfg.background, loaded_data["background"])
    elif isinstance(graphics, dict) and "enable_city_model" in graphics:
        cfg.background.enable_city_model = bool(graphics["enable_city_model"])

    if "solver" in loaded_data and isinstance(loaded_data["solver"], dict):
        _apply_dict_to_dataclass(cfg.solver, loaded_data["solver"])

    if "controls" in loaded_data and isinstance(loaded_data["controls"], dict):
        _apply_dict_to_dataclass(cfg.controls, loaded_data["controls"])

    if "animation" in loaded_data and isinstance(loaded_data["animation"], dict):
        _apply_dict_to_dataclass(cfg.animation, loaded_data["animation"])

    # Environment variables override
    import os
    env_no_city = os.environ.get("BLOXORZ_NO_CITY", "").strip().lower()
    env_enable_city = os.environ.get("BLOXORZ_ENABLE_CITY", "").strip().lower()
    if env_no_city in ("1", "true", "yes"):
        cfg.background.enable_city_model = False
    elif env_enable_city in ("1", "true", "yes"):
        cfg.background.enable_city_model = True

    return cfg


# Global singleton instance
CONFIG = load_config()


def get_config() -> AppConfig:
    """Returns the global active AppConfig instance."""
    return CONFIG


def reload_config(file_path: Optional[Path] = None) -> AppConfig:
    """Reloads configuration from disk and updates CONFIG singleton."""
    global CONFIG
    CONFIG = load_config(file_path)
    return CONFIG
