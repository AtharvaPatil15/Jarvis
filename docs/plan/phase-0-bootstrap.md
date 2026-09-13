# Phase 0 — Bootstrap (git, environment, test harness, models, config)

Order: **P0-T1 → P0-T2 → P0-T3 → P0-T4**. Commands are PowerShell, run from the repo root
`C:\Users\athar\Documents\Jarvis-Assistant`, unless stated otherwise.

---

## P0-T1: Git baseline on branch `testing`

**Goal:** The current folder becomes branch `testing` on GitHub, built on top of `origin/main`, with no secrets or
forbidden files committed. `main` and `Test` stay untouched.

**Depends on:** nothing. **Gate for this task only:** the checks in Step 6 (`verify_all.ps1` does not exist yet).

**Files:**
- Modify: `.gitignore` (append block)
- Modify: `assistant/voice/wake_word.py` (hardcoded Porcupine key → environment variable)
- Modify: `voice_main.py` (same)
- Create: `docs/proof/P0-T1.md`

- [ ] **Step 1: Resume check**

```powershell
git rev-parse --is-inside-work-tree
git branch --show-current
git log -1 --format=%s
```
If the repo exists, the branch is `testing`, and the last subject contains `[P0-T1]`, this task is already done:
mark it `DONE` in `docs/PROGRESS.md` and go to P0-T2. Otherwise continue (errors like
`not a git repository` are expected on a fresh start).

- [ ] **Step 2: Take the leaked Porcupine key out of source code**

The key (a 56-character string beginning `ycGa`) is hardcoded in two places. Never copy it anywhere.

In `assistant/voice/wake_word.py`: add `import os` at the top, and inside `WakeWordEngine.__init__` replace the
`access_key="..."` argument with:
```python
            access_key=os.environ.get("JARVIS_PORCUPINE_ACCESS_KEY", ""),
```
In `voice_main.py`: add `import os` at the top and replace the `PORCUPINE_ACCESS_KEY = "..."` line with:
```python
PORCUPINE_ACCESS_KEY = os.environ.get("JARVIS_PORCUPINE_ACCESS_KEY", "")
```
Verify (must print nothing):
```powershell
Select-String -Path assistant/voice/wake_word.py, voice_main.py -Pattern ('ycGaIQ' + 'bL2ZWI8r2M')
```

- [ ] **Step 3: Append ignore rules to `.gitignore`**

Append exactly:
```gitignore

# --- Added in P0-T1 ---
PROJECT_CONTEXT.md
PROJECT_RAW_DUMP.md
models/
data/
*.onnx
*.bin
*.wav
test-results/
playwright-report/
docs/proof/tmp/
```
(`.env`, `key.txt`, `*.db`, `*.mp3`, `.venv/`, `node_modules/`, `.next/` are already ignored.)

- [ ] **Step 4: Create the repo on top of `origin/main` without touching working files**

```powershell
git init -b testing
git remote add origin https://github.com/AtharvaPatil15/Jarvis.git
git fetch origin
git rev-parse origin/main origin/Test
git update-ref refs/heads/testing refs/remotes/origin/main
git reset
git branch --show-current
git status --short | Select-Object -First 80
gh auth setup-git
```
Expected: `origin/main` starts with `d31dfb6`, `origin/Test` starts with `a27b32d` (write both full hashes into the
proof — they prove later that those branches were not modified). If they differ, record the actual values in
`docs/DECISIONS.md` and continue. `git branch --show-current` prints `testing`. `git reset` (no flags) only
resets the index to `origin/main`; working files are unchanged.

- [ ] **Step 5: Stage the baseline (the only permitted `git add -A`)**

```powershell
git add -A
```

- [ ] **Step 6: Forbidden-path and secret checks — both must print nothing**

```powershell
$forbidden = '(^|/)\.env$|(^|/)key\.txt$|^\.venv/|(^|/)node_modules/|^\.next/|^models/|^data/|\.(db|onnx|bin|wav|mp3)$|^PROJECT_(CONTEXT|RAW_DUMP)\.md$'
git diff --cached --name-only | Where-Object { $_ -match $forbidden }
git grep --cached -lIE (('ycGaIQ' + 'bL2ZWI8r2M') + '|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}')
```
If either prints a path: `git restore --staged <path>`, fix `.gitignore` or the file, and repeat Step 6.

