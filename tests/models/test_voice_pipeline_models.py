import asyncio

import numpy as np
import pytest

from assistant.config import Settings
from assistant.voice.audio_io import NullSink, WavSource
from assistant.voice.factory import build_voice_controller

pytestmark = [pytest.mark.models, pytest.mark.timeout(300)]


async def test_wake_word_to_spoken_reply_with_real_models(speak, events) -> None:
    heard: list[str] = []

    async def handler(text: str, on_delta) -> str:
        heard.append(text)
        on_delta("Paris is the capital of France.")
        return "Paris is the capital of France."

    audio = np.concatenate([speak("Hey Jarvis.", lead_s=1.0, tail_s=0.6),
                            speak("What is the capital of France?", lead_s=0.0, tail_s=2.0)])
    sink = NullSink()
    controller = build_voice_controller(Settings(_env_file=None), handler, events, source=WavSource(audio), sink=sink)
    await controller.run(asyncio.Event())
    assert len(heard) == 1 and "capital of france" in heard[0].lower()
    assert len(sink.played) == 1
    types = events.types()
    assert types.index("wake_word_detected") < types.index("user_transcript")
