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
