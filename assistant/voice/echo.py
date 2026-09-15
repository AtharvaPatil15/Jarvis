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
