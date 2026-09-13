# Phase 3b — The hands-free voice loop and the switch-over

Order: **P3-T5 → P3-T6**. After P3-T6: full gate, then `git push origin testing`.

---

## P3-T5: Audio sources and sinks, `EchoGuard`, `VoiceController` with streaming speech and barge-in

**Goal:** One asynchronous loop that waits for "Hey Jarvis", captures the command, streams the model's reply to speech
sentence by sentence, keeps listening for follow-ups without the wake word, ignores its own voice, and stops talking
within 300 ms when the user interrupts.

**Depends on:** P3-T2, P3-T3, P3-T4.

**Files:**
- Modify: `assistant/voice/audio_io.py` (add protocols, `WavSource`, `MicSource`, `NullSink`, `SpeakerSink`), `requirements.txt` (add `rapidfuzz`)
- Create: `assistant/voice/echo.py`, `assistant/voice/controller.py`, `scripts/voice_hardware_check.py`,
  `tests/unit/test_audio_sources.py`, `tests/unit/test_echo.py`, `tests/unit/test_voice_controller.py`, `docs/proof/P3-T5.md`

**Interfaces — Produces:** PLAN §3.9 + §3.9a: `AudioSource`, `AudioSink` (Protocols), `WavSource`, `MicSource`,
`NullSink(simulate_playback=False)` with `played`, `stopped`; `SpeakerSink(device=None)`;
`EchoGuard(threshold=80, window_s=8.0, clock=time.monotonic)` (the `clock` parameter is for tests);
`VoiceController(... follow_up_s=6.0, barge_in_ms=300, echo=None)` with `run(stop)` and `speak(text)`.

**Behaviour contract for `VoiceController`**
1. Waiting mode: every frame goes to the wake detector. On detection: reset wake + segmenter, emit `wake_word_detected`,
   then `state_change listening`, and open a follow-up window of `follow_up_s` seconds of **audio time** (frames × 0.08 s).
2. Listening mode: frames go to the segmenter. A completed utterance is transcribed; empty or echo transcripts extend the
   window and are ignored; otherwise emit `user_transcript` and respond.
3. Responding: the handler runs as a task; `on_delta` chunks go through `SentenceBuffer`; each complete sentence is
   synthesized, noted in `EchoGuard`, and played. If the handler never streamed, the returned reply is split and spoken.
   If the handler raises, "Sorry, something went wrong." is spoken.
4. While a sentence plays, frames are read from the same queue and checked with `segmenter.is_speech`; `ceil(barge_in_ms / 80)`
   consecutive speech frames stop the sink, emit `state_change listening`, abandon remaining sentences, and feed those
   frames into the segmenter so the interruption itself is captured.
5. After responding (or after an interruption), listening mode continues with a fresh follow-up window. When the window
   expires while no speech is active: reset the wake detector, emit `state_change idle`, return to waiting mode.
6. The loop ends when `stop` is set or the source is exhausted (after finishing any playback in progress).

- [ ] **Step 1: Install**

Append `rapidfuzz` to `requirements.txt` and install.

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_audio_sources.py`:
```python
import time

import numpy as np
import soundfile

from assistant.voice.audio_io import FRAME_SAMPLES, NullSink, WavSource


def test_wav_source_from_array_adds_lead_and_tail_silence() -> None:
    frames = list(WavSource(np.ones(FRAME_SAMPLES * 2, dtype=np.int16), lead_silence_s=0.16, tail_silence_s=0.08).frames())
    assert len(frames) == 5
    assert not frames[0].any() and frames[2].all() and not frames[4].any()


def test_wav_source_from_file_is_resampled_to_16k(tmp_path) -> None:
    path = tmp_path / "tone.wav"
    soundfile.write(path, np.full(24000, 0.25, dtype=np.float32), 24000)
    frames = list(WavSource(path, tail_silence_s=0.0).frames())
    assert len(frames) == 13 and all(len(f) == FRAME_SAMPLES and f.dtype == np.int16 for f in frames)


def test_realtime_wav_source_paces_frames() -> None:
    start = time.monotonic()
    list(WavSource(np.zeros(FRAME_SAMPLES * 5, dtype=np.int16), realtime=True, tail_silence_s=0.0).frames())
    assert time.monotonic() - start >= 0.35


def test_null_sink_records_and_simulates_playback() -> None:
    sink = NullSink(simulate_playback=True)
    sink.play(np.zeros(4800, dtype=np.float32), 24000)
    assert sink.is_playing and len(sink.played) == 1
    sink.wait()
    assert not sink.is_playing


