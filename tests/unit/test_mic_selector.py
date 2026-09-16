"""Reproduces the real-world crash: the launcher redirects the backend's stdout/stderr to log files
(scripts/start_jarvis.ps1), and Windows opens a redirected stream with the system ANSI code page (cp1252 on
this machine), not UTF-8. `auto_select_best_mic` used to `print()` an emoji, which raised UnicodeEncodeError on
that stream and crashed voice startup; server.py caught the exception and silently reported `voice: false`, so
the wake word and TTS never ran even though a microphone was available (D-027)."""
import io
import sys

from assistant.voice.mic_selector import auto_select_best_mic, is_headset


def _cp1252_stream() -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")


def test_selecting_the_default_mic_never_raises_on_a_cp1252_stream(monkeypatch) -> None:
    monkeypatch.setattr("assistant.voice.mic_selector.sd.query_hostapis", lambda: [{"name": "Windows MME"}])
    monkeypatch.setattr(
        "assistant.voice.mic_selector.sd.query_devices",
        lambda: [{"max_input_channels": 1, "hostapi": 0, "name": "Microphone Array", "default_samplerate": 44100.0}],
    )
    monkeypatch.setattr(sys, "stdout", _cp1252_stream())
    monkeypatch.setattr(sys, "stderr", _cp1252_stream())

    mic = auto_select_best_mic()

    assert mic == {"index": 0, "name": "Microphone Array", "is_default": True}


def test_selecting_a_headset_never_raises_on_a_cp1252_stream(monkeypatch) -> None:
    monkeypatch.setattr("assistant.voice.mic_selector.sd.query_hostapis", lambda: [{"name": "Windows MME"}])
    monkeypatch.setattr(
        "assistant.voice.mic_selector.sd.query_devices",
        lambda: [
            {"max_input_channels": 1, "hostapi": 0, "name": "Microphone Array", "default_samplerate": 44100.0},
            {"max_input_channels": 1, "hostapi": 0, "name": "Bose Headset", "default_samplerate": 44100.0},
        ],
    )
    monkeypatch.setattr(sys, "stdout", _cp1252_stream())

    mic = auto_select_best_mic()

    assert mic is not None
    assert mic["name"] == "Bose Headset"


def test_no_mme_devices_falls_back_to_any_input_without_raising(monkeypatch) -> None:
    monkeypatch.setattr("assistant.voice.mic_selector.sd.query_hostapis", lambda: [{"name": "Windows MME"}])
    monkeypatch.setattr(
        "assistant.voice.mic_selector.sd.query_devices",
        lambda: [{"max_input_channels": 1, "hostapi": 1, "name": "WDM-KS Mic", "default_samplerate": 44100.0}],
    )
    monkeypatch.setattr(sys, "stdout", _cp1252_stream())

    mic = auto_select_best_mic()

    assert mic is not None
    assert mic["name"] == "WDM-KS Mic"


def test_is_headset_matches_known_brands_case_insensitively() -> None:
    assert is_headset("Bose QuietComfort")
    assert is_headset("JBL TUNE")
    assert not is_headset("Microphone Array")