- [ ] **Step 7: Write the proof and progress, then stage them**

Create `docs/proof/P0-T1.md` (template: `docs/proof/README.md`) containing the output of Steps 4 and 6 and of:
```powershell
git diff --cached --stat | Select-Object -Last 3
```
Set P0-T1 to `DONE` in `docs/PROGRESS.md`, then:
```powershell
git add docs/proof/P0-T1.md docs/PROGRESS.md
```

- [ ] **Step 8: Commit**

```powershell
git commit -m "chore(repo): import latest local codebase as testing baseline [P0-T1]" -m "Proof: docs/proof/P0-T1.md"
```

- [ ] **Step 9: Push and prove `main` / `Test` are untouched**

```powershell
git push -u origin testing
git ls-remote --heads origin
git rev-parse HEAD
git log -1 --format=%P
```
Expected: the `refs/heads/testing` hash equals `git rev-parse HEAD`; `refs/heads/main` and `refs/heads/Test` equal the
hashes recorded in Step 4; the commit's parent (`%P`) equals the `origin/main` hash. Append this output to
`docs/proof/P0-T1.md` under a heading `## Post-push verification` (it gets committed with P0-T2).

**Acceptance criteria**
- `origin/testing` exists and its parent commit is `origin/main`.
- `git ls-files | Where-Object { $_ -match $forbidden }` prints nothing.
- `main` and `Test` hashes unchanged.

---

## P0-T2: Python venv, test harness, and quality gate

**Goal:** A reproducible Python environment, a pytest harness with markers, and `scripts/verify_all.ps1` — the
single gate every later task must pass (proven to fail when a test fails).

**Depends on:** P0-T1.

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`, `pytest.ini`, `tests/__init__.py`, `tests/conftest.py`, `tests/helpers.py`,
  `tests/unit/__init__.py`, `tests/unit/test_harness.py`, `tests/live/.gitkeep`, `tests/models/.gitkeep`,
  `tests/e2e/.gitkeep`, `tests/fixtures/.gitkeep`, `scripts/__init__.py`, `scripts/verify_all.ps1`,
  `docs/proof/P0-T2.md`

**Interfaces — Produces:** `tests.helpers.wait_until(predicate, timeout=2.0, interval=0.02) -> bool`;
pytest fixture `events` (an `EventRecorder` with `__call__(type_, payload)`, `types() -> list[str]`,
`payloads(type_) -> list[Any]`, `events: list[tuple[str, Any]]`); `scripts/verify_all.ps1 [-Quick]`.

- [ ] **Step 1: Create the venv**

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe --version
.venv/Scripts/python.exe -m pip install --upgrade pip
```
Expected: `Python 3.12.4`.

- [ ] **Step 2: Write `requirements.txt` (replace the whole file)**

```text
# Runtime dependencies. Later tasks append to this file.
fastapi>=0.115
uvicorn[standard]>=0.30
websockets>=12
httpx>=0.27
pydantic>=2.8
pydantic-settings>=2.4
requests>=2.32
beautifulsoup4>=4.12
ddgs
numpy>=2.0
sounddevice>=0.5

# Legacy voice stack - removed in P3-T6
pvporcupine
SpeechRecognition
PyAudio
edge-tts
pygame
```

- [ ] **Step 3: Write `requirements-dev.txt`**

```text
pytest>=8.3
pytest-asyncio>=0.24
pytest-timeout>=2.3
```

- [ ] **Step 4: Install**

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt -r requirements-dev.txt
npm install
```
If a legacy package (PyAudio, pvporcupine, pygame, SpeechRecognition, edge-tts) fails to install, delete only that
line, record it in `docs/DECISIONS.md`, and continue — the legacy stack is deleted in P3-T6 and its tests use fake
modules.

- [ ] **Step 5: Write the failing test `tests/unit/test_harness.py`**

```python
import assistant


def test_assistant_package_importable() -> None:
    assert assistant is not None


