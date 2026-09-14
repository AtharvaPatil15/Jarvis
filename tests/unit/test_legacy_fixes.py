import ast
import importlib
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KEY_PREFIX = "ycGaIQ" + "bL2ZWI8r2M"


def _class_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    return {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}


def test_voice_main_only_calls_methods_that_exist_on_speech_to_text() -> None:
    tree = ast.parse((ROOT / "voice_main.py").read_text(encoding="utf-8"))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "stt"
    }
    assert called, "voice_main.py should call methods on its SpeechToText instance"
    assert called <= _class_methods(ROOT / "assistant/voice/stt.py", "SpeechToText")


def test_no_porcupine_key_in_any_tracked_file() -> None:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    offenders = [
        name for name in tracked.splitlines()
        if (ROOT / name).is_file() and KEY_PREFIX in (ROOT / name).read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == []


def test_smart_search_module_imports() -> None:
    module = importlib.import_module("assistant.tools.smart_search")
    assert module.SmartSearchTool.name == "smart_search"


def test_requirements_use_ddgs_package() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "ddgs" in requirements
    assert "duckduckgo-search" not in requirements


def test_legacy_wake_engine_without_key_fails_clearly(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("JARVIS_PORCUPINE_ACCESS_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "pvporcupine", types.ModuleType("pvporcupine"))
    monkeypatch.setitem(sys.modules, "sounddevice", types.ModuleType("sounddevice"))
    monkeypatch.delitem(sys.modules, "assistant.voice.wake_word", raising=False)
    wake_word = importlib.import_module("assistant.voice.wake_word")
    with pytest.raises(RuntimeError, match="JARVIS_PORCUPINE_ACCESS_KEY"):
        wake_word.WakeWordEngine()