def test_null_sink_stop_ends_playback_immediately() -> None:
    sink = NullSink(simulate_playback=True)
    sink.play(np.zeros(240000, dtype=np.float32), 24000)
    sink.stop()
    assert not sink.is_playing and sink.stopped == 1
```

`tests/unit/test_echo.py`:
```python
from assistant.voice.echo import EchoGuard


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_hearing_our_own_sentence_is_echo() -> None:
    guard = EchoGuard()
    guard.note_spoken("I have opened YouTube for you.")
    assert guard.is_echo("i have opened youtube for you")
    assert guard.is_echo("have opened YouTube for")


def test_echo_can_span_consecutive_sentences() -> None:
    guard = EchoGuard()
    guard.note_spoken("Sure.")
    guard.note_spoken("It is five o'clock.")
    assert guard.is_echo("sure it is five o'clock")


def test_real_commands_are_not_echo() -> None:
    guard = EchoGuard()
    guard.note_spoken("Done.")
    assert not guard.is_echo("what's the weather in Mumbai")
    assert not guard.is_echo("I'm done with that, now open my notes")
    assert not guard.is_echo("stop")


def test_old_speech_expires_after_the_window() -> None:
    clock = Clock()
    guard = EchoGuard(window_s=8.0, clock=clock)
    guard.note_spoken("I have opened YouTube for you.")
    clock.now += 9.0
    assert not guard.is_echo("i have opened youtube for you")
```

`tests/unit/test_voice_controller.py`:
```python
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
```
Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_audio_sources.py tests/unit/test_echo.py tests/unit/test_voice_controller.py -q`
Expected: FAIL — imports missing.

- [ ] **Step 3: Extend `assistant/voice/audio_io.py`**

Add these imports at the top: `import queue`, `import threading`, `import time`, `from collections.abc import Iterator`,
`from pathlib import Path`, `from typing import Protocol`, `import soundfile`. Append:
```python
class AudioSource(Protocol):
    def frames(self) -> Iterator[np.ndarray]: ...


class AudioSink(Protocol):
    def play(self, samples: np.ndarray, sample_rate: int) -> None: ...
    def stop(self) -> None: ...
    @property
    def is_playing(self) -> bool: ...
    def wait(self) -> None: ...


class WavSource:
    def __init__(self, audio: Path | np.ndarray, realtime: bool = False, lead_silence_s: float = 0.0,
                 tail_silence_s: float = 1.0) -> None:
        if isinstance(audio, (str, Path)):
            data, rate = soundfile.read(str(audio), dtype="float32", always_2d=True)
            samples = to_int16(resample(data[:, 0], rate))
        else:
            samples = to_int16(np.asarray(audio))
        self._samples = np.concatenate([silence(lead_silence_s), samples, silence(tail_silence_s)])
        self._realtime = realtime

    def frames(self) -> Iterator[np.ndarray]:
        deadline = time.monotonic()
        for frame in chunk_frames(self._samples):
            if self._realtime:
                deadline += FRAME_SECONDS
                time.sleep(max(0.0, deadline - time.monotonic()))
            yield frame


class MicSource:
    def __init__(self, device: int | None = None) -> None:
        self.device = device

    def frames(self) -> Iterator[np.ndarray]:
        import sounddevice as sd

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SAMPLES,
                            device=self.device) as stream:
            while True:
                data, _overflowed = stream.read(FRAME_SAMPLES)
                yield data[:, 0].copy()


class NullSink:
    """Records played audio. With simulate_playback, is_playing stays true for the clip's real duration."""

    def __init__(self, simulate_playback: bool = False) -> None:
        self.played: list[np.ndarray] = []
        self.stopped = 0
        self._simulate = simulate_playback
        self._busy_until = 0.0
        self._lock = threading.Lock()

    def play(self, samples: np.ndarray, sample_rate: int) -> None:
        with self._lock:
            self.played.append(np.asarray(samples))
            if self._simulate:
                self._busy_until = max(self._busy_until, time.monotonic()) + len(samples) / sample_rate

    def stop(self) -> None:
        with self._lock:
            self.stopped += 1
            self._busy_until = 0.0

    @property
    def is_playing(self) -> bool:
        return time.monotonic() < self._busy_until

    def wait(self) -> None:
        while self.is_playing:
            time.sleep(0.01)


class SpeakerSink:
    """Plays queued clips on an output device. Hardware only — exercised by scripts/voice_hardware_check.py."""

    def __init__(self, device: int | None = None) -> None:
        import sounddevice as sd

        self._sd = sd
        self._device = device
        self._queue: queue.Queue[tuple[np.ndarray, int, int]] = queue.Queue()
        self._generation = 0
        self._pending = 0
        self._lock = threading.Lock()
        threading.Thread(target=self._worker, name="speaker", daemon=True).start()

    def play(self, samples: np.ndarray, sample_rate: int) -> None:
        with self._lock:
            self._pending += 1
            self._queue.put((to_float32(samples), sample_rate, self._generation))

    def stop(self) -> None:
        with self._lock:
            self._generation += 1
        self._sd.stop()

    @property
    def is_playing(self) -> bool:
        return self._pending > 0

    def wait(self) -> None:
        while self.is_playing:
            time.sleep(0.01)

    def _worker(self) -> None:
        while True:
            samples, rate, generation = self._queue.get()
            try:
                if generation != self._generation:
                    continue
                self._sd.play(samples, rate, device=self._device)
                end = time.monotonic() + len(samples) / rate
                while time.monotonic() < end and generation == self._generation:
                    time.sleep(0.01)
                if generation != self._generation:
                    self._sd.stop()
            finally:
                with self._lock:
                    self._pending -= 1
```

