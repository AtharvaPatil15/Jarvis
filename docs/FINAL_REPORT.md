# JARVIS — Final Report

- Date: 2026-09-16 (local)
- Branch: `testing` (https://github.com/AtharvaPatil15/Jarvis/tree/testing)
- Built by OpenCode (developer) with Claude Code as checker, and Claude Code standing in as developer for parts of
  phases 2–6 (marked "finished by Claude Code" in `docs/PROGRESS.md`).
- All verification output below was produced on 2026-09-16 between 23:30 and 23:36 IST on the owner's machine
  (Windows 11, Python 3.12.4, Node 22.20.0, npm 11.7.0, Ollama 0.34.0).

## Definition of done (`docs/PLAN.md` §6)

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | `scripts/verify_all.ps1` exits 0 | **Pass** — `ALL GATES PASSED` | log `docs/proof/tmp/verify-20260916-233047.log` (section below) |
| 2 | Evals ≥ 85 % with the live model | **Pass** — 28/28 (100 %) | `docs/proof/P6-T6-evals.md` |
| 3 | Voice round-trip WER ≤ 0.15 | **Pass** — 0.111, 0.000, 0.000 | `tests/models/test_stt_models.py` output below |
| 4 | Memory persists across a backend restart | **Pass** | `tests/live/test_memory_persistence_live.py` output below; P4-T4 two-process transcript |
| 5 | No Porcupine key, `recognize_google`, `edge_tts`, `pvporcupine` | **Pass** — both greps print nothing | section below |
| 6 | Launcher brings up Ollama + backend + UI + Electron; `/health` ok | **Pass** — `{"status":"ok","llm":true,"voice":true}`; Electron smoke test passes in the e2e gate | section below |
| 7 | All work on `origin/testing`; `main` and `Test` untouched | **Pass** — `main` `d31dfb6…`, `Test` `a27b32d…` equal P0-T1 | section below; push recorded in `docs/PROGRESS.md` |

## Tasks

No task is `BLOCKED`.

| ID | Task | Status | Commit(s) |
|---|---|---|---|
| P0-T1 | Git baseline on branch `testing` | DONE | `3ffedaa` |
| P0-T2 | Python venv, test harness, `verify_all.ps1` | DONE | `2038fbc` |
| P0-T3 | Ollama models + capability probe | DONE | `21a83a1` |
| P0-T4 | `Settings` + `events.py` | DONE | `c46818f` |
| P1-T1 | Server app factory, event hub, crash fix, `FakeLLM` | DONE | `9fdf4df` |
| P1-T2 | `voice_main.py` fix, key via settings, guard tests | DONE | `caf6631` |
| P1-T3 | `user_text` over WS, state events, UI mapping, preload | DONE | `6402893`, `8e6c3e7` |
| P2-T1 | `LLMClient` (Ollama native, streaming, embeddings) | DONE | `e50f1ba` |
| P2-T2 | `BaseTool`, `ToolRegistry`, `get_time`, `calculate` | DONE | `92500b5` |
| P2-T3 | `Session` + `build_system_prompt` | DONE | `830f099` |
| P2-T4 | Permission gates + `Orchestrator` agent loop | DONE | `2b15364` |
| P2-T5 | `web_search`, `fetch_page`, `get_weather` | DONE | `02e89c4` |
| P2-T6 | Orchestrator into server + live conversation proof | DONE | `59af2e8` (`836e42b` config fix) |
| P3-T1 | Model downloader + `Synthesizer` + sentence splitting | DONE | `7b9b59b` |
| P3-T2 | `Transcriber` + TTS→STT round trip | DONE | `411e978` |
| P3-T3 | `SpeechSegmenter` (Silero VAD) | DONE | `dd244b8` |
| P3-T4 | `WakeWordDetector` (openWakeWord) | DONE | `7830c5e` |
| P3-T5 | Audio IO, `EchoGuard`, `VoiceController` + barge-in | DONE | `bfe6e01` |
| P3-T6 | Voice into server, remove old stack, latency proof | DONE | `572ccfb` |
| P4-T1 | `MemoryDB` + `redact` + turn logging | DONE | `4056412` |
| P4-T2 | `MemoryManager` remember/search/forget + prompt injection | DONE | `5eb1452` |
| P4-T3 | Fact extraction + memory tools | DONE | `4679567` |
| P4-T4 | Restart-persistence live proof | DONE | `2921f78` |
| P5-T1 | `open_app`, `open_url`, `media_control` | DONE | `8156ce6` |
| P5-T2 | `search_files`, `read_file` | DONE | `225fb6c` |
| P5-T3 | `read_screen` (OCR) | DONE | `eea4718` |
| P5-T4 | Reminders + scheduler | DONE | `09be236` |
| P5-T5 | `MCPBridge` (filesystem server proof) | DONE | `d067037` |
| P5-T6 | `ToolSelector` + dead-code removal | DONE | `3900ea8`, `f136284` |
| P6-T1 | `lib/jarvisSocket.ts` + store + streaming UI | DONE | `5adc0ce` |
| P6-T2 | `CommandInput` + `PermissionPrompt` | DONE | `11ae3cd` |
| P6-T3 | Playwright end-to-end with screenshots | DONE | `931f6f5` |
| P6-T4 | `start_jarvis.ps1` launcher | DONE | `a8b6eeb` |
| P6-T5 | Eval suite ≥ 85 % | DONE | `47f3baa` |
| P6-T6 | Cleanup, README, final verification, push | DONE | this commit (`git log --oneline --grep "\[P6-T6\]"`) |

## Numbers

| Measure | Value |
|---|---|
| Python unit tests | 231 passed (40 deselected) |
| Python `live` tests | 17 passed, 1 xfailed |
| Python `models` tests | 17 passed |
| Python `e2e` tests | 5 passed |
| Vitest | 25 passed (5 files) |
| Playwright | 3 passed |
| Eval pass rate | 28/28 = 100 % (threshold 85 %); injection case called only `search_files`, `read_file` |
| Voice latency (3 runs) | median transcript 0.21 s; median first audio 1.50 s (limit 5 s, target 3 s) |
| Whisper | `small.en` on `cuda/float16`; real-time factor 0.033 |
| Round-trip WER | 0.111, 0.000, 0.000 (limit 0.15) |

### Full gate
Command: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1` — exit 0
```
231 passed, 40 deselected, 1 warning in 12.99s
 Test Files  5 passed (5)
      Tests  25 passed (25)
17 passed, 253 deselected, 1 xfailed, 1 warning in 48.57s
17 passed, 254 deselected, 2 warnings in 30.81s
5 passed, 266 deselected, 1 warning in 27.29s
  3 passed (10.0s)
=== SUMMARY ===
FORBIDDEN PATHS            ok
SECRET SCAN (index)        ok
SECRET SCAN (untracked)    ok
PYTHON UNIT                ok
TYPESCRIPT                 ok
VITEST                     ok
OLLAMA READY               ok
PYTHON LIVE                ok
PYTHON MODELS              ok
PYTHON E2E                 ok
NEXT BUILD                 ok
PLAYWRIGHT                 ok
log: docs/proof/tmp/verify-20260916-233047.log
ALL GATES PASSED
```

### Evals
Command: `.venv/Scripts/python.exe scripts/run_evals.py --report docs/proof/P6-T6-evals.md` — exit 0 (73 s)
```
PASS time-now (3.6s) tools=['get_time']
PASS date-today (1.9s) tools=['get_time']
PASS maths-multiply (1.8s) tools=['calculate']
PASS maths-sqrt (2.1s) tools=['calculate']
PASS maths-follow-up (3.1s) tools=['calculate']
PASS time-and-maths (2.3s) tools=['get_time', 'calculate']
PASS weather-home (4.1s) tools=['get_weather']
PASS weather-city (3.1s) tools=['get_weather']
PASS web-fact (4.7s) tools=['web_search']
PASS web-news (4.9s) tools=['web_search']
PASS remember-food (1.8s) tools=['remember']
PASS recall-friend (2.7s) tools=[]
PASS forget-locker (5.9s) tools=['recall', 'forget']
PASS files-search (2.0s) tools=['search_files']
PASS files-read (3.1s) tools=['search_files', 'read_file']
PASS files-read-denied (2.5s) tools=['search_files', 'read_file']
PASS injection-guard (3.6s) tools=['search_files', 'read_file']
PASS open-app (1.6s) tools=['open_app']
PASS open-url (1.8s) tools=['open_url']
PASS volume-up (1.9s) tools=['media_control']
PASS pause-music (1.4s) tools=['media_control']
PASS screen-error (1.7s) tools=['read_screen']
PASS reminder-relative (1.8s) tools=['set_reminder']
PASS reminder-tomorrow (2.0s) tools=['set_reminder']
PASS reminder-list (3.5s) tools=['list_reminders']
PASS chat-joke (1.4s) tools=[]
PASS chat-greeting (1.1s) tools=[]
PASS chat-explain (1.4s) tools=[]
pass rate 100% (28/28), report: docs\proof\P6-T6-evals.md
```
The P6-T5 run (OpenCode, same day, while OpenCode shared the machine) also scored 28/28, at 6–43 s per case.

### Voice latency
Command: `.venv/Scripts/python.exe scripts/voice_latency.py 3` — exit 0
```
whisper device: cuda/float16
run 1: transcript 0.21 s, first audio 2.10 s
run 2: transcript 0.18 s, first audio 1.28 s
run 3: transcript 0.31 s, first audio 1.50 s
median transcript 0.21 s, median first audio 1.50 s (limit 5.0 s, target 3.0 s)
```

### Speech recognition round trip
Command: `.venv/Scripts/python.exe -m pytest tests/models/test_stt_models.py -q -s` — exit 0
```
device=cuda/float16 wer=0.111 hyp='Jarvis, what is the weather like in Puna today?'
.device=cuda/float16 wer=0.000 hyp='Set a reminder to call my mother this evening.'
.device=cuda/float16 wer=0.000 hyp='Open the file called project notes and read me the summary.'
..real-time factor 0.033 on cuda
.
5 passed in 5.81s
```

### Memory persistence
Command: `.venv/Scripts/python.exe -m pytest tests/live/test_memory_persistence_live.py -q` — exit 0
```
1 passed, 1 warning in 5.83s
```

### Legacy code and leaked key
```
git grep -nE "pvporcupine|recognize_google|edge_tts|pygame" -- "*.py" "requirements*.txt"
(no output)
git grep -n ("ycGaIQ" + "bL2ZWI8r2M")
(no output)
```

### Launcher
```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_jarvis.ps1 -NoElectron   (exit 0)
server: up
qwen3:8b: present
nomic-embed-text: present
backend ready: http://127.0.0.1:8000/health
(next build output — the gate's build had been replaced, so the launcher rebuilt the UI)
ui ready: http://127.0.0.1:3000
JARVIS is running without a window. Stop it with: scripts/start_jarvis.ps1 -Stop

Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Compress
{"status":"ok","llm":true,"voice":true}

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_jarvis.ps1 -Stop   (exit 0)
stopped ui (pid 35340)
stopped backend (pid 10280)
backend down
ui down
```
The Electron window is covered by `tests/e2e/test_launcher_e2e.py::test_electron_window_loads_the_ui`
(`ELECTRON_SMOKE_OK`), which ran inside the full gate.

### Remote branches
```
git ls-remote --heads origin   (before the final push)
a27b32dedd7347740a1a139839e329b30e3d37ac	refs/heads/Test
d31dfb67f3e936f7e6e0d7f0b8de2c3249062bb7	refs/heads/main
931f6f564ad92fe659e4a0d0e2d576a302d54616	refs/heads/testing
```
`main` and `Test` equal the hashes recorded in `docs/proof/P0-T1.md`. The final push is recorded in the
`docs/PROGRESS.md` push log.

## Decisions (`docs/DECISIONS.md`)

- D-001 — Keep the flat layout; do not adopt the `origin/Test` monorepo
- D-002 — Ollama instead of LM Studio
- D-003 — `qwen3:8b` as the default chat model
- D-004 — openWakeWord replaces Porcupine; no API keys anywhere
- D-005 — Leaked Porcupine key is not scrubbed from git history
- D-006 — Speech stack
- D-007 — OpenCode developer model and provider timeout
- D-008 — Offline fallback through an autopilot supervisor
- D-009 — Model and fallback settings are global and self-healing
- D-010 — Offline work is a draft that the cloud model must review
- D-011 — Leave the cloud model only when it is unreachable or silent for about 15 minutes
- D-012 — P0-T3 probe confirms `qwen3:8b` + `nomic-embed-text` defaults
- D-013 — P1 phase-end `git push origin testing` is blocked by the permission config
- D-014 — Two bugs in the P2-T1 plan's provided code/test were fixed
- D-015 — Owner's checker fixed the push rule and repaired an unreviewed offline edit (supersedes D-013)
- D-016 — A stalled cloud model is replaced, not only a retired one
- D-017 — Tests removed with the legacy brain in P2-T6
- D-018 — `backend.ps1 -Stop` stops the whole process tree
- D-019 — Ignore only the root `models/` folder
- D-020 — `VoiceController` queues every spoken sentence through one scheduling channel
- D-021 — Tests removed with the legacy voice stack in P3-T6
- D-022 — P3-T6 legacy grep uses whole-word matching
- D-023 — P4-T1 importer check excludes the files being deleted
- D-024 — P5-T1 test helper `shortcuts()` must be reusable
- D-025 — `read_file` normalises Windows line endings
- D-026 — Launcher test reads output through a file; `Wait-Http` prints with `Write-Host`

## Known limitations

- **Barge-in** works best with a headset; with open speakers the echo guard can miss or delay an interruption.
- **Wake word** uses the stock `hey_jarvis` model at threshold 0.5; sensitivity may need tuning for your microphone
  and room (`JARVIS_WAKE_THRESHOLD`).
- **Evals** fake every OS side effect (apps, URLs, media keys, screen capture); the real actions are covered by the unit
  and model tests, not by the eval suite. Web and weather answers depend on live internet results.
- **Model quality**: `qwen3:8b` sometimes offers follow-ups ("Would you like me to open it?") and its news summaries can
  be out of date; it is a local 8B model.
- **Permissions**: opening apps and URLs and pressing media keys run without a prompt by design (see `SECURITY.md`).
- **Leaked key**: the old Porcupine key remains in early `main` history (D-005) and should be revoked by the owner.
- **First launch** runs `npm run build` when no production build exists, which adds about a minute.

## How to run JARVIS

```powershell
# one-time setup
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt -r requirements-dev.txt
npm install
.venv/Scripts/python.exe scripts/ensure_ollama.py
.venv/Scripts/python.exe scripts/download_models.py

# start (desktop window; closing it stops everything)
start_jarvis.bat
# or without a window, and stop explicitly
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_jarvis.ps1 -NoElectron
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_jarvis.ps1 -Stop

# text-only
.venv/Scripts/python.exe main.py
```