def test_event_recorder_records_in_order(events) -> None:
    events("state_change", "thinking")
    events("ai_response", "hi")
    events("state_change", "idle")
    assert events.types() == ["state_change", "ai_response", "state_change"]
    assert events.payloads("state_change") == ["thinking", "idle"]
```
Also create empty `tests/__init__.py`, `tests/unit/__init__.py`, `scripts/__init__.py`.

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_harness.py -q`
Expected: FAIL — `fixture 'events' not found`.

- [ ] **Step 6: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
asyncio_mode = auto
timeout = 600
addopts = -p no:cacheprovider
markers =
    live: needs the local Ollama server with pulled models
    models: needs downloaded Whisper / Kokoro / openWakeWord model files
    e2e: starts real servers and/or a browser
```

- [ ] **Step 7: Write `tests/helpers.py` and `tests/conftest.py`**

`tests/helpers.py`:
```python
from __future__ import annotations

import time
from collections.abc import Callable


def wait_until(predicate: Callable[[], bool], timeout: float = 2.0, interval: float = 0.02) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    raise AssertionError(f"condition not met within {timeout} s")
```

`tests/conftest.py`:
```python
from __future__ import annotations

from typing import Any

import pytest


class EventRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def __call__(self, type_: str, payload: Any) -> None:
        self.events.append((str(type_), payload))

    def types(self) -> list[str]:
        return [t for t, _ in self.events]

    def payloads(self, type_: str) -> list[Any]:
        return [p for t, p in self.events if t == str(type_)]


@pytest.fixture
def events() -> EventRecorder:
    return EventRecorder()
```
Create empty `tests/live/.gitkeep`, `tests/models/.gitkeep`, `tests/e2e/.gitkeep`, `tests/fixtures/.gitkeep`.

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_harness.py -q`
Expected: `2 passed`.

- [ ] **Step 8: Write `scripts/verify_all.ps1`**

```powershell
param([switch]$Quick)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root '.venv/Scripts/python.exe'
New-Item -ItemType Directory -Force -Path 'docs/proof/tmp' | Out-Null
$log = "docs/proof/tmp/verify-$(Get-Date -Format yyyyMMdd-HHmmss).log"
$results = [ordered]@{}

$forbidden = '(^|/)\.env$|(^|/)key\.txt$|^\.venv/|(^|/)node_modules/|^\.next/|^models/|^data/|\.(db|onnx|bin|wav|mp3)$|^PROJECT_(CONTEXT|RAW_DUMP)\.md$'
$secretPattern = ('ycGaIQ' + 'bL2ZWI8r2M') + '|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}'

function Invoke-Gate {
    param([string]$Name, [scriptblock]$Command, [int[]]$OkCodes = @(0))
    Write-Output "=== $Name ==="
    Add-Content -Path $log -Value "=== $Name ==="
    $global:LASTEXITCODE = 0
    & $Command 2>&1 | ForEach-Object {
        $line = "$_"
        Write-Output $line
        Add-Content -Path $log -Value $line
    }
    $code = $global:LASTEXITCODE
    Add-Content -Path $log -Value "exit=$code"
    if ($OkCodes -contains $code) { $results[$Name] = 'ok' } else { $results[$Name] = "FAILED (exit $code)" }
}

Invoke-Gate 'FORBIDDEN PATHS' {
    $bad = @(git ls-files) + @(git diff --cached --name-only) | Sort-Object -Unique | Where-Object { $_ -match $forbidden }
    if ($bad) { $bad; $global:LASTEXITCODE = 1 } else { 'none'; $global:LASTEXITCODE = 0 }
}

# git grep exits 1 when nothing matches, which is the passing case. -l prints file names only, never secrets.
Invoke-Gate 'SECRET SCAN (index)' { git grep --cached -lIE $secretPattern } @(1)

Invoke-Gate 'SECRET SCAN (untracked)' {
    $hits = git ls-files --others --exclude-standard |
        Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
        ForEach-Object { Select-String -LiteralPath $_ -Pattern $secretPattern -List }
    if ($hits) { $hits | ForEach-Object { "$($_.Path):$($_.LineNumber)" }; $global:LASTEXITCODE = 1 }
    else { 'none'; $global:LASTEXITCODE = 0 }
}

# pytest exit 5 = no tests collected for that marker, which is fine early in the project.
Invoke-Gate 'PYTHON UNIT' { & $py -m pytest -m 'not live and not models and not e2e' -q } @(0, 5)
Invoke-Gate 'TYPESCRIPT' { npx tsc --noEmit }
if (Test-Path 'vitest.config.ts') { Invoke-Gate 'VITEST' { npx vitest run } }

if (-not $Quick) {
    if (Test-Path 'scripts/ensure_ollama.py') { Invoke-Gate 'OLLAMA READY' { & $py scripts/ensure_ollama.py --no-pull } }
    Invoke-Gate 'PYTHON LIVE' { & $py -m pytest -m live -q } @(0, 5)
    Invoke-Gate 'PYTHON MODELS' { & $py -m pytest -m models -q } @(0, 5)
    Invoke-Gate 'PYTHON E2E' { & $py -m pytest -m e2e -q } @(0, 5)
    Invoke-Gate 'NEXT BUILD' { npm run build }
    if (Test-Path 'playwright.config.ts') { Invoke-Gate 'PLAYWRIGHT' { npx playwright test } }
}

Write-Output '=== SUMMARY ==='
$failed = @()
foreach ($key in $results.Keys) {
    Write-Output ('{0,-26} {1}' -f $key, $results[$key])
    if ($results[$key] -ne 'ok') { $failed += $key }
}
Write-Output "log: $log"
if ($failed.Count -gt 0) { Write-Output "GATES FAILED: $($failed -join ', ')"; exit 1 }
Write-Output 'ALL GATES PASSED'
exit 0
```
Note: stop any running `next dev` before the full gate — `npm run build` and `next dev` fight over `.next/`.

