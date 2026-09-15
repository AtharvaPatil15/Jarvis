import ast
import importlib
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KEY_PREFIX = "ycGaIQ" + "bL2ZWI8r2M"


def test_no_porcupine_key_in_any_tracked_file() -> None:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    offenders = [
        name for name in tracked.splitlines()
        if (ROOT / name).is_file() and KEY_PREFIX in (ROOT / name).read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == []


def test_web_search_tool_module_imports() -> None:
    module = importlib.import_module("assistant.tools.builtin.web_search")
    assert module.WebSearchTool.name == "web_search"


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