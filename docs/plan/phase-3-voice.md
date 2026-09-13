# Phase 3a — Local voice building blocks: TTS, STT, VAD, wake word

Order: **P3-T1 → P3-T2 → P3-T3 → P3-T4**, then continue with `docs/plan/phase-3-controller.md` (P3-T5 → P3-T6).
None of these tests touch a microphone or speaker: speech is generated with Kokoro at test time.

---

## P3-T1: Model downloader, `Synthesizer` (Kokoro), sentence splitting, audio utilities

**Goal:** Offline British-male TTS that returns audio arrays, a sentence splitter/buffer that lets speech start before the
LLM finishes, audio conversion helpers, and a downloader that fetches every speech model without manual steps.

**Depends on:** P0-T2, P0-T4.

**Files:**
- Rename (with `git mv`): `assistant/voice/stt.py` → `assistant/voice/legacy_stt.py`, `assistant/voice/tts.py` → `assistant/voice/legacy_tts.py`
- Modify: `assistant/voice/voice_controller.py` (imports `.legacy_stt` / `.legacy_tts`), `tests/unit/test_legacy_voice.py`
  (stub `assistant.voice.legacy_stt` / `assistant.voice.legacy_tts`), `requirements.txt` (add `kokoro-onnx`, `soundfile`, `scipy`)
- Create: `scripts/download_models.py`, `assistant/voice/audio_io.py`, `assistant/voice/tts.py`,
  `tests/unit/test_audio_utils.py`, `tests/unit/test_tts_text.py`, `tests/models/__init__.py`, `tests/models/conftest.py`,
  `tests/models/test_tts_models.py`, `docs/proof/P3-T1.md`

**Interfaces — Produces:** `SAMPLE_RATE`, `FRAME_SAMPLES`, `FRAME_SECONDS`, `resample`, `to_int16`, `to_float32`,
`chunk_frames`, `silence` (audio_io); `split_sentences`, `SentenceBuffer`, `Synthesizer(model_dir, voice="bm_george",
speed=1.1)` with `voices()` and `synthesize(text, voice=None)`, constants `KOKORO_SAMPLE_RATE = 24000`; pytest fixtures
`synthesizer` (session) and `speak(text, voice=None, lead_s=0.5, tail_s=1.0) -> np.ndarray` (int16, 16 kHz) in `tests/models/conftest.py`.

- [ ] **Step 1: Free the module names used by the new stack**

```powershell
git mv assistant/voice/stt.py assistant/voice/legacy_stt.py
git mv assistant/voice/tts.py assistant/voice/legacy_tts.py
```
In `assistant/voice/voice_controller.py` change `from .stt import SpeechToText` → `from .legacy_stt import SpeechToText`
and `from .tts import TextToSpeech` → `from .legacy_tts import TextToSpeech`. In `tests/unit/test_legacy_voice.py` change
the stub module names to `assistant.voice.legacy_stt` and `assistant.voice.legacy_tts`. Run
`.venv/Scripts/python.exe -m pytest tests/unit -q` — everything must still pass.

- [ ] **Step 2: Install dependencies**

Append to `requirements.txt`:
```text
kokoro-onnx
soundfile
scipy
```
Run `.venv/Scripts/python.exe -m pip install -r requirements.txt`.

- [ ] **Step 3: Write the failing unit tests**

`tests/unit/test_audio_utils.py`:
```python
import numpy as np

from assistant.voice.audio_io import FRAME_SAMPLES, SAMPLE_RATE, chunk_frames, resample, silence, to_float32, to_int16


def test_resample_24k_to_16k_keeps_duration() -> None:
    t = np.arange(24000) / 24000
    out = resample(np.sin(2 * np.pi * 440 * t).astype(np.float32), 24000)
    assert len(out) == 16000 and out.dtype == np.float32


def test_int16_float32_conversions() -> None:
    assert to_int16(np.array([2.0, -2.0, 0.5], dtype=np.float32)).tolist() == [32767, -32767, 16383]
    assert to_float32(np.array([16384], dtype=np.int16)).tolist() == [0.5]
    same = np.array([1, 2], dtype=np.int16)
    assert to_int16(same) is same


def test_chunk_frames_pads_the_last_frame() -> None:
    frames = chunk_frames(np.ones(3000, dtype=np.int16))
    assert [len(f) for f in frames] == [FRAME_SAMPLES] * 3
    assert not frames[2][440:].any()


def test_silence_length() -> None:
    assert len(silence(0.5)) == SAMPLE_RATE // 2
```

