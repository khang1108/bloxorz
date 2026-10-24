"""Procedural minimalist sound generator and audio manager.

Generates sleek, tactile audio samples procedurally using Python's standard
library (wave, math, struct) so no external audio assets or downloads are needed.
"""

import math
import struct
import wave
from pathlib import Path
from typing import Dict, Optional, Any
from bloxorz.config import CONFIG


class SoundManager:
    """Manages audio generation and playback for Bloxorz."""

    def __init__(self, assets_dir: Optional[Path] = None):
        self.enabled: bool = CONFIG.audio.enabled
        if assets_dir is None:
            self.assets_dir = Path(__file__).parent.parent / "assets" / "sounds"
        else:
            self.assets_dir = assets_dir

        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.sounds: Dict[str, Any] = {}
        self._generate_procedural_sounds()

    def _create_wav(self, filename: str, duration: float, sample_rate: int, generator_fn):
        """Helper to synthesize a WAV file from a sample generator function."""
        filepath = self.assets_dir / filename
        if filepath.exists():
            return filepath

        total_samples = int(duration * sample_rate)
        with wave.open(str(filepath), "w") as wav:
            wav.setnchannels(1)       # Mono
            wav.setsampwidth(2)       # 16-bit
            wav.setframerate(sample_rate)

            raw_data = bytearray()
            for i in range(total_samples):
                t = i / sample_rate
                val = generator_fn(t, duration)
                # Clamp to 16-bit signed integer range (-32767 to 32767)
                clamped = max(-1.0, min(1.0, val))
                int_val = int(clamped * 32767.0 * CONFIG.audio.master_headroom)
                raw_data.extend(struct.pack("<h", int_val))

            wav.writeframes(raw_data)
        return filepath

    def _generate_procedural_sounds(self):
        """Synthesizes all minimal tactile sound effects."""
        cfg = CONFIG.audio
        sr = cfg.sample_rate

        # 1. Roll sound: Subtle ceramic/slate wooden tap (70ms)
        def roll_gen(t, d):
            progress = t / d
            envelope = math.exp(-28.0 * progress)
            # Low thud mixed with ceramic crackle
            freq = 140.0 - (progress * 60.0)
            wave_val = math.sin(2.0 * math.pi * freq * t)
            noise = ((math.sin(t * 12345.67) % 1.0) - 0.5) * 0.15
            return (wave_val + noise) * envelope

        # 2. Switch sound: Precision mechanical click (45ms)
        def switch_gen(t, d):
            progress = t / d
            envelope = math.exp(-40.0 * progress)
            tone1 = math.sin(2.0 * math.pi * 920.0 * t)
            tone2 = math.sin(2.0 * math.pi * 1480.0 * t) * 0.5
            return (tone1 + tone2) * envelope

        # 3. Fall sound: Soft low-frequency sinking whoosh (400ms)
        def fall_gen(t, d):
            progress = t / d
            envelope = math.sin(progress * math.pi) * math.exp(-2.5 * progress)
            freq = 220.0 * math.exp(-3.5 * progress)
            return math.sin(2.0 * math.pi * freq * t) * envelope

        # 4. Win sound: Minimal ambient warm chord (600ms)
        def win_gen(t, d):
            progress = t / d
            envelope = math.sin(min(1.0, progress * 4.0) * math.pi * 0.5) * math.exp(-2.2 * progress)
            # C major chord: C5 (523Hz), E5 (659Hz), G5 (784Hz), B5 (987Hz)
            chord = (
                math.sin(2.0 * math.pi * 523.25 * t) * 0.35 +
                math.sin(2.0 * math.pi * 659.25 * t) * 0.28 +
                math.sin(2.0 * math.pi * 783.99 * t) * 0.22 +
                math.sin(2.0 * math.pi * 987.77 * t) * 0.15
            )
            return chord * envelope

        # 5. Undo sound: Delicate rewind pop (40ms)
        def undo_gen(t, d):
            progress = t / d
            envelope = math.exp(-35.0 * progress)
            freq = 300.0 + (progress * 500.0)
            return math.sin(2.0 * math.pi * freq * t) * envelope

        self.roll_file = self._create_wav("roll.wav", cfg.roll_duration, sr, roll_gen)
        self.switch_file = self._create_wav("switch.wav", cfg.switch_duration, sr, switch_gen)
        self.fall_file = self._create_wav("fall.wav", cfg.fall_duration, sr, fall_gen)
        self.win_file = self._create_wav("win.wav", cfg.win_duration, sr, win_gen)
        self.undo_file = self._create_wav("undo.wav", cfg.undo_duration, sr, undo_gen)

    def load_audio_objects(self):
        """Loads Ursina Audio objects once the engine is running."""
        try:
            from ursina import Audio
            self.sounds = {
                "roll": Audio(self.roll_file, autoplay=False, loop=False),
                "switch": Audio(self.switch_file, autoplay=False, loop=False),
                "fall": Audio(self.fall_file, autoplay=False, loop=False),
                "win": Audio(self.win_file, autoplay=False, loop=False),
                "undo": Audio(self.undo_file, autoplay=False, loop=False),
            }
        except Exception:
            # Fallback if audio device is unavailable
            self.sounds = {}

    def play(self, sound_name: str):
        """Plays sound by identifier if audio is enabled."""
        if not self.enabled:
            return
        audio = self.sounds.get(sound_name)
        if audio:
            audio.stop()
            audio.play()

    def toggle_audio(self) -> bool:
        """Toggles audio on/off."""
        self.enabled = not self.enabled
        return self.enabled