- [ ] **Step 4: Write `assistant/voice/echo.py`**

```python
"""Recognises the assistant's own speech coming back through the microphone."""
from __future__ import annotations

import re
import time
from collections import deque
from collections.abc import Callable

from rapidfuzz import fuzz

MIN_WORDS = 3


def _normalise(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9' ]", " ", text.lower()).split())


class EchoGuard:
    def __init__(self, threshold: int = 80, window_s: float = 8.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.threshold = threshold
        self.window_s = window_s
        self._clock = clock
        self._spoken: deque[tuple[float, str]] = deque()

    def note_spoken(self, text: str) -> None:
        normalised = _normalise(text)
        if normalised:
            self._spoken.append((self._clock(), normalised))

    def is_echo(self, transcript: str) -> bool:
        heard = _normalise(transcript)
        if len(heard.split()) < MIN_WORDS:
            return False
        cutoff = self._clock() - self.window_s
        while self._spoken and self._spoken[0][0] < cutoff:
            self._spoken.popleft()
        spoken = " ".join(text for _, text in self._spoken)
        if not spoken or len(heard) > 1.2 * len(spoken):
            return False
        return fuzz.partial_ratio(heard, spoken) >= self.threshold
```

- [ ] **Step 5: Write `assistant/voice/controller.py`**