`tests/unit/test_tts_text.py`:
```python
import pytest

from assistant.voice.tts import SentenceBuffer, Synthesizer, split_sentences


@pytest.mark.parametrize(("text", "expected"), [
    ("Hello there. How are you? Fine!", ["Hello there.", "How are you?", "Fine!"]),
    ("It costs 3.5 dollars. OK.", ["It costs 3.5 dollars.", "OK."]),
    ("Dr. Smith is here. Mr. Jones too.", ["Dr. Smith is here.", "Mr. Jones too."]),
    ("Use a tool, e.g. the calculator. Then answer.", ["Use a tool, e.g. the calculator.", "Then answer."]),
    ("Line one\nLine two", ["Line one", "Line two"]),
    ("no punctuation at all", ["no punctuation at all"]),
    ("   ", []),
])
def test_split_sentences(text: str, expected: list[str]) -> None:
    assert split_sentences(text) == expected


def test_sentence_buffer_releases_only_complete_sentences() -> None:
    buffer = SentenceBuffer()
    assert buffer.push("Hello the") == []
    assert buffer.push("re. How ") == ["Hello there."]
    assert buffer.push("are you?") == []
    assert buffer.flush() == ["How are you?"]
    assert buffer.flush() == []


def test_sentence_buffer_does_not_split_decimals_across_chunks() -> None:
    buffer = SentenceBuffer()
    assert buffer.push("It is 3.") == []
    assert buffer.push("5 degrees. Nice") == ["It is 3.5 degrees."]
    assert buffer.flush() == ["Nice"]


def test_synthesizer_reports_missing_model_files(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="download_models.py"):
        Synthesizer(tmp_path)
```
Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_audio_utils.py tests/unit/test_tts_text.py -q`
Expected: FAIL — modules not found.

- [ ] **Step 4: Write `assistant/voice/audio_io.py` (utilities; sources and sinks are added in P3-T5)**

```python
"""Audio format helpers. Internal format: 16 kHz mono int16, frames of 1280 samples (80 ms)."""
from __future__ import annotations

import math

import numpy as np
from scipy.signal import resample_poly

SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280
FRAME_SECONDS = FRAME_SAMPLES / SAMPLE_RATE


def resample(samples: np.ndarray, src_rate: int, dst_rate: int = SAMPLE_RATE) -> np.ndarray:
    samples = np.asarray(samples)
    if src_rate == dst_rate:
        return samples
    divisor = math.gcd(src_rate, dst_rate)
    return resample_poly(samples.astype(np.float32), dst_rate // divisor, src_rate // divisor).astype(np.float32)


def to_float32(samples: np.ndarray) -> np.ndarray:
    array = np.asarray(samples)
    if array.dtype == np.int16:
        return array.astype(np.float32) / 32768.0
    return array.astype(np.float32)


def to_int16(samples: np.ndarray) -> np.ndarray:
    array = np.asarray(samples)
    if array.dtype == np.int16:
        return array
    return (np.clip(array, -1.0, 1.0) * 32767.0).astype(np.int16)


def chunk_frames(samples: np.ndarray, frame_samples: int = FRAME_SAMPLES) -> list[np.ndarray]:
    array = to_int16(samples)
    remainder = len(array) % frame_samples
    if remainder:
        array = np.concatenate([array, np.zeros(frame_samples - remainder, dtype=np.int16)])
    return [array[i:i + frame_samples] for i in range(0, len(array), frame_samples)]


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(round(seconds * SAMPLE_RATE)), dtype=np.int16)
```

- [ ] **Step 5: Write `assistant/voice/tts.py`**

```python
"""Kokoro text-to-speech (local ONNX) plus sentence splitting for streaming speech."""
from __future__ import annotations

