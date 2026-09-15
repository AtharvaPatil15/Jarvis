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
