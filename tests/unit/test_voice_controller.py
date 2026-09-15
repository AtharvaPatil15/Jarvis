import asyncio

import numpy as np
import pytest

from assistant.voice.audio_io import FRAME_SAMPLES, NullSink, WavSource
from assistant.voice.controller import VoiceController
from assistant.voice.vad import SpeechSegmenter

pytestmark = pytest.mark.timeout(60)

WAKE = np.full(FRAME_SAMPLES, 3000, dtype=np.int16)
SPEECH = np.full(FRAME_SAMPLES, 1000, dtype=np.int16)
QUIET = np.zeros(FRAME_SAMPLES, dtype=np.int16)


def audio(*parts: tuple[np.ndarray, int]) -> np.ndarray:
    return np.concatenate([np.concatenate([frame] * count) for frame, count in parts])


class FakeWake:
    def score(self, frame: np.ndarray) -> float:
        return 1.0 if int(frame.max()) == 3000 else 0.0

    def detected(self, frame: np.ndarray) -> bool:
        return self.score(frame) >= 0.5

    def reset(self) -> None:
        pass


def fake_vad(frame: np.ndarray) -> float:
    return 1.0 if np.abs(frame.astype(np.int32)).mean() > 100 else 0.0


class FakeSTT:
    def __init__(self, texts: list[str]) -> None:
        self.texts = list(texts)

    def transcribe(self, utterance: np.ndarray) -> str:
        return self.texts.pop(0) if self.texts else ""


class FakeTTS:
    def __init__(self, seconds: float = 0.3) -> None:
        self.spoken: list[str] = []
        self.seconds = seconds

    def synthesize(self, text: str, voice: str | None = None):
        self.spoken.append(text)
        return np.full(int(24000 * self.seconds), 0.1, dtype=np.float32), 24000


def handler_with(chunks: tuple[str, ...]):
    calls: list[str] = []

    async def handler(text: str, on_delta) -> str:
        calls.append(text)
        for chunk in chunks:
            on_delta(chunk)
        return "".join(chunks)

    return handler, calls


async def run(events, source_audio, stt_texts, chunks=("Sure. ", "Done."), realtime=False, tts_seconds=0.3,
              simulate=False, follow_up_s=6.0):
    handler, calls = handler_with(chunks)
    tts, sink = FakeTTS(tts_seconds), NullSink(simulate_playback=simulate)
    controller = VoiceController(WavSource(source_audio, realtime=realtime, tail_silence_s=0.0), sink, FakeWake(),
                                 SpeechSegmenter(vad=fake_vad), FakeSTT(stt_texts), tts, handler, events,
                                 follow_up_s=follow_up_s, barge_in_ms=300)
    await controller.run(asyncio.Event())
    return calls, tts, sink, controller


async def test_wake_word_then_command_is_answered_and_spoken(events) -> None:
    source = audio((QUIET, 5), (WAKE, 1), (QUIET, 2), (SPEECH, 10), (QUIET, 12))
    calls, tts, sink, _ = await run(events, source, ["what time is it"])
    assert calls == ["what time is it"]
    assert tts.spoken == ["Sure.", "Done."] and len(sink.played) == 2
    types = events.types()
    assert types.index("wake_word_detected") < types.index("user_transcript")
    assert ("state_change", "listening") in events.events


async def test_speech_without_wake_word_is_ignored(events) -> None:
    calls, tts, _, _ = await run(events, audio((SPEECH, 10), (QUIET, 12)), ["should not happen"])
    assert calls == [] and tts.spoken == []


async def test_follow_up_is_accepted_then_the_window_expires(events) -> None:
    source = audio((WAKE, 1), (QUIET, 2), (SPEECH, 10), (QUIET, 12), (SPEECH, 10), (QUIET, 12),
                   (QUIET, 40), (SPEECH, 10), (QUIET, 12))
    calls, _, _, _ = await run(events, source, ["first", "second", "third"], follow_up_s=2.0)
    assert calls == ["first", "second"]
    last_transcript = max(i for i, (t, _) in enumerate(events.events) if t == "user_transcript")
    assert ("state_change", "idle") in events.events[last_transcript:]


async def test_our_own_voice_is_not_treated_as_a_command(events) -> None:
    source = audio((WAKE, 1), (QUIET, 2), (SPEECH, 10), (QUIET, 12), (SPEECH, 10), (QUIET, 12))
    calls, _, _, _ = await run(events, source, ["open youtube", "i have opened youtube for you"],
                               chunks=("I have opened YouTube for you.",))
    assert calls == ["open youtube"]


async def test_barge_in_stops_playback_and_the_interruption_is_handled(events) -> None:
    source = audio((WAKE, 1), (QUIET, 2), (SPEECH, 10), (QUIET, 10), (QUIET, 3), (SPEECH, 10), (QUIET, 12), (QUIET, 5))
    calls, tts, sink, _ = await run(events, source, ["tell me a long story", "stop that"],
                                    chunks=("This is a long answer. ", "It keeps going."),
                                    realtime=True, tts_seconds=3.0, simulate=True)
    assert calls == ["tell me a long story", "stop that"]
    assert sink.stopped == 1
    assert tts.spoken == ["This is a long answer.", "This is a long answer.", "It keeps going."]


async def test_speak_plays_every_sentence(events) -> None:
    handler, _ = handler_with(("x",))
    tts, sink = FakeTTS(0.1), NullSink()
    controller = VoiceController(WavSource(QUIET), sink, FakeWake(), SpeechSegmenter(vad=fake_vad),
                                 FakeSTT([]), tts, handler, events)
    await controller.speak("Hello there. General Kenobi.")
    assert tts.spoken == ["Hello there.", "General Kenobi."] and len(sink.played) == 2