import re
import threading
from pathlib import Path

import numpy as np

MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"
KOKORO_SAMPLE_RATE = 24000

_BOUNDARY = re.compile(r"[.!?]+[\"')\]]*(?=\s|$)")
_ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "approx"}


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for line in text.splitlines():
        start = 0
        for match in _BOUNDARY.finditer(line):
            words = line[start:match.start()].split()
            last = words[-1].lower() if words else ""
            if match.group().startswith(".") and (last in _ABBREVIATIONS or (len(last) == 1 and last.isalpha())):
                continue
            piece = line[start:match.end()].strip()
            if piece:
                sentences.append(piece)
            start = match.end()
        tail = line[start:].strip()
        if tail:
            sentences.append(tail)
    return sentences


class SentenceBuffer:
    """Accumulates streamed text; releases sentences once a following sentence has started."""

    def __init__(self) -> None:
        self._text = ""

    def push(self, delta: str) -> list[str]:
        self._text += delta
        sentences = split_sentences(self._text)
        if len(sentences) <= 1:
            return []
        self._text = self._text[self._text.rfind(sentences[-1]):]
        return sentences[:-1]

    def flush(self) -> list[str]:
        rest = split_sentences(self._text)
        self._text = ""
        return rest


class Synthesizer:
    def __init__(self, model_dir: Path, voice: str = "bm_george", speed: float = 1.1) -> None:
        model_path, voices_path = Path(model_dir) / MODEL_FILE, Path(model_dir) / VOICES_FILE
        missing = [str(p) for p in (model_path, voices_path) if not p.is_file()]
        if missing:
            raise FileNotFoundError(
                f"Kokoro model files missing: {missing}. "
                "Run: .venv/Scripts/python.exe scripts/download_models.py --kokoro"
            )
        from kokoro_onnx import Kokoro

        self._kokoro = Kokoro(str(model_path), str(voices_path))
        self._lock = threading.Lock()
        self.voice = voice
        self.speed = speed

    def voices(self) -> list[str]:
        return sorted(self._kokoro.get_voices())

    def synthesize(self, text: str, voice: str | None = None) -> tuple[np.ndarray, int]:
        text = text.strip()
        if not text:
            return np.zeros(0, dtype=np.float32), KOKORO_SAMPLE_RATE
        chosen = voice or self.voice
        lang = "en-gb" if chosen.startswith("b") else "en-us"
        with self._lock:
            samples, rate = self._kokoro.create(text, voice=chosen, speed=self.speed, lang=lang)
        return np.asarray(samples, dtype=np.float32).reshape(-1), int(rate)
