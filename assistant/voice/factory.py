"""Assembles the production voice pipeline from Settings."""
from __future__ import annotations

from assistant.config import Settings
from assistant.events import Emit
from assistant.voice.audio_io import AudioSink, AudioSource, MicSource, SpeakerSink
from assistant.voice.controller import Handler, VoiceController
from assistant.voice.stt import Transcriber
from assistant.voice.tts import Synthesizer
from assistant.voice.vad import SpeechSegmenter
from assistant.voice.wake import WakeWordDetector


def build_voice_controller(settings: Settings, handler: Handler, emit: Emit, source: AudioSource | None = None,
                           sink: AudioSink | None = None) -> VoiceController:
    if source is None:
        from assistant.voice.mic_selector import auto_select_best_mic

        mic = auto_select_best_mic()
        if mic is None:
            raise RuntimeError("no microphone found")
        source = MicSource(device=mic["index"])
    return VoiceController(
        source=source,
        sink=sink if sink is not None else SpeakerSink(),
        wake=WakeWordDetector(settings.wake_model, settings.wake_threshold),
        segmenter=SpeechSegmenter(silence_ms=settings.vad_silence_ms),
        stt=Transcriber(settings.whisper_model, settings.whisper_device, download_root=settings.models_dir / "whisper"),
        tts=Synthesizer(settings.models_dir / "kokoro", voice=settings.tts_voice, speed=settings.tts_speed),
        handler=handler,
        emit=emit,
    )
