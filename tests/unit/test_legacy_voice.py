import importlib
import sys
import types


def _stub_module(monkeypatch, module_name: str, class_name: str) -> None:
    module = types.ModuleType(module_name)
    setattr(module, class_name, type(class_name, (), {"__init__": lambda self, *a, **k: None}))
    monkeypatch.setitem(sys.modules, module_name, module)


def test_legacy_voice_controller_exposes_conv_manager(monkeypatch) -> None:
    import assistant.voice  # noqa: F401  (real package, stubbed submodules below)

    _stub_module(monkeypatch, "assistant.voice.stt", "SpeechToText")
    _stub_module(monkeypatch, "assistant.voice.wake_word", "WakeWordEngine")
    _stub_module(monkeypatch, "assistant.voice.tts", "TextToSpeech")
    monkeypatch.delitem(sys.modules, "assistant.voice.voice_controller", raising=False)
    controller_module = importlib.import_module("assistant.voice.voice_controller")
    controller = controller_module.VoiceController(on_event=lambda *_: None)
    assert controller.conv_manager.is_processing is False