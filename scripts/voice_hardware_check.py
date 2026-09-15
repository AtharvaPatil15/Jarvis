"""Manual check for the owner: records 3 s from the chosen microphone and speaks one sentence."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from assistant.config import get_settings  # noqa: E402
from assistant.voice.audio_io import FRAME_SAMPLES, MicSource, SpeakerSink  # noqa: E402
from assistant.voice.mic_selector import auto_select_best_mic  # noqa: E402
from assistant.voice.tts import Synthesizer  # noqa: E402


def main() -> int:
    settings = get_settings()
    mic = auto_select_best_mic()
    if mic is None:
        print("no microphone found")
        return 1
    print(f"microphone: {mic['name']} (index {mic['index']}) - speak now for 3 seconds")
    frames = []
    for frame in MicSource(mic["index"]).frames():
        frames.append(frame)
        if len(frames) * FRAME_SAMPLES >= 3 * 16000:
            break
    rms = float(np.sqrt(np.mean(np.concatenate(frames).astype(np.float64) ** 2)))
    print(f"recorded RMS level: {rms:.0f} (speech is usually above 300)")
    sink = SpeakerSink()
    samples, rate = Synthesizer(settings.models_dir / "kokoro", settings.tts_voice, settings.tts_speed).synthesize(
        "Audio check complete. I can hear you, and you can hear me.")
    sink.play(samples, rate)
    sink.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
