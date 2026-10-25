"""Centralized layout constants, UI coordinates, scale factors, and anchors for Bloxorz UI."""

from typing import Tuple

Point2D = Tuple[float, float]
Size2D = Tuple[float, float]


class UIAnchor:
    """Standard origin alignment anchors in Ursina camera.ui space."""
    TOP_LEFT: Point2D = (-0.5, 0.5)
    TOP_RIGHT: Point2D = (0.5, 0.5)
    TOP_CENTER: Point2D = (0.0, 0.5)
    BOTTOM_CENTER: Point2D = (0.0, -0.5)
    CENTER: Point2D = (0.0, 0.0)
    MIDDLE_LEFT: Point2D = (-0.5, 0.0)
    MIDDLE_RIGHT: Point2D = (0.5, 0.0)


class HUDConstants:
    """Coordinates, scale tokens, and anchors for the head-up display."""
    STAGE_POS: Point2D = (-0.82, 0.44)
    STAGE_SCALE: float = 1.35
    STAGE_ORIGIN: Point2D = UIAnchor.TOP_LEFT

    SUBTITLE_POS: Point2D = (-0.82, 0.39)
    SUBTITLE_SCALE: float = 0.85
    SUBTITLE_ORIGIN: Point2D = UIAnchor.TOP_LEFT

    MOVES_POS: Point2D = (0.82, 0.44)
    MOVES_SCALE: float = 1.20
    MOVES_ORIGIN: Point2D = UIAnchor.TOP_RIGHT

    GUIDE_POS: Point2D = (0.0, -0.46)
    GUIDE_SCALE: float = 0.48
    GUIDE_ORIGIN: Point2D = UIAnchor.BOTTOM_CENTER

    BANNER_POS: Point2D = (0.0, 0.15)
    BANNER_SCALE: float = 2.20
    BANNER_ORIGIN: Point2D = UIAnchor.CENTER


