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
