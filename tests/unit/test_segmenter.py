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