```
If `kokoro_onnx.Kokoro` has a different method name for listing voices or creating audio in the installed version,
inspect it (`.venv/Scripts/python.exe -c "import kokoro_onnx, inspect; print(inspect.getsource(kokoro_onnx.Kokoro))"`),
adapt only the calls inside `Synthesizer`, and record it in `docs/DECISIONS.md`.

Run the unit tests. Expected: `4` audio + `10` TTS-text tests pass.

- [ ] **Step 6: Write `scripts/download_models.py`**

```python
"""Download local speech models: Kokoro TTS and Whisper STT into models/, openWakeWord into its package folder.

Usage: .venv/Scripts/python.exe scripts/download_models.py [--kokoro] [--whisper] [--wake]   (no flags = all)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assistant.config import get_settings  # noqa: E402

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
KOKORO_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"present  {target} ({target.stat().st_size} bytes)", flush=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(30.0, read=600.0)) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes(1 << 20):
                handle.write(chunk)
    partial.replace(target)
    print(f"download {target} ({target.stat().st_size} bytes)", flush=True)


def kokoro(models_dir: Path) -> None:
    for name in KOKORO_FILES:
        path = models_dir / "kokoro" / name
        download(f"{KOKORO_BASE}/{name}", path)
        print(f"sha256   {name} {sha256(path)}", flush=True)


def whisper(models_dir: Path, size: str) -> None:
    from faster_whisper import download_model

    print(f"whisper  {size} -> {download_model(size, cache_dir=str(models_dir / 'whisper'))}", flush=True)


def wake() -> None:
    import openwakeword.utils

    openwakeword.utils.download_models()
    print("openwakeword pre-trained models downloaded", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for flag in ("kokoro", "whisper", "wake"):
        parser.add_argument(f"--{flag}", action="store_true")
    args = parser.parse_args(argv)
    settings = get_settings()
    models_dir = settings.models_dir if settings.models_dir.is_absolute() else ROOT / settings.models_dir
    selected = [name for name in ("kokoro", "whisper", "wake") if getattr(args, name)] or ["kokoro", "whisper", "wake"]
    if "kokoro" in selected:
        kokoro(models_dir)
    if "whisper" in selected:
        whisper(models_dir, settings.whisper_model)
    if "wake" in selected:
        wake()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
Run: `.venv/Scripts/python.exe scripts/download_models.py --kokoro`
Expected: two `download` lines (≈ 310 MB and ≈ 27 MB) and two `sha256` lines. A second run prints `present` for both.

- [ ] **Step 7: Model-backed tests and shared speech fixture**

`tests/models/conftest.py` (also create empty `tests/models/__init__.py`):
```python
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
```

`tests/models/test_tts_models.py`:
```python
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
```
Run: `.venv/Scripts/python.exe -m pytest tests/models/test_tts_models.py -q` → `3 passed`.

- [ ] **Step 8: Gate, proof, progress, commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add requirements.txt scripts/download_models.py assistant/voice tests/unit/test_audio_utils.py tests/unit/test_tts_text.py tests/unit/test_legacy_voice.py tests/models docs/proof/P3-T1.md docs/PROGRESS.md
git diff --cached --name-only
git commit -m "feat(voice): Kokoro synthesizer, sentence streaming and model downloader [P3-T1]" -m "Proof: docs/proof/P3-T1.md"
```
`git diff --cached --name-only` must not list anything under `models/`.

**Acceptance criteria:** Kokoro speaks with `bm_george` offline; decimals and abbreviations never split a sentence.

---

## P3-T2: `Transcriber` (faster-whisper) with automatic CPU fallback, and the TTS→STT round trip

**Goal:** Local speech recognition that uses the RTX 5060 when CUDA works and silently falls back to CPU when it does not,
filters Whisper's silence hallucinations, and proves accuracy on generated speech.

**Depends on:** P3-T1.

**Files:**
- Modify: `requirements.txt` (add `faster-whisper`, `jiwer`)
- Create: `assistant/voice/stt.py`, `tests/unit/test_transcriber.py`, `tests/models/test_stt_models.py`, `docs/proof/P3-T2.md`

**Interfaces — Produces:** `Transcriber` (PLAN §3.9 + §3.9a) with attributes `device`, `compute_type`; module constants
`NO_SPEECH_MAX = 0.5`, `LOGPROB_MIN = -1.0`, `MIN_AUDIO_S = 0.3`.

- [ ] **Step 1: Install**

Append `faster-whisper` and `jiwer` to `requirements.txt`; install. Then try the optional GPU libraries (large download; a
failure here is acceptable because the CPU fallback is mandatory):
```powershell
.venv/Scripts/python.exe -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
.venv/Scripts/python.exe scripts/download_models.py --whisper
```
Record in the proof whether the GPU libraries installed. Do not add them to `requirements.txt`.

- [ ] **Step 2: Write the failing unit tests** — `tests/unit/test_transcriber.py`

```python
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
```
Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_transcriber.py -q` → FAIL (no `Transcriber`).

- [ ] **Step 3: Write `assistant/voice/stt.py`**

```python
"""Local speech-to-text with faster-whisper. CUDA float16 when it works, CPU int8 otherwise."""
from __future__ import annotations

import logging
import os
import sys
import sysconfig
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from assistant.voice.audio_io import SAMPLE_RATE, to_float32

log = logging.getLogger("jarvis.stt")

NO_SPEECH_MAX = 0.5
LOGPROB_MIN = -1.0
MIN_AUDIO_S = 0.3


def _default_factory(size: str, device: str, compute_type: str, download_root: str | None) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(size, device=device, compute_type=compute_type, download_root=download_root)


def _add_nvidia_dll_dirs() -> None:
    if sys.platform != "win32":
        return
    base = Path(sysconfig.get_paths()["purelib"]) / "nvidia"
    for bin_dir in base.glob("*/bin"):
        os.add_dll_directory(str(bin_dir))
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"


class Transcriber:
    def __init__(self, model_size: str = "small.en", device: str = "auto", download_root: Path | None = None,
                 model_factory: Callable[..., Any] | None = None) -> None:
        factory = model_factory or _default_factory
        root = str(download_root) if download_root else None
        attempts = [("cuda", "float16"), ("cpu", "int8")] if device == "auto" else \
            [(device, "float16" if device == "cuda" else "int8")]
        last_error: Exception | None = None
        for candidate_device, compute_type in attempts:
            try:
                if candidate_device == "cuda" and model_factory is None:
                    _add_nvidia_dll_dirs()
                model = factory(model_size, device=candidate_device, compute_type=compute_type, download_root=root)
                segments, _ = model.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language="en", beam_size=1)
                list(segments)
            except Exception as exc:
                log.warning("Whisper unavailable on %s/%s: %s", candidate_device, compute_type, exc)
                last_error = exc
                continue
            self._model = model
            self.device = candidate_device
            self.compute_type = compute_type
            log.info("Whisper %s ready on %s (%s)", model_size, candidate_device, compute_type)
            return
        raise RuntimeError(f"could not load Whisper model {model_size}: {last_error}")

    def transcribe(self, audio: np.ndarray) -> str:
        samples = to_float32(audio)
        if len(samples) < int(MIN_AUDIO_S * SAMPLE_RATE):
            return ""
        segments, _ = self._model.transcribe(samples, language="en", beam_size=1, condition_on_previous_text=False,
                                             vad_filter=False, without_timestamps=True)
        kept = [
            s.text.strip() for s in segments
            if s.text.strip() and s.no_speech_prob < NO_SPEECH_MAX and s.avg_logprob >= LOGPROB_MIN
        ]
        return " ".join(kept).strip()
```
Run the unit tests → `7 passed`.

- [ ] **Step 4: Round-trip accuracy test** — `tests/models/test_stt_models.py`

```python
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
```
Run: `.venv/Scripts/python.exe -m pytest tests/models/test_stt_models.py -q -s` → `5 passed`; keep the printed device,
WER and real-time factor lines for the proof. If WER fails on CPU with `small.en`, do not change the threshold: try
`beam_size=5` in `transcribe`, then `JARVIS_WHISPER_MODEL=medium.en` via Settings default, and record the decision.

- [ ] **Step 5: Gate, proof, progress, commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add requirements.txt assistant/voice/stt.py tests/unit/test_transcriber.py tests/models/test_stt_models.py docs/proof/P3-T2.md docs/PROGRESS.md
git commit -m "feat(voice): local Whisper transcriber with GPU-to-CPU fallback [P3-T2]" -m "Proof: docs/proof/P3-T2.md"
```

**Acceptance criteria:** WER ≤ 0.15 on all three sentences; silence yields `""`; proof states the device actually used.

---

## P3-T3: `SpeechSegmenter` with Silero VAD

**Goal:** Decide when the user started and stopped talking (600 ms of silence ends an utterance), ignore clicks and
noise, keep a little audio before speech onset, and cap runaway utterances.

**Depends on:** P3-T1.

**Files:**
- Modify: `requirements.txt` (add `pysilero-vad`)
- Create: `assistant/voice/vad.py`, `tests/unit/test_segmenter.py`, `tests/models/test_vad_models.py`, `docs/proof/P3-T3.md`

**Interfaces — Produces:** `SileroFrameVAD`, `SpeechSegmenter` (PLAN §3.9 + §3.9a), constant `FRAME_MS = 80`.

- [ ] **Step 1: Install and confirm the pysilero-vad API**

Append `pysilero-vad` to `requirements.txt`; install; then run:
```powershell
.venv/Scripts/python.exe -c "import pysilero_vad, inspect; print(inspect.getsource(pysilero_vad.SileroVoiceActivityDetector))"
```
The adapter below assumes `SileroVoiceActivityDetector()` is callable with 16 kHz int16 mono **bytes** of exactly
`chunk_samples()` samples and returns a probability. If the installed version differs, change only `SileroFrameVAD` and
record it in `docs/DECISIONS.md`.

- [ ] **Step 2: Write the failing unit tests** — `tests/unit/test_segmenter.py`

```python
import numpy as np

from assistant.voice.vad import SpeechSegmenter

SPEECH = np.full(1280, 1000, dtype=np.int16)
QUIET = np.zeros(1280, dtype=np.int16)


def fake_vad(frame: np.ndarray) -> float:
    return 1.0 if np.abs(frame.astype(np.int32)).mean() > 100 else 0.0


def run(segmenter: SpeechSegmenter, frames: list[np.ndarray]) -> list[tuple[int, np.ndarray]]:
    results = []
    for index, frame in enumerate(frames):
        utterance = segmenter.feed(frame)
        if utterance is not None:
            results.append((index, utterance))
    return results


def test_utterance_is_emitted_after_enough_silence_and_includes_pre_roll() -> None:
    segmenter = SpeechSegmenter(silence_ms=600, min_speech_ms=250, vad=fake_vad, pre_roll_ms=240)
    results = run(segmenter, [QUIET] * 5 + [SPEECH] * 10 + [QUIET] * 11)
    assert len(results) == 1
    index, utterance = results[0]
    assert index == 22
    assert len(utterance) == (3 + 10 + 8) * 1280
    assert utterance.dtype == np.int16


def test_short_blips_are_ignored() -> None:
    assert run(SpeechSegmenter(vad=fake_vad), [SPEECH] * 2 + [QUIET] * 12) == []


def test_max_utterance_length_forces_a_cut() -> None:
    results = run(SpeechSegmenter(max_utterance_s=1.0, vad=fake_vad), [SPEECH] * 30)
    assert [index for index, _ in results] == [11, 23]
    assert all(len(u) == 12 * 1280 for _, u in results)


def test_speech_active_and_reset() -> None:
    segmenter = SpeechSegmenter(vad=fake_vad)
    assert segmenter.speech_active is False
    segmenter.feed(SPEECH)
    assert segmenter.speech_active is True
    segmenter.reset()
    assert segmenter.speech_active is False


def test_threshold_controls_is_speech() -> None:
    assert SpeechSegmenter(vad=lambda f: 0.4, threshold=0.5).is_speech(QUIET) is False
    assert SpeechSegmenter(vad=lambda f: 0.4, threshold=0.3).is_speech(QUIET) is True
```
Run → FAIL (module missing).

- [ ] **Step 3: Write `assistant/voice/vad.py`**

```python
"""Voice activity detection (Silero) and utterance segmentation over 80 ms frames."""
from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable

import numpy as np

from assistant.voice.audio_io import FRAME_SAMPLES, SAMPLE_RATE, to_int16

FRAME_MS = FRAME_SAMPLES * 1000 // SAMPLE_RATE


class SileroFrameVAD:
    """Speech probability for one 1280-sample frame, evaluated in Silero's native 512-sample chunks."""

    def __init__(self) -> None:
        from pysilero_vad import SileroVoiceActivityDetector

        self._detector = SileroVoiceActivityDetector()
        chunk = getattr(self._detector, "chunk_samples", None)
        self._chunk = int(chunk()) if callable(chunk) else 512
        self._pending = np.zeros(0, dtype=np.int16)

    def __call__(self, frame: np.ndarray) -> float:
        audio = np.concatenate([self._pending, to_int16(frame)])
        best, offset = 0.0, 0
        while offset + self._chunk <= len(audio):
            best = max(best, float(self._detector(audio[offset:offset + self._chunk].tobytes())))
            offset += self._chunk
        self._pending = audio[offset:]
        return best

    def reset(self) -> None:
        self._pending = np.zeros(0, dtype=np.int16)
        reset = getattr(self._detector, "reset", None)
        if callable(reset):
            reset()


