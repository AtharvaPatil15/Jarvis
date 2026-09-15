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
