"""Sound and background music audio manager for Bloxorz 3D."""

from pathlib import Path
from typing import Dict, Optional, Any
from bloxorz.config import CONFIG


class SoundManager:
    """Manages audio generation, background music theme, and tactile SFX playback for Bloxorz."""

    _instance: Optional["SoundManager"] = None

    def __init__(self, assets_dir: Optional[Path] = None):
        SoundManager._instance = self
        self.enabled: bool = CONFIG.audio.enabled
        self.bgm_enabled: bool = getattr(CONFIG.audio, "bgm_enabled", True)
        self.bgm_volume: float = getattr(CONFIG.audio, "bgm_volume", 0.50)
        self.sfx_enabled: bool = getattr(CONFIG.audio, "sfx_enabled", True)
        self.sfx_volume: float = getattr(CONFIG.audio, "sfx_volume", 0.80)
        self.theme_track: str = getattr(CONFIG.audio, "theme_track", "background.mp3")

        if assets_dir is None:
            self.assets_dir = Path(__file__).parent.parent / "assets" / "sounds"
        else:
            self.assets_dir = assets_dir

        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.sounds: Dict[str, Any] = {}
        self.bgm: Optional[Any] = None

    def load_audio_objects(self):
        """Loads Ursina Audio objects once the engine is running."""
        try:
            from ursina import Audio
            sfx_names = ["roll", "switch", "fall", "win", "undo", "restart", "click", "merge", "teleport"]
            self.sounds = {}
            for name in sfx_names:
                wav_path = self.assets_dir / f"{name}.wav"
                if wav_path.is_file():
                    self.sounds[name] = Audio(
                        wav_path, autoplay=False, loop=False, volume=self.sfx_volume
                    )

            theme_path = self.assets_dir / self.theme_track

            if theme_path.is_file():
                self.bgm = Audio(theme_path, autoplay=False, loop=True, volume=self.bgm_volume)
                if self.enabled and self.bgm_enabled:
                    self.play_bgm()
        except Exception:
            # Fallback if audio device is unavailable
            self.sounds = {}
            self.bgm = None

    def play_bgm(self):
        """Starts background music playback in a continuous loop."""
        if not self.enabled or not self.bgm_enabled or not self.bgm:
            return
        clip = getattr(self.bgm, "clip", None)
        if clip:
            self.bgm.volume = self.bgm_volume
            is_playing = bool(getattr(self.bgm, "playing", False))
            if not is_playing:
                clip.play()

    def stop_bgm(self):
        """Stops background music without destroying the Audio entity."""
        if self.bgm and getattr(self.bgm, "clip", None):
            self.bgm.clip.stop()

    def pause_bgm(self):
        """Pauses background music playback."""
        self.stop_bgm()

    def resume_bgm(self):
        """Resumes background music playback if music is enabled."""
        if self.enabled and self.bgm_enabled:
            self.play_bgm()

    def set_bgm_volume(self, val: float):
        """Updates BGM volume (clamped between 0.0 and 1.0)."""
        self.bgm_volume = max(0.0, min(1.0, float(val)))
        if self.bgm:
            self.bgm.volume = self.bgm_volume

    def set_sfx_volume(self, val: float):
        """Updates SFX volume (clamped between 0.0 and 1.0) for all sound effects."""
        self.sfx_volume = max(0.0, min(1.0, float(val)))
        for sound in self.sounds.values():
            if sound:
                sound.volume = self.sfx_volume

    def toggle_bgm(self) -> bool:
        """Toggles background music on/off."""
        self.bgm_enabled = not self.bgm_enabled
        if self.bgm_enabled and self.enabled:
            self.play_bgm()
        else:
            self.stop_bgm()
        return self.bgm_enabled

    def toggle_sfx(self) -> bool:
        """Toggles sound effects on/off."""
        self.sfx_enabled = not self.sfx_enabled
        return self.sfx_enabled

    def toggle_audio(self) -> bool:
        """Toggles master audio on/off."""
        self.enabled = not self.enabled
        if self.enabled:
            if self.bgm_enabled:
                self.play_bgm()
        else:
            self.stop_bgm()
        return self.enabled

    def play(self, sound_name: str):
        """Plays sound by identifier if master audio and SFX are enabled."""
        if not self.enabled or not self.sfx_enabled:
            return
        audio = self.sounds.get(sound_name)
        if audio and getattr(audio, "clip", None):
            audio.volume = self.sfx_volume
            audio.clip.stop()
            audio.clip.play()


def play_sfx(sound_name: str):
    """Global convenience helper to play a sound effect if SoundManager is active."""
    if SoundManager._instance is not None:
        SoundManager._instance.play(sound_name)
