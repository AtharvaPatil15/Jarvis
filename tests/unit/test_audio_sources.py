import time

import numpy as np
import soundfile

from assistant.voice.audio_io import FRAME_SAMPLES, NullSink, WavSource


def test_wav_source_from_array_adds_lead_and_tail_silence() -> None:
    frames = list(WavSource(np.ones(FRAME_SAMPLES * 2, dtype=np.int16), lead_silence_s=0.16, tail_silence_s=0.08).frames())
    assert len(frames) == 5
    assert not frames[0].any() and frames[2].all() and not frames[4].any()


def test_wav_source_from_file_is_resampled_to_16k(tmp_path) -> None:
    path = tmp_path / "tone.wav"
    soundfile.write(path, np.full(24000, 0.25, dtype=np.float32), 24000)
    frames = list(WavSource(path, tail_silence_s=0.0).frames())
    assert len(frames) == 13 and all(len(f) == FRAME_SAMPLES and f.dtype == np.int16 for f in frames)


def test_realtime_wav_source_paces_frames() -> None:
    start = time.monotonic()
    list(WavSource(np.zeros(FRAME_SAMPLES * 5, dtype=np.int16), realtime=True, tail_silence_s=0.0).frames())
    assert time.monotonic() - start >= 0.35


def test_null_sink_records_and_simulates_playback() -> None:
    sink = NullSink(simulate_playback=True)
    sink.play(np.zeros(4800, dtype=np.float32), 24000)
    assert sink.is_playing and len(sink.played) == 1
    sink.wait()
    assert not sink.is_playing


def test_null_sink_stop_ends_playback_immediately() -> None:
    sink = NullSink(simulate_playback=True)
    sink.play(np.zeros(240000, dtype=np.float32), 24000)
    sink.stop()
    assert not sink.is_playing and sink.stopped == 1
