import importlib
import subprocess
from pathlib import Path

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