"""Tests for centralized configuration loader (TOML and JSON support)."""

import json
from pathlib import Path
from bloxorz.config import load_config, AppConfig, CONFIG


def test_default_config_loading():
    """Verifies that config.toml loads properly into CONFIG."""
    cfg = CONFIG
    assert isinstance(cfg, AppConfig)
    assert cfg.window.width == 1280
    assert cfg.window.height == 720
    assert cfg.camera.fov == 34.0
    assert cfg.camera.angle_x == 52.0
    assert cfg.camera.angle_y == -40.0
    assert cfg.motion.roll_duration == 0.20
    assert cfg.block.unit_scale_1 == 0.86
    assert cfg.board.tile_size == 0.86
    assert cfg.board.goal_floor_height == 0.04
    assert cfg.audio.sample_rate == 44100
    assert cfg.solver.default_delay == 0.08
    assert cfg.controls.arrow_scheme == "isometric"


def test_json_config_fallback(tmp_path: Path):
    """Verifies that a custom JSON configuration file can be parsed and merged."""
    json_path = tmp_path / "custom_config.json"
    custom_data = {
        "window": {
            "title": "Custom Test Title",
            "width": 1920,
            "height": 1080,
        },
        "camera": {
            "fov": 45.0,
        },
        "motion": {
            "roll_duration": 0.15,
        },
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(custom_data, f)

    cfg = load_config(json_path)
    assert cfg.window.title == "Custom Test Title"
    assert cfg.window.width == 1920
    assert cfg.window.height == 1080
    assert cfg.camera.fov == 45.0
    assert cfg.motion.roll_duration == 0.15
    # Unspecified fields retain sensible defaults
    assert cfg.audio.sample_rate == 44100
