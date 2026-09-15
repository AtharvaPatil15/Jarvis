"""Audio format helpers. Internal format: 16 kHz mono int16, frames of 1280 samples (80 ms)."""
from __future__ import annotations

import math
import queue
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import numpy as np
import soundfile
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