class SpeechSegmenter:
    def __init__(self, silence_ms: int = 600, min_speech_ms: int = 250, max_utterance_s: float = 15.0,
                 threshold: float = 0.5, vad: Callable[[np.ndarray], float] | None = None,
                 pre_roll_ms: int = 240) -> None:
        self._vad = vad if vad is not None else SileroFrameVAD()
        self.threshold = threshold
        self._silence_needed = math.ceil(silence_ms / FRAME_MS)
        self._min_speech = math.ceil(min_speech_ms / FRAME_MS)
        self._max_frames = int(max_utterance_s * 1000 / FRAME_MS)
        self._pre_roll: deque[np.ndarray] = deque(maxlen=math.ceil(pre_roll_ms / FRAME_MS))
        self.reset()

    def is_speech(self, frame: np.ndarray) -> bool:
        return self._vad(frame) >= self.threshold

    @property
    def speech_active(self) -> bool:
        return self._active

    def reset(self) -> None:
        self._active = False
        self._frames: list[np.ndarray] = []
        self._speech_frames = 0
        self._silent_frames = 0
        self._pre_roll.clear()

    def feed(self, frame: np.ndarray) -> np.ndarray | None:
        frame = to_int16(frame)
        speech = self.is_speech(frame)
        if not self._active:
            if speech:
                self._active = True
                self._frames = [*self._pre_roll, frame]
                self._speech_frames, self._silent_frames = 1, 0
            else:
                self._pre_roll.append(frame)
            return None
        self._frames.append(frame)
        if speech:
            self._speech_frames += 1
            self._silent_frames = 0
        else:
            self._silent_frames += 1
        if self._silent_frames >= self._silence_needed or len(self._frames) >= self._max_frames:
            utterance = np.concatenate(self._frames) if self._speech_frames >= self._min_speech else None
            self.reset()
            return utterance
        return None