```python
"""Hands-free loop: wake word -> utterance -> transcript -> streamed reply spoken aloud, with barge-in."""
from __future__ import annotations

import asyncio
import logging
import math
import threading
from collections.abc import Awaitable, Callable
from typing import Any

import numpy as np

from assistant.events import AssistantState, Emit, EventType
from assistant.voice.audio_io import FRAME_SECONDS, AudioSink, AudioSource
from assistant.voice.echo import EchoGuard
from assistant.voice.tts import SentenceBuffer, split_sentences

log = logging.getLogger("jarvis.voice")

Handler = Callable[[str, Callable[[str], None]], Awaitable[str]]
FAILURE_REPLY = "Sorry, something went wrong."


class VoiceController:
    def __init__(self, source: AudioSource, sink: AudioSink, wake: Any, segmenter: Any, stt: Any, tts: Any,
                 handler: Handler, emit: Emit, follow_up_s: float = 6.0, barge_in_ms: int = 300,
                 echo: EchoGuard | None = None) -> None:
        self._source, self._sink, self._wake, self._segmenter = source, sink, wake, segmenter
        self._stt, self._tts, self._handler, self._emit = stt, tts, handler, emit
        self._follow_up_s = follow_up_s
        self._barge_frames = max(1, math.ceil(barge_in_ms / (FRAME_SECONDS * 1000)))
        self._echo = echo or EchoGuard()
        self._frames: asyncio.Queue[np.ndarray | None] = asyncio.Queue()
        self._listening = False
        self._audio_clock = 0.0
        self._deadline = 0.0

    async def run(self, stop: asyncio.Event) -> None:
        loop = asyncio.get_running_loop()
        self._frames = asyncio.Queue()
        threading.Thread(target=self._read_source, args=(loop, stop), name="voice-source", daemon=True).start()
        self._emit(EventType.STATE_CHANGE, AssistantState.IDLE)
        while True:
            frame = await self._next_frame(stop)
            if frame is None:
                break
            utterance = self._consume(frame)
            if utterance is not None:
                await self._handle_utterance(utterance, stop)

    async def speak(self, text: str) -> None:
        for sentence in split_sentences(text):
            samples, rate = await asyncio.to_thread(self._tts.synthesize, sentence)
            if len(samples):
                self._echo.note_spoken(sentence)
                self._sink.play(samples, rate)
        await asyncio.to_thread(self._sink.wait)

    def _read_source(self, loop: asyncio.AbstractEventLoop, stop: asyncio.Event) -> None:
        try:
            for frame in self._source.frames():
                if stop.is_set():
                    break
                loop.call_soon_threadsafe(self._frames.put_nowait, frame)
        except Exception:
            log.exception("audio source failed")
        finally:
            try:
                loop.call_soon_threadsafe(self._frames.put_nowait, None)
            except RuntimeError:
                pass

    async def _next_frame(self, stop: asyncio.Event) -> np.ndarray | None:
        while not stop.is_set():
            try:
                frame = await asyncio.wait_for(self._frames.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            if frame is not None:
                self._audio_clock += FRAME_SECONDS
            return frame
        return None

    def _open_window(self) -> None:
        self._listening = True
        self._deadline = self._audio_clock + self._follow_up_s
        self._emit(EventType.STATE_CHANGE, AssistantState.LISTENING)

    def _consume(self, frame: np.ndarray) -> np.ndarray | None:
        if not self._listening:
            if self._wake.detected(frame):
                self._wake.reset()
                self._segmenter.reset()
                self._emit(EventType.WAKE_WORD_DETECTED, None)
                self._open_window()
            return None
        utterance = self._segmenter.feed(frame)
        if utterance is None and not self._segmenter.speech_active and self._audio_clock > self._deadline:
            self._listening = False
            self._wake.reset()
            self._emit(EventType.STATE_CHANGE, AssistantState.IDLE)
        return utterance

    async def _handle_utterance(self, utterance: np.ndarray, stop: asyncio.Event) -> None:
        text = (await asyncio.to_thread(self._stt.transcribe, utterance)).strip()
        if not text or self._echo.is_echo(text):
            self._deadline = self._audio_clock + self._follow_up_s
            return
        self._emit(EventType.USER_TRANSCRIPT, text)
        interruption = await self._respond(text, stop)
        self._segmenter.reset()
        self._open_window()
        for frame in interruption or []:
            self._segmenter.feed(frame)

    async def _respond(self, text: str, stop: asyncio.Event) -> list[np.ndarray] | None:
        loop = asyncio.get_running_loop()
        sentences: asyncio.Queue[str | None] = asyncio.Queue()
        buffer = SentenceBuffer()
        streamed = False

        def on_delta(chunk: str) -> None:
            nonlocal streamed
            streamed = True
            for sentence in buffer.push(chunk):
                loop.call_soon_threadsafe(sentences.put_nowait, sentence)

        async def produce() -> None:
            try:
                reply = await self._handler(text, on_delta)
                remainder = buffer.flush() if streamed else split_sentences(reply)
            except Exception:
                log.exception("voice handler failed")
                remainder = [*buffer.flush(), FAILURE_REPLY]
            for sentence in remainder:
                sentences.put_nowait(sentence)
            sentences.put_nowait(None)

        producer = asyncio.create_task(produce())
        try:
            while True:
                sentence = await sentences.get()
                if sentence is None:
                    return None
                samples, rate = await asyncio.to_thread(self._tts.synthesize, sentence)
                if not len(samples):
                    continue
                self._echo.note_spoken(sentence)
                self._sink.play(samples, rate)
                interruption = await self._watch_for_barge_in(stop)
                if interruption is not None:
                    self._sink.stop()
                    self._emit(EventType.STATE_CHANGE, AssistantState.LISTENING)
                    log.info("barge-in after %d speech frames", len(interruption))
                    return interruption
        finally:
            if not producer.done():
                producer.add_done_callback(lambda task: None if task.cancelled() else task.exception())

    async def _watch_for_barge_in(self, stop: asyncio.Event) -> list[np.ndarray] | None:
        run: list[np.ndarray] = []
        while self._sink.is_playing and not stop.is_set():
            try:
                frame = await asyncio.wait_for(self._frames.get(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            if frame is None:
                self._frames.put_nowait(None)
                while self._sink.is_playing and not stop.is_set():
                    await asyncio.sleep(0.02)
                return None
            self._audio_clock += FRAME_SECONDS
            if self._segmenter.is_speech(frame):
                run.append(frame)
                if len(run) >= self._barge_frames:
                    return run
            else:
                run = []
        return None
```
Run the three test files. Expected: `5` + `4` + `6` pass. If a timing-based test is flaky, fix the controller (not the
test's timings) and run it 5 times in a row: `for ($i=0; $i -lt 5; $i++) { .venv/Scripts/python.exe -m pytest tests/unit/test_voice_controller.py -q }`
— paste all five results into the proof.

- [ ] **Step 6: Write the manual hardware check** — `scripts/voice_hardware_check.py` (not part of any gate)

```python
"""Manual check for the owner: records 3 s from the chosen microphone and speaks one sentence."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from assistant.config import get_settings  # noqa: E402
from assistant.voice.audio_io import FRAME_SAMPLES, MicSource, SpeakerSink  # noqa: E402
from assistant.voice.mic_selector import auto_select_best_mic  # noqa: E402
from assistant.voice.tts import Synthesizer  # noqa: E402


def main() -> int:
    settings = get_settings()
    mic = auto_select_best_mic()
    if mic is None:
        print("no microphone found")
        return 1
    print(f"microphone: {mic['name']} (index {mic['index']}) - speak now for 3 seconds")
    frames = []
    for frame in MicSource(mic["index"]).frames():
        frames.append(frame)
        if len(frames) * FRAME_SAMPLES >= 3 * 16000:
            break
    rms = float(np.sqrt(np.mean(np.concatenate(frames).astype(np.float64) ** 2)))
    print(f"recorded RMS level: {rms:.0f} (speech is usually above 300)")
    sink = SpeakerSink()
    samples, rate = Synthesizer(settings.models_dir / "kokoro", settings.tts_voice, settings.tts_speed).synthesize(
        "Audio check complete. I can hear you, and you can hear me.")
    sink.play(samples, rate)
    sink.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
Verify it at least imports: `.venv/Scripts/python.exe -c "import runpy, sys; sys.argv=['x']; import scripts.voice_hardware_check"`.

- [ ] **Step 7: Gate, proof, progress, commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add requirements.txt assistant/voice/audio_io.py assistant/voice/echo.py assistant/voice/controller.py scripts/voice_hardware_check.py tests/unit/test_audio_sources.py tests/unit/test_echo.py tests/unit/test_voice_controller.py docs/proof/P3-T5.md docs/PROGRESS.md
git commit -m "feat(voice): hands-free controller with streaming speech, follow-ups, echo guard and barge-in [P3-T5]" -m "Proof: docs/proof/P3-T5.md"
```

**Acceptance criteria:** all six controller behaviours pass five consecutive runs; the barge-in test shows playback
stopped (`stopped == 1`) and the interruption handled as the next command.

---

## P3-T6: Voice into the server, delete the legacy voice stack, measure latency

**Goal:** The backend starts the new voice loop (wake word → Whisper → agent → Kokoro) on the real microphone and speaker,
typed commands are spoken too, the Porcupine / Google STT / edge-tts / pygame stack and the key setting are gone, and
end-to-end latency is measured with real models and the live LLM.

**Depends on:** P3-T5, P2-T6.

**Files:**
- Create: `assistant/voice/factory.py`, `scripts/voice_latency.py`, `tests/unit/test_server_voice.py`,
  `tests/models/test_voice_pipeline_models.py`, `docs/proof/P3-T6.md`
- Modify: `server.py`, `assistant/config.py` (remove `porcupine_access_key`), `tests/unit/test_config.py` (remove its
  assertion), `tests/unit/test_server_app.py` (delete `test_mark_voice_idle_*` and `test_voice_failure_at_startup_*` —
  replaced by `test_server_voice.py`), `tests/unit/test_legacy_fixes.py` (delete the wake-engine test), `requirements.txt`
  (remove `pvporcupine`, `SpeechRecognition`, `PyAudio`, `edge-tts`, `pygame`), `docs/PLAN.md` §3.1 (remove the
  `porcupine_access_key` line)
- Delete (`git rm`): `assistant/voice/legacy_stt.py`, `assistant/voice/legacy_tts.py`, `assistant/voice/wake_word.py`,
  `assistant/voice/voice_controller.py`, `assistant/voice/conversation_manager.py`, `tests/unit/test_legacy_voice.py`
- Delete from disk (untracked, ignored): `response_*.mp3`

**Interfaces — Produces:** `build_voice_controller(settings, handler, emit, source=None, sink=None) -> VoiceController`;
`app.state.voice_handler(text, on_delta) -> str`; `app.state.voice` is a `VoiceController` or `None`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_server_voice.py`:
```python
import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings
from tests.helpers import receive_until_idle

pytestmark = pytest.mark.timeout(30)


class FakeVoice:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.running = False
        self.stopped = False

    async def run(self, stop) -> None:
        self.running = True
        await stop.wait()
        self.stopped = True

    async def speak(self, text: str) -> None:
        self.spoken.append(text)


def voice_settings() -> Settings:
    return Settings(_env_file=None, llm_backend="fake", voice_enabled=True)


@pytest.fixture
def fake_voice(monkeypatch) -> FakeVoice:
    import assistant.voice.factory as factory

    voice = FakeVoice()
    monkeypatch.setattr(factory, "build_voice_controller", lambda settings, handler, emit: voice)
    return voice


def test_voice_loop_starts_and_stops_with_the_server(fake_voice) -> None:
    with TestClient(server.create_app(voice_settings())) as client:
        assert client.get("/health").json()["voice"] is True
        assert fake_voice.running
    assert fake_voice.stopped


def test_typed_commands_are_spoken_when_voice_is_on(fake_voice) -> None:
    with TestClient(server.create_app(voice_settings())) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "hello"})
        receive_until_idle(ws)
    assert fake_voice.spoken == ["You said: hello"]


