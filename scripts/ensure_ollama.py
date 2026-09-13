"""Ensure the local Ollama server is running and the JARVIS models are pulled.

Usage:
  python scripts/ensure_ollama.py            start server if needed, pull missing models
  python scripts/ensure_ollama.py --no-pull  start server if needed, fail if models are missing
  python scripts/ensure_ollama.py --check    do not start or pull; exit 1 if anything is missing
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

OLLAMA_URL = os.environ.get("JARVIS_OLLAMA_URL", "http://127.0.0.1:11434")
REQUIRED = [
    os.environ.get("JARVIS_CHAT_MODEL", "qwen3:8b"),
    os.environ.get("JARVIS_EMBED_MODEL", "nomic-embed-text"),
]
DEFAULT_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"


def ollama_exe() -> str:
    found = shutil.which("ollama")
    if found:
        return found
    if DEFAULT_EXE.exists():
        return str(DEFAULT_EXE)
    raise SystemExit("ollama executable not found")


def server_up() -> bool:
    try:
        return httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def start_server() -> None:
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        [ollama_exe(), "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    for _ in range(60):
        if server_up():
            return
        time.sleep(1)
    raise SystemExit("ollama server did not become ready within 60 s")


def installed_models() -> set[str]:
    names: set[str] = set()
    for model in httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10).json().get("models", []):
        names.add(model["name"])
        if model["name"].endswith(":latest"):
            names.add(model["name"].removesuffix(":latest"))
    return names


def pull(model: str) -> None:
    print(f"pulling {model}", flush=True)
    last = ""
    with httpx.stream("POST", f"{OLLAMA_URL}/api/pull", json={"model": model, "stream": True}, timeout=None) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            if "error" in data:
                raise SystemExit(f"pull failed for {model}: {data['error']}")
            status = data.get("status", "")
            if status != last:
                print(status, flush=True)
                last = status


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    no_pull = "--no-pull" in argv
    if not server_up():
        if check_only:
            print("server: down")
            return 1
        start_server()
    print("server: up")
    have = installed_models()
    missing = [m for m in REQUIRED if m not in have]
    for model in REQUIRED:
        print(f"{model}: {'missing' if model in missing else 'present'}")
    if missing and (check_only or no_pull):
        return 1
    for model in missing:
        pull(model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))