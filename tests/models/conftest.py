from __future__ import annotations

import numpy as np
import pytest

from assistant.config import Settings
from assistant.voice.audio_io import resample, silence, to_int16
from assistant.voice.tts import Synthesizer


@pytest.fixture(scope="session")
def synthesizer() -> Synthesizer:
    settings = Settings(_env_file=None)
    return Synthesizer(settings.models_dir / "kokoro", voice=settings.tts_voice, speed=1.0)


@pytest.fixture(scope="session")
def speak(synthesizer: Synthesizer):
    cache: dict[tuple, np.ndarray] = {}

    def _speak(text: str, voice: str | None = None, lead_s: float = 0.5, tail_s: float = 1.0) -> np.ndarray:
        key = (text, voice, lead_s, tail_s)
        if key not in cache:
            samples, rate = synthesizer.synthesize(text, voice=voice)
            cache[key] = np.concatenate([silence(lead_s), to_int16(resample(samples, rate)), silence(tail_s)])
        return cache[key]

    return _speak