class MenuConstants:
    """Dimensions, spacing, z-depths, and coordinates for menu and overlay screens."""
    # Shared Backdrop & Overlay Depth
    BACKDROP_SCALE: Size2D = (2.5, 2.0)
    BACKDROP_Z: float = 1.0

    # Button Sizes & Scaling Factors
    MINIMALIST_BTN_SCALE: Size2D = (0.45, 0.065)
    MINIMALIST_BTN_TEXT_SCALE_FACTOR: float = 1.25
    BTN_HOVER_OFFSET_X: float = 0.015
    BTN_ANIM_DURATION: float = 0.10

    STAGE_CARD_SCALE: Size2D = (0.142, 0.050)
    STAGE_CARD_TEXT_SCALE_FACTOR: float = 0.82

    MENU_ACTION_BTN_SCALE: Size2D = (0.24, 0.050)
    MENU_ACTION_BTN_TEXT_SCALE_FACTOR: float = 0.85

    SETTING_TOGGLE_BTN_SCALE: Size2D = (0.16, 0.046)
    SETTING_TOGGLE_TEXT_SCALE_FACTOR: float = 0.85
    SETTING_STEPPER_BTN_SCALE: Size2D = (0.046, 0.044)
    SETTING_STEPPER_TEXT_SCALE_FACTOR: float = 0.95
    SETTING_PREVIEW_BTN_SCALE: Size2D = (0.24, 0.042)
    SETTING_STEERING_BTN_SCALE: Size2D = (0.38, 0.046)
    SETTING_BACK_BTN_SCALE: Size2D = (0.28, 0.046)

    # Z-depths for architectural layer stacking
    Z_BACKDROP: float = 1.0
    Z_CONTAINER_BORDER: float = 0.9
    Z_CONTAINER_SURFACE: float = 0.8
    Z_DIVIDER: float = 0.5
    Z_FOREGROUND_TEXT: float = 0.0

    # Stage Select Grid Layout
    GRID_COLUMNS: int = 7
    GRID_SPACING_X: float = 0.155
    GRID_SPACING_Y: float = 0.064
    GRID_START_Y: float = 0.18

    STAGE_SELECT_TITLE_POS: Point2D = (0.0, 0.38)
    STAGE_SELECT_TITLE_SCALE: float = 2.40
    STAGE_SELECT_SUBTITLE_POS: Point2D = (0.0, 0.30)
    STAGE_SELECT_SUBTITLE_SCALE: float = 1.10
    STAGE_SELECT_BOTTOM_BAR_Y: float = -0.21
    STAGE_SELECT_BOTTOM_BAR_SPACING: float = 0.26
    STAGE_SELECT_HINT_POS: Point2D = (0.0, -0.29)
    STAGE_SELECT_HINT_SCALE: float = 0.95

    # Settings Modal Screen
    SETTINGS_CONTAINER_SCALE: Size2D = (1.02, 0.74)
    SETTINGS_BORDER_SCALE: Size2D = (1.026, 0.746)
    SETTINGS_DIVIDER_SCALE: Size2D = (0.88, 0.002)

    SETTINGS_TITLE_POS: Point2D = (0.0, 0.30)
    SETTINGS_TITLE_SCALE: float = 2.20
    SETTINGS_SUBTITLE_POS: Point2D = (0.0, 0.245)
    SETTINGS_SUBTITLE_SCALE: float = 0.95

    SETTINGS_DIVIDER_1_Y: float = 0.205
    SETTINGS_BGM_TITLE_POS: Point2D = (-0.41, 0.145)
    SETTINGS_BGM_TITLE_SCALE: float = 1.05
    SETTINGS_BGM_THEME_POS: Point2D = (-0.41, 0.095)
    SETTINGS_BGM_THEME_SCALE: float = 0.78
    SETTINGS_BGM_TOGGLE_POS: Point2D = (0.31, 0.145)
    SETTINGS_BGM_GAUGE_POS: Point2D = (0.21, 0.085)
    SETTINGS_BGM_GAUGE_SCALE: float = 0.95
    SETTINGS_BGM_STEP_MINUS_X: float = 0.06
    SETTINGS_BGM_STEP_PLUS_X: float = 0.36
    SETTINGS_BGM_STEP_Y: float = 0.085

    SETTINGS_DIVIDER_2_Y: float = 0.025
    SETTINGS_SFX_TITLE_POS: Point2D = (-0.41, -0.04)
    SETTINGS_SFX_TITLE_SCALE: float = 1.05
    SETTINGS_SFX_DESC_POS: Point2D = (-0.41, -0.09)
    SETTINGS_SFX_DESC_SCALE: float = 0.78
    SETTINGS_SFX_TOGGLE_POS: Point2D = (0.31, -0.04)
    SETTINGS_SFX_GAUGE_POS: Point2D = (0.21, -0.10)
    SETTINGS_SFX_GAUGE_SCALE: float = 0.95
    SETTINGS_SFX_STEP_MINUS_X: float = 0.06
    SETTINGS_SFX_STEP_PLUS_X: float = 0.36
    SETTINGS_SFX_STEP_Y: float = -0.10
    SETTINGS_SFX_PREVIEW_POS: Point2D = (-0.28, -0.155)

    SETTINGS_DIVIDER_3_Y: float = -0.205
    SETTINGS_STEERING_BTN_POS: Point2D = (-0.17, -0.26)
    SETTINGS_BACK_BTN_POS: Point2D = (0.25, -0.26)
    SETTINGS_FOOTER_HINT_POS: Point2D = (0.0, -0.33)
    SETTINGS_FOOTER_HINT_SCALE: float = 0.90

    # Victory Modal Screen
    VICTORY_TITLE_POS: Point2D = (0.0, 0.25)
    VICTORY_TITLE_SCALE: float = 2.80
    VICTORY_INFO_POS: Point2D = (0.0, 0.14)
    VICTORY_INFO_SCALE: float = 1.35
    VICTORY_NEXT_BTN_Y: float = 0.01
    VICTORY_NEXT_BTN_SCALE: Size2D = (0.48, 0.065)
    VICTORY_REPLAY_BTN_Y: float = -0.08
    VICTORY_REPLAY_BTN_SCALE: Size2D = (0.42, 0.065)
    VICTORY_SELECT_BTN_Y: float = -0.17
    VICTORY_SELECT_BTN_SCALE: Size2D = (0.42, 0.065)