```
Run the unit tests → `5 passed`.

- [ ] **Step 4: Real Silero tests** — `tests/models/test_vad_models.py`

```python
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
```
Run → `3 passed`.

- [ ] **Step 5: Gate, proof, progress, commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add requirements.txt assistant/voice/vad.py tests/unit/test_segmenter.py tests/models/test_vad_models.py docs/proof/P3-T3.md docs/PROGRESS.md
git commit -m "feat(voice): Silero VAD utterance segmentation [P3-T3]" -m "Proof: docs/proof/P3-T3.md"
```

**Acceptance criteria:** real speech is segmented at natural pauses; 7 s of silence and noise produce no utterance.

---

## P3-T4: `WakeWordDetector` with openWakeWord ("hey jarvis", no key)

**Goal:** A keyless wake word that fires on "Hey Jarvis" and stays quiet on silence, noise, and ordinary speech.

**Depends on:** P3-T1.

**Files:**
- Modify: `requirements.txt` (add `openwakeword`), `assistant/config.py` only if the threshold decision below applies
- Create: `assistant/voice/wake.py`, `tests/unit/test_wake.py`, `tests/models/test_wake_models.py`, `docs/proof/P3-T4.md`

**Interfaces — Produces:** `WakeWordDetector(model_name="hey_jarvis", threshold=0.5, model=None)` with `score`,
`detected`, `reset`, attribute `threshold` (PLAN §3.9 + §3.9a).