def test_voice_handler_streams_through_the_orchestrator(fake_voice) -> None:
    app = server.create_app(voice_settings())
    chunks: list[str] = []
    with TestClient(app) as client:
        reply = client.portal.call(app.state.voice_handler, "hi there", chunks.append)
    assert reply == "You said: hi there"
    assert "".join(chunks) == reply


def test_voice_pipeline_failure_keeps_text_mode_working(monkeypatch) -> None:
    import assistant.voice.factory as factory

    def boom(*args, **kwargs):
        raise RuntimeError("no microphone found")

    monkeypatch.setattr(factory, "build_voice_controller", boom)
    with TestClient(server.create_app(voice_settings())) as client:
        assert client.get("/health").json() == {"status": "ok", "llm": True, "voice": False}
```
Run → FAIL (`assistant.voice.factory` missing).

- [ ] **Step 2: Write `assistant/voice/factory.py`**

```python
"""Assembles the production voice pipeline from Settings."""
from __future__ import annotations

from assistant.config import Settings
from assistant.events import Emit
from assistant.voice.audio_io import AudioSink, AudioSource, MicSource, SpeakerSink
from assistant.voice.controller import Handler, VoiceController
from assistant.voice.stt import Transcriber
from assistant.voice.tts import Synthesizer
from assistant.voice.vad import SpeechSegmenter
from assistant.voice.wake import WakeWordDetector


