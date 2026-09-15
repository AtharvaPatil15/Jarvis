import numpy as np
import pytest

from assistant.config import Settings
from assistant.voice.audio_io import SAMPLE_RATE, chunk_frames, silence
from assistant.voice.wake import WakeWordDetector

pytestmark = pytest.mark.models
VOICES = ["bm_george", "am_michael", "bf_emma", "af_heart"]


@pytest.fixture(scope="module")
def detector() -> WakeWordDetector:
    s = Settings(_env_file=None)
    return WakeWordDetector(s.wake_model, s.wake_threshold)


def max_score(detector: WakeWordDetector, audio: np.ndarray) -> float:
    detector.reset()
    return max(detector.score(frame) for frame in chunk_frames(audio))


def test_silence_and_noise_never_trigger(detector) -> None:
    noise = np.random.default_rng(1).normal(0, 300, SAMPLE_RATE * 10).astype(np.int16)
    assert max_score(detector, np.concatenate([silence(10.0), noise])) < detector.threshold


def test_ordinary_speech_does_not_trigger(detector, speak) -> None:
    for sentence in ["The weather today is sunny and warm.",
                     "Please send the report to my manager by Friday.",
                     "I think the service at that restaurant was excellent."]:
        score = max_score(detector, speak(sentence, lead_s=1.0, tail_s=1.0))
        assert score < detector.threshold, (sentence, score)


def test_hey_jarvis_triggers_for_generated_voices(detector, speak) -> None:
    scores = {v: max_score(detector, speak("Hey Jarvis.", voice=v, lead_s=1.5, tail_s=1.5)) for v in VOICES}
    print(scores)
    assert max(scores.values()) >= detector.threshold
    assert sum(score >= detector.threshold for score in scores.values()) >= 2
