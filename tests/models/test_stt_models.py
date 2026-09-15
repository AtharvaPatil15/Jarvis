import re
import time

import jiwer
import pytest

from assistant.config import Settings
from assistant.voice.audio_io import SAMPLE_RATE, silence
from assistant.voice.stt import Transcriber

pytestmark = pytest.mark.models

SENTENCES = [
    "Jarvis, what is the weather like in Pune today?",
    "Set a reminder to call my mother this evening.",
    "Open the file called project notes and read me the summary.",
]


@pytest.fixture(scope="module")
def transcriber() -> Transcriber:
    s = Settings(_env_file=None)
    return Transcriber(s.whisper_model, s.whisper_device, download_root=s.models_dir / "whisper")


def normalise(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9' ]", " ", text.lower()).split())


@pytest.mark.parametrize("sentence", SENTENCES)
def test_round_trip_word_error_rate(transcriber, speak, sentence: str) -> None:
    hypothesis = transcriber.transcribe(speak(sentence))
    error = jiwer.wer(normalise(sentence), normalise(hypothesis))
    print(f"device={transcriber.device}/{transcriber.compute_type} wer={error:.3f} hyp={hypothesis!r}")
    assert error <= 0.15


def test_silence_transcribes_to_nothing(transcriber) -> None:
    assert transcriber.transcribe(silence(2.0)) == ""


def test_faster_than_real_time(transcriber, speak) -> None:
    audio = speak(SENTENCES[2])
    start = time.perf_counter()
    transcriber.transcribe(audio)
    factor = (time.perf_counter() - start) / (len(audio) / SAMPLE_RATE)
    print(f"real-time factor {factor:.3f} on {transcriber.device}")
    assert factor < 1.0
