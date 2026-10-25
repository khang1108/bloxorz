"""Unit tests for BGM audio playback, SFX controls, and volume management."""

from pathlib import Path
from unittest.mock import MagicMock
from bloxorz.config import AppConfig, AudioConfig
from bloxorz.audio.sound_manager import SoundManager


def test_sound_manager_initialization(tmp_path: Path):
    """Verifies that SoundManager initializes with config parameters."""
    from unittest.mock import patch
    cfg = AppConfig(
        audio=AudioConfig(
            enabled=True,
            bgm_enabled=True,
            bgm_volume=0.45,
            sfx_enabled=True,
            sfx_volume=0.75,
            theme_track="background.mp3",
        )
    )
    with patch("bloxorz.audio.sound_manager.CONFIG", cfg):
        sm = SoundManager(assets_dir=tmp_path)
        assert sm.enabled is True
        assert sm.bgm_enabled is True
        assert sm.bgm_volume == 0.45
        assert sm.sfx_enabled is True
        assert sm.sfx_volume == 0.75
        assert sm.theme_track == "background.mp3"


def test_bgm_volume_clamping(tmp_path: Path):
    """BGM volume should be clamped between 0.0 and 1.0."""
    sm = SoundManager(assets_dir=tmp_path)
    sm.bgm = MagicMock()

    sm.set_bgm_volume(0.3)
    assert sm.bgm_volume == 0.3
    assert sm.bgm.volume == 0.3

    sm.set_bgm_volume(1.5)
    assert sm.bgm_volume == 1.0
    assert sm.bgm.volume == 1.0

    sm.set_bgm_volume(-0.5)
    assert sm.bgm_volume == 0.0
    assert sm.bgm.volume == 0.0


def test_sfx_volume_clamping(tmp_path: Path):
    """SFX volume should be clamped between 0.0 and 1.0 and update all sound entities."""
    sm = SoundManager(assets_dir=tmp_path)
    mock_roll = MagicMock()
    mock_switch = MagicMock()
    sm.sounds = {"roll": mock_roll, "switch": mock_switch}

    sm.set_sfx_volume(0.6)
    assert sm.sfx_volume == 0.6
    assert mock_roll.volume == 0.6
    assert mock_switch.volume == 0.6

    sm.set_sfx_volume(2.0)
    assert sm.sfx_volume == 1.0
    assert mock_roll.volume == 1.0

    sm.set_sfx_volume(-1.0)
    assert sm.sfx_volume == 0.0
    assert mock_roll.volume == 0.0


def test_toggle_bgm(tmp_path: Path):
    """Toggling BGM should flip bgm_enabled and call play/stop."""
    sm = SoundManager(assets_dir=tmp_path)
    sm.bgm = MagicMock()
    sm.bgm_enabled = True
    sm.enabled = True

    # Toggle OFF
    state = sm.toggle_bgm()
    assert state is False
    assert sm.bgm_enabled is False
    sm.bgm.clip.stop.assert_called_once()

    # Toggle ON
    sm.bgm.reset_mock()
    sm.bgm.playing = False
    state = sm.toggle_bgm()
    assert state is True
    assert sm.bgm_enabled is True
    sm.bgm.clip.play.assert_called_once()


def test_toggle_sfx(tmp_path: Path):
    """Toggling SFX should flip sfx_enabled and mute sound effect playback."""
    sm = SoundManager(assets_dir=tmp_path)
    mock_sound = MagicMock()
    sm.sounds = {"roll": mock_sound}
    sm.sfx_enabled = True
    sm.enabled = True

    # Play when enabled
    sm.play("roll")
    mock_sound.clip.play.assert_called_once()

    # Toggle OFF
    mock_sound.reset_mock()
    state = sm.toggle_sfx()
    assert state is False
    assert sm.sfx_enabled is False

    # Attempt to play while disabled -> ignored
    sm.play("roll")
    mock_sound.clip.play.assert_not_called()


def test_toggle_master_audio(tmp_path: Path):
    """Master audio toggle should stop BGM and prevent SFX from playing."""
    sm = SoundManager(assets_dir=tmp_path)
    sm.bgm = MagicMock()
    mock_sound = MagicMock()
    sm.sounds = {"switch": mock_sound}
    sm.enabled = True
    sm.bgm_enabled = True

    # Toggle master audio OFF
    state = sm.toggle_audio()
    assert state is False
    assert sm.enabled is False
    sm.bgm.clip.stop.assert_called_once()

    # Attempt to play SFX while master is off -> ignored
    sm.play("switch")
    mock_sound.clip.play.assert_not_called()


def test_audio_assets_exist():
    """Verify that all expected sound files exist on disk."""
    sounds_dir = Path(__file__).parent.parent / "bloxorz" / "assets" / "sounds"
    for sfx in ["roll", "win", "restart", "click", "merge", "switch", "fall", "undo"]:
        assert (sounds_dir / f"{sfx}.wav").is_file(), f"Missing audio asset: {sfx}.wav"


def test_play_sfx_helper(tmp_path: Path):
    """Verify that play_sfx delegates to SoundManager._instance."""
    from bloxorz.audio import play_sfx
    sm = SoundManager(assets_dir=tmp_path)
    mock_click = MagicMock()
    sm.sounds = {"click": mock_click}
    sm.enabled = True
    sm.sfx_enabled = True

    play_sfx("click")
    mock_click.clip.play.assert_called_once()
