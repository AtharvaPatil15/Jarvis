from types import SimpleNamespace

import numpy as np
import pytest

from assistant.voice.stt import Transcriber


def segment(text: str, no_speech: float = 0.01, logprob: float = -0.2) -> SimpleNamespace:
    return SimpleNamespace(text=text, no_speech_prob=no_speech, avg_logprob=logprob)


class FakeModel:
    instances: list["FakeModel"] = []
    fail_on_load: set[str] = set()
    fail_on_transcribe: set[str] = set()
    segments: list[SimpleNamespace] = []

    def __init__(self, size, device, compute_type, download_root) -> None:
        if device in self.fail_on_load:
            raise RuntimeError(f"{device} load failed")
        self.device, self.compute_type, self.calls = device, compute_type, 0
        FakeModel.instances.append(self)

    def transcribe(self, audio, **kwargs):
        if self.device in self.fail_on_transcribe:
            raise RuntimeError("cublas64_12.dll not found")
        self.calls += 1
        return iter(list(FakeModel.segments)), SimpleNamespace(language="en")


@pytest.fixture(autouse=True)
def reset_fake() -> None:
    FakeModel.instances, FakeModel.fail_on_load, FakeModel.fail_on_transcribe, FakeModel.segments = [], set(), set(), []


def test_auto_prefers_cuda_float16() -> None:
    t = Transcriber(device="auto", model_factory=FakeModel)
    assert (t.device, t.compute_type) == ("cuda", "float16")


def test_auto_falls_back_to_cpu_when_cuda_cannot_load() -> None:
    FakeModel.fail_on_load = {"cuda"}
    t = Transcriber(device="auto", model_factory=FakeModel)
    assert (t.device, t.compute_type) == ("cpu", "int8")


def test_auto_falls_back_to_cpu_when_cuda_fails_at_first_inference() -> None:
    FakeModel.fail_on_transcribe = {"cuda"}
    t = Transcriber(device="auto", model_factory=FakeModel)
    assert (t.device, t.compute_type) == ("cpu", "int8")


def test_forced_cpu_never_tries_cuda() -> None:
    Transcriber(device="cpu", model_factory=FakeModel)
    assert [m.device for m in FakeModel.instances] == ["cpu"]


def test_no_device_available_raises() -> None:
    FakeModel.fail_on_load = {"cuda", "cpu"}
    with pytest.raises(RuntimeError, match="could not load Whisper"):
        Transcriber(device="auto", model_factory=FakeModel)


def test_hallucinated_and_empty_segments_are_dropped() -> None:
    t = Transcriber(device="cpu", model_factory=FakeModel)
    FakeModel.segments = [segment(" What time"), segment(" is it?"), segment(" Thank you.", no_speech=0.9),
                          segment(" um", logprob=-1.6), segment("   ")]
    assert t.transcribe(np.ones(16000, dtype=np.int16)) == "What time is it?"


def test_very_short_audio_is_not_sent_to_the_model() -> None:
    t = Transcriber(device="cpu", model_factory=FakeModel)
    calls_after_warmup = FakeModel.instances[-1].calls
    assert t.transcribe(np.ones(1000, dtype=np.int16)) == ""
    assert FakeModel.instances[-1].calls == calls_after_warmup
