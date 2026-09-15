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
