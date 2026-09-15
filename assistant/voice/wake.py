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
