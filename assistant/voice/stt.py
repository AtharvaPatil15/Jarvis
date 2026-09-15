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
