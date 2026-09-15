"""Download local speech models: Kokoro TTS and Whisper STT into models/, openWakeWord into its package folder.

Usage: .venv/Scripts/python.exe scripts/download_models.py [--kokoro] [--whisper] [--wake]   (no flags = all)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assistant.config import get_settings  # noqa: E402

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
KOKORO_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"present  {target} ({target.stat().st_size} bytes)", flush=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(30.0, read=600.0)) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes(1 << 20):
                handle.write(chunk)
    partial.replace(target)
    print(f"download {target} ({target.stat().st_size} bytes)", flush=True)


def kokoro(models_dir: Path) -> None:
    for name in KOKORO_FILES:
        path = models_dir / "kokoro" / name
        download(f"{KOKORO_BASE}/{name}", path)
        print(f"sha256   {name} {sha256(path)}", flush=True)


def whisper(models_dir: Path, size: str) -> None:
    from faster_whisper import download_model

    print(f"whisper  {size} -> {download_model(size, cache_dir=str(models_dir / 'whisper'))}", flush=True)


def wake() -> None:
    import openwakeword.utils

    openwakeword.utils.download_models()
    print("openwakeword pre-trained models downloaded", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for flag in ("kokoro", "whisper", "wake"):
        parser.add_argument(f"--{flag}", action="store_true")
    args = parser.parse_args(argv)
    settings = get_settings()
    models_dir = settings.models_dir if settings.models_dir.is_absolute() else ROOT / settings.models_dir
    selected = [name for name in ("kokoro", "whisper", "wake") if getattr(args, name)] or ["kokoro", "whisper", "wake"]
    if "kokoro" in selected:
        kokoro(models_dir)
    if "whisper" in selected:
        whisper(models_dir, settings.whisper_model)
    if "wake" in selected:
        wake()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