- [ ] **Step 1: Install, download, confirm the model name**

Append `openwakeword` to `requirements.txt`; install; then:
```powershell
.venv/Scripts/python.exe scripts/download_models.py --wake
.venv/Scripts/python.exe -c "from openwakeword.model import Model; m = Model(wakeword_models=['hey_jarvis'], inference_framework='onnx'); print(list(m.models.keys()))"
```
Expected: a list containing a `hey_jarvis` model key. If that name is rejected, `_load_model` below also tries
`"hey jarvis"` and `"hey_jarvis_v0.1"`; record the working name in the proof.

- [ ] **Step 2: Write the failing unit tests** — `tests/unit/test_wake.py`

```python
import numpy as np

from assistant.voice.wake import WakeWordDetector


class FakeModel:
    def __init__(self, scores: list[dict[str, float]]) -> None:
        self.scores = list(scores)
        self.dtypes: list = []
        self.resets = 0

    def predict(self, frame: np.ndarray) -> dict[str, float]:
        self.dtypes.append(frame.dtype)
        return self.scores.pop(0)

    def reset(self) -> None:
        self.resets += 1


def test_score_is_the_highest_model_score_and_frames_are_int16() -> None:
    model = FakeModel([{"hey_jarvis": 0.2, "other": 0.7}])
    detector = WakeWordDetector(model=model)
    assert detector.score(np.zeros(1280, dtype=np.float32)) == 0.7
    assert model.dtypes == [np.int16]


def test_detected_uses_threshold() -> None:
    model = FakeModel([{"hey_jarvis": 0.49}, {"hey_jarvis": 0.5}])
    detector = WakeWordDetector(threshold=0.5, model=model)
    assert detector.detected(np.zeros(1280, dtype=np.int16)) is False
    assert detector.detected(np.zeros(1280, dtype=np.int16)) is True


def test_empty_prediction_scores_zero_and_reset_is_forwarded() -> None:
    model = FakeModel([{}])
    detector = WakeWordDetector(model=model)
    assert detector.score(np.zeros(1280, dtype=np.int16)) == 0.0
    detector.reset()
    assert model.resets == 1
```
Run → FAIL (module missing).

