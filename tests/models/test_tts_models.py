import numpy as np
import pytest

pytestmark = pytest.mark.models


def test_configured_british_voice_is_available(synthesizer) -> None:
    assert "bm_george" in synthesizer.voices()


def test_synthesis_produces_audible_speech_of_plausible_length(synthesizer) -> None:
    samples, rate = synthesizer.synthesize("Good evening. All systems are online.")
    assert rate == 24000 and samples.dtype == np.float32 and samples.ndim == 1
    assert 1.0 < len(samples) / rate < 6.0
    assert float(np.max(np.abs(samples))) > 0.05


def test_blank_text_returns_no_audio(synthesizer) -> None:
    samples, _ = synthesizer.synthesize("   ")
    assert len(samples) == 0