- [ ] **Step 9: Prove the gate passes**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick; echo "exit=$LASTEXITCODE"`
Expected: SUMMARY shows `ok` for FORBIDDEN PATHS, SECRET SCAN (index), SECRET SCAN (untracked), PYTHON UNIT,
TYPESCRIPT; last lines `ALL GATES PASSED` and `exit=0`.

- [ ] **Step 10: Prove the gate fails when a test fails**

Create `tests/unit/test_gate_selfcheck.py`:
```python
def test_gate_must_catch_this() -> None:
    assert False, "deliberate failure to prove verify_all.ps1 catches failing tests"
```
Run the Quick gate again. Expected: `PYTHON UNIT  FAILED (exit 1)`, `GATES FAILED: PYTHON UNIT`, `exit=1`.
Delete `tests/unit/test_gate_selfcheck.py` and run the Quick gate once more. Expected: `exit=0`.
Paste all three runs' SUMMARY blocks into the proof.

- [ ] **Step 11: Proof, progress, commit**

Write `docs/proof/P0-T2.md`. Set P0-T2 `DONE` in `docs/PROGRESS.md`.
```powershell
git add requirements.txt requirements-dev.txt pytest.ini tests scripts/__init__.py scripts/verify_all.ps1 docs/proof/P0-T1.md docs/proof/P0-T2.md docs/PROGRESS.md
git diff --cached --name-only
git commit -m "chore(test): add venv requirements, pytest harness and verify_all gate [P0-T2]" -m "Proof: docs/proof/P0-T2.md"
```
Include `docs/DECISIONS.md` in `git add` if you changed it.

**Acceptance criteria**
- `.venv/Scripts/python.exe -m pytest tests/unit -q` → `2 passed`.
- Quick gate exits 0 on clean tree and exits 1 when a unit test fails (both runs in proof).

---

## P0-T3: Ollama models and capability probe

**Goal:** Ollama is running, `qwen3:8b` and `nomic-embed-text` are pulled, and a probe proves the exact API features
JARVIS relies on: `think:false`, tool calls, tool-result round trip, streaming, embeddings.

**Depends on:** P0-T2.

**Files:**
- Create: `scripts/ensure_ollama.py`, `scripts/probe_llm.py`, `tests/live/__init__.py`,
  `tests/live/test_ollama_capabilities.py`, `docs/proof/P0-T3.md`, `docs/proof/P0-T3-probe.json`
- Modify: `docs/DECISIONS.md` (record model/thinking decisions)

**Interfaces — Produces:** `scripts.probe_llm.probe(base_url: str, model: str, embed_model: str) -> dict` with
keys `model`, `embed_model`, `think_false_supported: bool`, `embedding_dim: int`, `checks: dict[str, {"ok": bool, ...}]`.
`scripts/ensure_ollama.py [--check | --no-pull]` (exit 0 = ready).

- [ ] **Step 1: Write `scripts/ensure_ollama.py`**

```python
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
```

- [ ] **Step 2: Start the pull in the background and wait for it**

`qwen3:8b` is ~5 GB; do not run the pull in the foreground (tool timeouts).
```powershell
Start-Process -FilePath .venv/Scripts/python.exe -ArgumentList 'scripts/ensure_ollama.py' -WindowStyle Hidden `
  -RedirectStandardOutput docs/proof/tmp/ollama-pull.log -RedirectStandardError docs/proof/tmp/ollama-pull.err
```
Every 60 seconds (up to 90 minutes) run:
```powershell
.venv/Scripts/python.exe scripts/ensure_ollama.py --check; echo "exit=$LASTEXITCODE"
```
Expected when finished: `server: up`, `qwen3:8b: present`, `nomic-embed-text: present`, `exit=0`.
If `docs/proof/tmp/ollama-pull.err` shows a failure, retry once; if `qwen3:8b` cannot be pulled, use `qwen2.5:7b`
(set `$env:JARVIS_CHAT_MODEL='qwen2.5:7b'` for this task) and record it in `docs/DECISIONS.md`.