- [ ] **Step 3: Write `assistant/voice/wake.py`**

```python
"""Wake word detection with openWakeWord's pre-trained "hey jarvis" model. No account or key required."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from assistant.voice.audio_io import to_int16

log = logging.getLogger("jarvis.wake")


def _load_model(model_name: str) -> Any:
    from openwakeword.model import Model

    last_error: Exception | None = None
    for candidate in dict.fromkeys([model_name, model_name.replace("_", " "), f"{model_name}_v0.1"]):
        try:
            model = Model(wakeword_models=[candidate], inference_framework="onnx")
            log.info("openWakeWord loaded %s", list(model.models.keys()))
            return model
        except Exception as exc:
            last_error = exc
    raise RuntimeError(
        f"openWakeWord model {model_name!r} unavailable ({last_error}). "
        "Run: .venv/Scripts/python.exe scripts/download_models.py --wake"
    )


class WakeWordDetector:
    def __init__(self, model_name: str = "hey_jarvis", threshold: float = 0.5, model: Any | None = None) -> None:
        self.threshold = threshold
        self._model = model if model is not None else _load_model(model_name)

    def score(self, frame: np.ndarray) -> float:
        prediction = self._model.predict(to_int16(frame))
        return float(max(prediction.values())) if prediction else 0.0

    def detected(self, frame: np.ndarray) -> bool:
        return self.score(frame) >= self.threshold

    def reset(self) -> None:
        self._model.reset()
```
Run the unit tests → `3 passed`.

- [ ] **Step 4: Real-model tests** — `tests/models/test_wake_models.py`

```python
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
```
If a listed voice is not in `synthesizer.voices()`, replace it with another voice of the same accent/gender prefix and
record it. Run: `.venv/Scripts/python.exe -m pytest tests/models/test_wake_models.py -q -s` → `3 passed`; copy the printed
scores into the proof.

Threshold decision rule: if detection fails at `0.5` but all three tests pass with a lower threshold (never below `0.3`),
change the `wake_threshold` default in `assistant/config.py` to the highest value that passes all three and record the
per-threshold results in `docs/DECISIONS.md`. Never change the tests' sentences to make them pass.

- [ ] **Step 5: Gate, proof, progress, commit, push**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add requirements.txt assistant/voice/wake.py assistant/config.py tests/unit/test_wake.py tests/models/test_wake_models.py docs/proof/P3-T4.md docs/PROGRESS.md docs/DECISIONS.md
git commit -m "feat(voice): keyless hey-jarvis wake word via openWakeWord [P3-T4]" -m "Proof: docs/proof/P3-T4.md"
git push origin testing
```

**Acceptance criteria:** zero triggers on 20 s of silence/noise and on three ordinary sentences; "Hey Jarvis" triggers
for at least two different voices.
