import numpy as np
import pytest

from assistant.voice.audio_io import SAMPLE_RATE, chunk_frames, silence
from assistant.voice.vad import SpeechSegmenter

pytestmark = pytest.mark.models


def utterances(segmenter: SpeechSegmenter, audio: np.ndarray) -> list[np.ndarray]:
    return [u for frame in chunk_frames(audio) if (u := segmenter.feed(frame)) is not None]


def test_one_sentence_becomes_one_utterance(speak) -> None:
    audio = speak("Hello Jarvis, how are you doing today?", lead_s=1.0, tail_s=1.5)
    found = utterances(SpeechSegmenter(), audio)
    assert len(found) == 1
    assert 1.2 < len(found[0]) / SAMPLE_RATE < len(audio) / SAMPLE_RATE


def test_two_sentences_with_a_pause_become_two_utterances(speak) -> None:
    audio = np.concatenate([speak("Open my notes.", lead_s=0.5, tail_s=1.2),
                            speak("Then read the first line.", lead_s=0.0, tail_s=1.2)])
    assert len(utterances(SpeechSegmenter(), audio)) == 2


def test_silence_and_quiet_noise_produce_nothing() -> None:
    noise = np.random.default_rng(0).normal(0, 150, SAMPLE_RATE * 4).astype(np.int16)
    assert utterances(SpeechSegmenter(), np.concatenate([silence(3.0), noise])) == []