- [ ] **Step 3: Write the failing live test `tests/live/test_ollama_capabilities.py`**

```python
import json
import os

import pytest

from scripts.probe_llm import probe

pytestmark = pytest.mark.live

URL = os.environ.get("JARVIS_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("JARVIS_CHAT_MODEL", "qwen3:8b")
EMBED = os.environ.get("JARVIS_EMBED_MODEL", "nomic-embed-text")


def test_probe_reports_every_capability_ok() -> None:
    report = probe(URL, MODEL, EMBED)
    failed = {name: check for name, check in report["checks"].items() if not check["ok"]}
    assert not failed, json.dumps(failed, indent=2)
    assert report["embedding_dim"] > 0
```
Create empty `tests/live/__init__.py`.

Run: `.venv/Scripts/python.exe -m pytest tests/live/test_ollama_capabilities.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.probe_llm'`.

- [ ] **Step 4: Write `scripts/probe_llm.py`**

```python
"""Probe the local Ollama models for every capability JARVIS depends on."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

GET_TIME_TOOL = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "Get the current local date and time.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}
SYSTEM = {"role": "system", "content": "You are Jarvis. Call a tool whenever a tool can answer the question."}


def _body(model: str, messages: list[dict[str, Any]], *, think_false: bool, tools: list | None = None,
          stream: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"temperature": 0, "num_predict": 256},
    }
    if tools:
        body["tools"] = tools
    if think_false:
        body["think"] = False
    return body


def probe(base_url: str, model: str, embed_model: str) -> dict[str, Any]:
    report: dict[str, Any] = {"model": model, "embed_model": embed_model, "checks": {}}
    checks = report["checks"]
    with httpx.Client(base_url=base_url, timeout=300) as client:
        names = {m["name"] for m in client.get("/api/tags").json().get("models", [])}
        has = lambda n: n in names or f"{n}:latest" in names  # noqa: E731
        checks["models_present"] = {"ok": has(model) and has(embed_model), "installed": sorted(names)}

        think_false = True
        start = time.perf_counter()
        ping = [{"role": "user", "content": "Reply with exactly one word: pong"}]
        resp = client.post("/api/chat", json=_body(model, ping, think_false=True))
        if resp.status_code == 400 and "think" in resp.text.lower():
            think_false = False
            resp = client.post("/api/chat", json=_body(model, ping, think_false=False))
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        report["think_false_supported"] = think_false
        checks["plain_chat"] = {
            "ok": "pong" in content.lower() and "<think>" not in content,
            "content": content[:200],
            "seconds": round(time.perf_counter() - start, 2),
        }

        question = [SYSTEM, {"role": "user", "content": "What time is it right now?"}]
        hits, assistant_msg, attempts = 0, None, []
        for _ in range(3):
            start = time.perf_counter()
            msg = client.post(
                "/api/chat", json=_body(model, question, think_false=think_false, tools=[GET_TIME_TOOL])
            ).json()["message"]
            calls = msg.get("tool_calls") or []
            called = [c["function"]["name"] for c in calls]
            attempts.append({"called": called, "seconds": round(time.perf_counter() - start, 2)})
            if "get_time" in called:
                hits += 1
                assistant_msg = msg
        checks["tool_call"] = {"ok": hits >= 2, "hits": hits, "attempts": attempts}

        if assistant_msg is not None:
            follow = question + [
                assistant_msg,
                {"role": "tool", "tool_name": "get_time", "content": "The current local time is 14:05."},
            ]
            final = client.post("/api/chat", json=_body(model, follow, think_false=think_false,
                                                        tools=[GET_TIME_TOOL])).json()["message"]["content"]
            checks["tool_result_round_trip"] = {"ok": "14:05" in final or "2:05" in final, "content": final[:200]}
        else:
            checks["tool_result_round_trip"] = {"ok": False, "content": "no tool call to follow up"}

        chunks = 0
        story = [{"role": "user", "content": "Count from one to ten in words."}]
        with client.stream("POST", "/api/chat", json=_body(model, story, think_false=think_false, stream=True)) as s:
            for line in s.iter_lines():
                if line and json.loads(line).get("message", {}).get("content"):
                    chunks += 1
        checks["streaming"] = {"ok": chunks >= 2, "chunks": chunks}

        emb = client.post("/api/embed", json={"model": embed_model, "input": ["hello world", "goodbye"]}).json()
        vectors = emb.get("embeddings") or []
        report["embedding_dim"] = len(vectors[0]) if vectors else 0
        checks["embeddings"] = {
            "ok": len(vectors) == 2 and len(vectors[0]) == len(vectors[1]) > 0,
            "dim": report["embedding_dim"],
        }
    report["ok"] = all(c["ok"] for c in checks.values())
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("JARVIS_OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--model", default=os.environ.get("JARVIS_CHAT_MODEL", "qwen3:8b"))
    parser.add_argument("--embed-model", default=os.environ.get("JARVIS_EMBED_MODEL", "nomic-embed-text"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    report = probe(args.url, args.model, args.embed_model)
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the probe and the live test**

```powershell
.venv/Scripts/python.exe scripts/probe_llm.py --out docs/proof/P0-T3-probe.json; echo "exit=$LASTEXITCODE"
.venv/Scripts/python.exe -m pytest tests/live/test_ollama_capabilities.py -q
```
Expected: JSON with every `"ok": true`, `"ok": true` at the end, `exit=0`; pytest `1 passed`.

Decision rules (record each outcome in `docs/DECISIONS.md`):
- `think_false_supported` is false → P0-T4 sets `llm_disable_thinking` default to `False`.
- `tool_call.hits < 2` for `qwen3:8b` → `ollama pull qwen2.5:7b`, re-run the probe with `--model qwen2.5:7b`; if that
  passes, P0-T4 sets `chat_model` default to `qwen2.5:7b`.
- `plain_chat` fails only because `<think>` appears → keep the model; `LLMClient` strips think blocks (P2-T1).

- [ ] **Step 6: Gate, proof, progress, commit**

Run the Quick gate (exit 0). Write `docs/proof/P0-T3.md` (probe output + pytest output + `ensure_ollama.py --check`).
```powershell
git add scripts/ensure_ollama.py scripts/probe_llm.py tests/live docs/proof/P0-T3.md docs/proof/P0-T3-probe.json docs/PROGRESS.md docs/DECISIONS.md
git commit -m "chore(llm): pull local Ollama models and add capability probe [P0-T3]" -m "Proof: docs/proof/P0-T3.md"
```

**Acceptance criteria**
- `ensure_ollama.py --check` exits 0.
- Probe JSON: every check `ok`, embedding dimension recorded.
- Live test passes.

---

## P0-T4: `Settings` and `events` contracts

**Goal:** One typed settings object (no hardcoded values anywhere after this) and the event/state enums that
the backend and UI share, with a test that fails if the Python and TypeScript state lists ever drift apart.

**Depends on:** P0-T2 (and P0-T3 decisions for `chat_model` / `llm_disable_thinking` defaults).

**Files:**
- Create: `assistant/config.py`, `assistant/events.py`, `tests/unit/test_config.py`, `tests/unit/test_events.py`,
  `docs/proof/P0-T4.md`
- Modify: `tests/conftest.py` (autouse settings-cache fixture), `.env.example` (replace), `requirements.txt` (no change
  needed — `pydantic-settings` already listed)

**Interfaces — Produces:** exactly `docs/PLAN.md` §3.1 and §3.2.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_config.py`:
```python
from pathlib import Path

from assistant.config import Settings, get_settings


def test_defaults_match_plan() -> None:
    s = Settings(_env_file=None)
    assert s.ollama_url == "http://127.0.0.1:11434"
    assert s.chat_model == "qwen3:8b"  # change only if P0-T3 recorded a different model in DECISIONS.md
    assert s.embed_model == "nomic-embed-text"
    assert s.llm_backend == "ollama"
    assert s.max_agent_steps == 5
    assert s.server_host == "127.0.0.1"
    assert s.server_port == 8000
    assert s.whisper_model == "small.en"
    assert s.wake_model == "hey_jarvis"
    assert Path.home() / "Documents" in s.file_roots
    assert s.porcupine_access_key == ""


def test_env_prefix_overrides(monkeypatch) -> None:
    monkeypatch.setenv("JARVIS_CHAT_MODEL", "test-model")
    monkeypatch.setenv("JARVIS_VOICE_ENABLED", "false")
    monkeypatch.setenv("JARVIS_MAX_AGENT_STEPS", "3")
    s = Settings(_env_file=None)
    assert s.chat_model == "test-model"
    assert s.voice_enabled is False
    assert s.max_agent_steps == 3


def test_unprefixed_env_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("CHAT_MODEL", "should-not-apply")
    assert Settings(_env_file=None).chat_model != "should-not-apply"


def test_works_without_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert Settings().chat_model


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
```