def build_voice_controller(settings: Settings, handler: Handler, emit: Emit, source: AudioSource | None = None,
                           sink: AudioSink | None = None) -> VoiceController:
    if source is None:
        from assistant.voice.mic_selector import auto_select_best_mic

        mic = auto_select_best_mic()
        if mic is None:
            raise RuntimeError("no microphone found")
        source = MicSource(device=mic["index"])
    return VoiceController(
        source=source,
        sink=sink if sink is not None else SpeakerSink(),
        wake=WakeWordDetector(settings.wake_model, settings.wake_threshold),
        segmenter=SpeechSegmenter(silence_ms=settings.vad_silence_ms),
        stt=Transcriber(settings.whisper_model, settings.whisper_device, download_root=settings.models_dir / "whisper"),
        tts=Synthesizer(settings.models_dir / "kokoro", voice=settings.tts_voice, speed=settings.tts_speed),
        handler=handler,
        emit=emit,
    )
```

- [ ] **Step 3: Update `server.py`**

1. Add `import contextlib` and `from collections.abc import Callable`. Delete `mark_voice_idle` and `on_voice_event`.
2. Move `lock = asyncio.Lock()` above the lifespan definition and add, right after it:
```python
    voice_stop = asyncio.Event()

    async def voice_handler(text: str, on_delta: Callable[[str], None]) -> str:
        async with lock:
            return await runtime.orchestrator.handle(text, on_delta=on_delta)
