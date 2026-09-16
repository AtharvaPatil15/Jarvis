"""Open installed apps and web pages, and send media keys (Windows)."""
from __future__ import annotations

import ctypes
import os
import webbrowser
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from assistant.tools.base import BaseTool

ALIASES = {
    "notepad": "notepad.exe", "calculator": "calc.exe", "file explorer": "explorer.exe", "explorer": "explorer.exe",
    "command prompt": "cmd.exe", "terminal": "wt.exe", "task manager": "taskmgr.exe", "paint": "mspaint.exe",
    "settings": "ms-settings:", "control panel": "control.exe",
}
SYNONYMS = {"vs code": "visual studio code", "vscode": "visual studio code", "word": "microsoft word",
            "excel": "microsoft excel", "powerpoint": "microsoft powerpoint", "edge": "microsoft edge"}
MATCH_THRESHOLD = 75
VIRTUAL_KEYS = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "volume_up": 0xAF, "volume_down": 0xAE, "mute": 0xAD}
_KEYEVENTF_KEYUP = 0x0002


def default_shortcut_dirs() -> list[Path]:
    return [Path(os.environ[var]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            for var in ("PROGRAMDATA", "APPDATA") if os.environ.get(var)]


def _launch(target: str) -> None:
    os.startfile(target)  # resolved Start-menu shortcut or a fixed alias, never free text


def press_virtual_key(code: int) -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(code, 0, 0, 0)
    user32.keybd_event(code, 0, _KEYEVENTF_KEYUP, 0)


class OpenAppArgs(BaseModel):
    name: str = Field(description="App name as the user says it, e.g. 'chrome', 'spotify', 'vs code'")


class OpenAppTool(BaseTool):
    name = "open_app"
    description = "Open an installed application by name."
    Args = OpenAppArgs

    def __init__(self, shortcut_dirs: Iterable[Path] | None = None, launcher: Callable[[str], None] = _launch) -> None:
        self._dirs = list(shortcut_dirs) if shortcut_dirs is not None else default_shortcut_dirs()
        self._launch = launcher

    def resolve(self, name: str) -> str | None:
        key = name.strip().lower()
        if key in ALIASES:
            return ALIASES[key]
        key = SYNONYMS.get(key, key)
        found = {p.stem: p for d in self._dirs if d.is_dir() for p in d.rglob("*.lnk")
                 if "uninstall" not in p.stem.lower()}
        if not found:
            return None
        match = process.extractOne(key, list(found), scorer=fuzz.WRatio, processor=str.lower)
        return str(found[match[0]]) if match and match[1] >= MATCH_THRESHOLD else None

    def run(self, args: OpenAppArgs) -> str:
        target = self.resolve(args.name)
        if target is None:
            return f"ERROR: no installed app matches {args.name!r}"
        try:
            self._launch(target)
        except OSError as exc:
            return f"ERROR: could not open {args.name}: {exc}"
        return f"Opened {Path(target).stem if target.lower().endswith('.lnk') else args.name}."


class OpenUrlArgs(BaseModel):
    url: str = Field(description="Full http or https URL to open in the default browser")


class OpenUrlTool(BaseTool):
    name = "open_url"
    description = "Open a web page in the user's default browser."
    Args = OpenUrlArgs

    def __init__(self, opener: Callable[[str], bool] = webbrowser.open) -> None:
        self._opener = opener

    def run(self, args: OpenUrlArgs) -> str:
        parsed = urlparse(args.url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return "ERROR: only http and https URLs can be opened"
        return f"Opened {args.url}." if self._opener(args.url) else f"ERROR: the browser did not open {args.url}"


class MediaControlArgs(BaseModel):
    action: Literal["play_pause", "next", "previous", "volume_up", "volume_down", "mute"]
    steps: int = Field(default=1, ge=1, le=10, description="How many volume steps; ignored for other actions")


class MediaControlTool(BaseTool):
    name = "media_control"
    description = "Control media playback and system volume: play_pause, next, previous, volume_up, volume_down, mute."
    Args = MediaControlArgs

    def __init__(self, press: Callable[[int], None] = press_virtual_key) -> None:
        self._press = press

    def run(self, args: MediaControlArgs) -> str:
        repeats = args.steps if args.action.startswith("volume") else 1
        for _ in range(repeats):
            self._press(VIRTUAL_KEYS[args.action])
        return f"Done: {args.action.replace('_', ' ')}{f' x{repeats}' if repeats > 1 else ''}."