`tests/unit/test_events.py`:
```python
import re
from pathlib import Path

from assistant.events import AssistantState, EventType

ROOT = Path(__file__).resolve().parents[2]


def test_assistant_states_match_frontend_store() -> None:
    source = (ROOT / "store" / "assistantStore.ts").read_text(encoding="utf-8")
    union = re.search(r"export type AssistantStatus\s*=\s*([^;]+);", source)
    assert union, "AssistantStatus union not found in store/assistantStore.ts"
    assert set(re.findall(r"'([a-z_]+)'", union.group(1))) == {s.value for s in AssistantState}


def test_event_types_match_protocol_table() -> None:
    assert {e.value for e in EventType} == {
        "state_change", "wake_word_detected", "user_transcript", "ai_response_delta", "ai_response",
        "tool_start", "tool_end", "permission_request", "reminder", "error",
    }


def test_enum_members_behave_as_plain_strings() -> None:
    assert EventType.STATE_CHANGE == "state_change"
    assert f"{AssistantState.EXECUTING_TOOL}" == "executing_tool"
    assert str(AssistantState.IDLE) == "idle"
```
Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_config.py tests/unit/test_events.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'assistant.config'`.

- [ ] **Step 2: Write `assistant/config.py`**

```python
"""Typed settings for JARVIS. Every tunable value lives here; override with JARVIS_* env vars or .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_file_roots() -> list[Path]:
    home = Path.home()
    return [home / "Documents", home / "Desktop", home / "Downloads"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_", env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore")

    ollama_url: str = "http://127.0.0.1:11434"
    chat_model: str = "qwen3:8b"
    embed_model: str = "nomic-embed-text"
    llm_backend: Literal["ollama", "fake"] = "ollama"
    llm_timeout_s: float = 120.0
    llm_disable_thinking: bool = True

    user_description: str = "Final-year engineering student"
    location_name: str = "Pimpri-Chinchwad, Maharashtra, India"
    latitude: float = 18.6298
    longitude: float = 73.7997
    timezone: str = "Asia/Kolkata"

    data_dir: Path = Path("data")
    models_dir: Path = Path("models")

    whisper_model: str = "small.en"
    whisper_device: Literal["auto", "cuda", "cpu"] = "auto"
    tts_voice: str = "bm_george"
    tts_speed: float = 1.1
    wake_model: str = "hey_jarvis"
    wake_threshold: float = 0.5
    vad_silence_ms: int = 600
    voice_enabled: bool = True

    server_host: str = "127.0.0.1"
    server_port: int = 8000

    max_agent_steps: int = 5
    history_max_chars: int = 12000
    permission_timeout_s: float = 30.0
    file_roots: list[Path] = Field(default_factory=_default_file_roots)
    mcp_config_path: Path = Path("mcp_servers.json")

    porcupine_access_key: str = ""  # legacy wake word only; removed in P3-T6


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```
Apply P0-T3 decisions to the `chat_model` / `llm_disable_thinking` defaults (and to the test) if any were recorded.

- [ ] **Step 3: Write `assistant/events.py`**

```python
"""Event and state names shared with the UI. Must match docs/PLAN.md §4 and store/assistantStore.ts."""
from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    STATE_CHANGE = "state_change"
    WAKE_WORD_DETECTED = "wake_word_detected"
    USER_TRANSCRIPT = "user_transcript"
    AI_RESPONSE_DELTA = "ai_response_delta"
    AI_RESPONSE = "ai_response"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    PERMISSION_REQUEST = "permission_request"
    REMINDER = "reminder"
    ERROR = "error"


class AssistantState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    RESPONDING = "responding"
    EXECUTING_TOOL = "executing_tool"


Emit = Callable[[str, Any], None]
```

- [ ] **Step 4: Add the autouse settings fixture to `tests/conftest.py`**

Append:
```python
from assistant.config import get_settings


@pytest.fixture(autouse=True)
def _fresh_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

- [ ] **Step 5: Replace `.env.example`**

```dotenv
# Every setting is optional. Defaults live in assistant/config.py.
# Copy this file to .env only to override something. Never put secrets in git.
JARVIS_OLLAMA_URL=http://127.0.0.1:11434
JARVIS_CHAT_MODEL=qwen3:8b
JARVIS_EMBED_MODEL=nomic-embed-text
JARVIS_LLM_BACKEND=ollama
JARVIS_LOCATION_NAME=Pimpri-Chinchwad, Maharashtra, India
JARVIS_LATITUDE=18.6298
JARVIS_LONGITUDE=73.7997
JARVIS_TIMEZONE=Asia/Kolkata
JARVIS_WHISPER_MODEL=small.en
JARVIS_WHISPER_DEVICE=auto
JARVIS_TTS_VOICE=bm_george
JARVIS_WAKE_MODEL=hey_jarvis
JARVIS_VOICE_ENABLED=true
JARVIS_SERVER_HOST=127.0.0.1
JARVIS_SERVER_PORT=8000
```

- [ ] **Step 6: Run tests**

Run: `.venv/Scripts/python.exe -m pytest tests/unit -q`
Expected: all pass (`10 passed` including the harness tests).

- [ ] **Step 7: Gate, proof, progress, commit, push (end of phase)**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add assistant/config.py assistant/events.py tests/conftest.py tests/unit/test_config.py tests/unit/test_events.py .env.example docs/proof/P0-T4.md docs/PROGRESS.md
git commit -m "feat(config): add typed Settings and shared event contracts [P0-T4]" -m "Proof: docs/proof/P0-T4.md"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1
git push origin testing
```
The full gate must exit 0 before the push (live probe test included). Paste both gate summaries into the proof
(the push output goes into P1-T1's commit as an appended section of `docs/proof/P0-T4.md`).

**Acceptance criteria**
- Tests above pass; state list contract test compares against the real TypeScript file.
- No `.env` file is required for any test.