```
3. Replace the lifespan with:
```python
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        hub.bind_loop(asyncio.get_running_loop())
        voice_task: asyncio.Task[None] | None = None
        if voice_wanted:
            try:
                from assistant.voice.factory import build_voice_controller

                app.state.voice = await asyncio.to_thread(build_voice_controller, settings, voice_handler, hub.emit)
                voice_task = asyncio.create_task(app.state.voice.run(voice_stop))
            except Exception:
                log.exception("voice disabled: voice pipeline failed to start")
                app.state.voice = None
        try:
            yield
        finally:
            voice_stop.set()
            if voice_task is not None:
                with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
                    await asyncio.wait_for(voice_task, timeout=3)
            await hub.close()
```
4. After `app.state.voice = None` add `app.state.voice_handler = voice_handler`.
5. In `process_text`, replace the voice block with:
```python
            voice = app.state.voice
            if voice is not None:
                await voice.speak(reply)
```

- [ ] **Step 4: Delete the legacy stack and prove it is gone**

```powershell
git rm assistant/voice/legacy_stt.py assistant/voice/legacy_tts.py assistant/voice/wake_word.py assistant/voice/voice_controller.py assistant/voice/conversation_manager.py tests/unit/test_legacy_voice.py
Remove-Item response_*.mp3 -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m pip uninstall -y pvporcupine SpeechRecognition PyAudio edge-tts pygame
git grep -nE "pvporcupine|speech_recognition|recognize_google|edge_tts|pygame|porcupine|conv_manager|voice_controller" -- "*.py" "requirements*.txt"
```
Apply the file modifications listed above (config field, tests, requirements, PLAN §3.1). The `git grep` must print
nothing. Run `.venv/Scripts/python.exe -m pytest tests/unit -q` — all pass with the legacy packages uninstalled.

- [ ] **Step 5: Real-model pipeline test** — `tests/models/test_voice_pipeline_models.py`

```python
import asyncio

import numpy as np
import pytest

from assistant.config import Settings
from assistant.voice.audio_io import NullSink, WavSource
from assistant.voice.factory import build_voice_controller

pytestmark = [pytest.mark.models, pytest.mark.timeout(300)]


async def test_wake_word_to_spoken_reply_with_real_models(speak, events) -> None:
    heard: list[str] = []

    async def handler(text: str, on_delta) -> str:
        heard.append(text)
        on_delta("Paris is the capital of France.")
        return "Paris is the capital of France."

    audio = np.concatenate([speak("Hey Jarvis.", lead_s=1.0, tail_s=0.6),
                            speak("What is the capital of France?", lead_s=0.0, tail_s=2.0)])
    sink = NullSink()
    controller = build_voice_controller(Settings(_env_file=None), handler, events, source=WavSource(audio), sink=sink)
    await controller.run(asyncio.Event())
    assert len(heard) == 1 and "capital of france" in heard[0].lower()
    assert len(sink.played) == 1
    types = events.types()
    assert types.index("wake_word_detected") < types.index("user_transcript")
```
Run: `.venv/Scripts/python.exe -m pytest tests/models/test_voice_pipeline_models.py -q` → `1 passed`.

- [ ] **Step 6: Latency measurement** — `scripts/voice_latency.py`

```python
"""Real-model voice latency with the live LLM: end of speech -> transcript -> first audio played.

Usage: .venv/Scripts/python.exe scripts/voice_latency.py [runs]
Exits 1 if the median time from end of speech to first audio exceeds 5.0 s (target: 3.0 s).
"""
from __future__ import annotations

import asyncio
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from assistant.config import get_settings  # noqa: E402
from assistant.runtime import build_runtime  # noqa: E402
from assistant.safety.permissions import DenyAllGate  # noqa: E402
from assistant.voice.audio_io import NullSink, WavSource, resample, silence, to_int16  # noqa: E402
from assistant.voice.controller import VoiceController  # noqa: E402
from assistant.voice.stt import Transcriber  # noqa: E402
from assistant.voice.tts import Synthesizer  # noqa: E402
from assistant.voice.vad import SpeechSegmenter  # noqa: E402
from assistant.voice.wake import WakeWordDetector  # noqa: E402

LIMIT_S = 5.0


class TimedSink(NullSink):
    def __init__(self) -> None:
        super().__init__()
        self.first_play: float | None = None

    def play(self, samples: np.ndarray, sample_rate: int) -> None:
        if self.first_play is None:
            self.first_play = time.perf_counter()
        super().play(samples, sample_rate)


