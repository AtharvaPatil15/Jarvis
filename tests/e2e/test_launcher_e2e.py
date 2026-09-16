import subprocess
import tempfile
from pathlib import Path

import httpx
import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(1200)]
ROOT = Path(__file__).resolve().parents[2]


def launcher(*args: str) -> subprocess.CompletedProcess:
    # The launcher's background servers inherit its output handles, so a pipe would never reach
    # end-of-file and subprocess.run would hang; a temporary file does not (D-026).
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as out:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(ROOT / "scripts" / "start_jarvis.ps1"), *args],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, timeout=1000)
        out.seek(0)
        return subprocess.CompletedProcess(done.args, done.returncode, out.read(), "")


def test_launcher_starts_backend_and_ui_and_stops_them() -> None:
    started = launcher("-Fake", "-NoElectron")
    try:
        assert started.returncode == 0, started.stdout + started.stderr
        assert httpx.get("http://127.0.0.1:8000/health", timeout=5).json()["status"] == "ok"
        assert httpx.get("http://127.0.0.1:3000", timeout=15).status_code == 200
    finally:
        stopped = launcher("-Stop")
    assert stopped.returncode == 0
    with pytest.raises(httpx.HTTPError):
        httpx.get("http://127.0.0.1:8000/health", timeout=2)


def test_electron_window_loads_the_ui() -> None:
    started = launcher("-Fake", "-NoElectron")
    try:
        assert started.returncode == 0, started.stdout + started.stderr
        smoke = subprocess.run(["npx.cmd", "electron", "electron/main.js", "--smoke"], cwd=ROOT,
                               capture_output=True, text=True, timeout=180)
        assert smoke.returncode == 0 and "ELECTRON_SMOKE_OK" in smoke.stdout, smoke.stdout + smoke.stderr
    finally:
        launcher("-Stop")