class TimedSegmenter(SpeechSegmenter):
    ended: float | None = None

    def feed(self, frame: np.ndarray) -> np.ndarray | None:
        utterance = super().feed(frame)
        if utterance is not None and self.ended is None:
            self.ended = time.perf_counter()
        return utterance


def spoken(tts: Synthesizer, text: str) -> np.ndarray:
    samples, rate = tts.synthesize(text)
    return to_int16(resample(samples, rate))


async def main(runs: int) -> int:
    settings = get_settings()
    stt = Transcriber(settings.whisper_model, settings.whisper_device, download_root=settings.models_dir / "whisper")
    tts = Synthesizer(settings.models_dir / "kokoro", settings.tts_voice, settings.tts_speed)
    wake = WakeWordDetector(settings.wake_model, settings.wake_threshold)
    audio = np.concatenate([silence(1.0), spoken(tts, "Hey Jarvis."), silence(0.6),
                            spoken(tts, "What is the capital of France?"), silence(8.0)])
    first_audio, transcription = [], []
    print(f"whisper device: {stt.device}/{stt.compute_type}")
    for index in range(runs):
        marks: dict[str, float] = {}

        def emit(type_: str, payload: object) -> None:
            if str(type_) == "user_transcript":
                marks.setdefault("transcript", time.perf_counter())

        runtime = build_runtime(settings, emit=lambda t, p: None, gate=DenyAllGate())
        sink, segmenter = TimedSink(), TimedSegmenter(silence_ms=settings.vad_silence_ms)
        wake.reset()
        controller = VoiceController(WavSource(audio, realtime=True, tail_silence_s=0.0), sink, wake, segmenter,
                                     stt, tts, runtime.orchestrator.handle, emit)
        await controller.run(asyncio.Event())
        if segmenter.ended is None or "transcript" not in marks or sink.first_play is None:
            print(f"run {index + 1}: incomplete (ended={segmenter.ended}, marks={marks}, played={sink.first_play})")
            return 1
        transcription.append(marks["transcript"] - segmenter.ended)
        first_audio.append(sink.first_play - segmenter.ended)
        print(f"run {index + 1}: transcript {transcription[-1]:.2f} s, first audio {first_audio[-1]:.2f} s")
    median = statistics.median(first_audio)
    print(f"median transcript {statistics.median(transcription):.2f} s, median first audio {median:.2f} s "
          f"(limit {LIMIT_S} s, target 3.0 s)")
    return 0 if median <= LIMIT_S else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)))
```
```powershell
.venv/Scripts/python.exe scripts/ensure_ollama.py --no-pull
.venv/Scripts/python.exe scripts/voice_latency.py 3; echo "exit=$LASTEXITCODE"
```
Expected: three runs and a median line; `exit=0`. If the median exceeds 5 s, profile (Whisper device, `think:false`,
`max_tokens`) and fix; never raise `LIMIT_S`.

- [ ] **Step 7: Real server with voice on (no hardware assertions)**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Start -TimeoutSec 300
Get-Content docs/proof/tmp/backend.err.log -Tail 40
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Stop
```
Expected: `/health` answered. Paste the log lines showing which Whisper device loaded and the microphone chosen (or the
logged reason voice was disabled, e.g. no input device). Either outcome is acceptable here; hardware is verified by the
owner with `scripts/voice_hardware_check.py`.

- [ ] **Step 8: Gates, proof, commit, push (end of phase)**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add server.py requirements.txt assistant/config.py assistant/voice/factory.py scripts/voice_latency.py tests/unit/test_server_voice.py tests/unit/test_server_app.py tests/unit/test_config.py tests/unit/test_legacy_fixes.py tests/models/test_voice_pipeline_models.py docs/PLAN.md docs/proof/P3-T6.md docs/PROGRESS.md docs/DECISIONS.md
git status --short
git commit -m "feat(voice): run the local voice pipeline in the server and remove the legacy voice stack [P3-T6]" -m "Proof: docs/proof/P3-T6.md"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1
git push origin testing
```

**Acceptance criteria**
- No Porcupine, Google STT, edge-tts or pygame code or dependency remains; unit suite passes with them uninstalled.
- Real-model pipeline test passes; latency script exits 0 and the proof records the medians and Whisper device.
- A voice start-up failure never prevents the text path from working.
