# Progress Tracker

Update this file in the **same commit** as each task. Status values: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`.
Find a task's commit with `git log --oneline --grep "<TASK-ID>"`. Proof files live in `docs/proof/`.

| ID | Task | Status | Date | Proof | Notes |
|---|---|---|---|---|---|
| P0-T1 | Git baseline on branch `testing` | DONE | 2026-09-14 | `docs/proof/P0-T1.md` | Branch `testing` built on `origin/main`; key removed; ignore rules added |
| P0-T2 | Python venv, test harness, `verify_all.ps1` | DONE | 2026-09-14 | `docs/proof/P0-T2.md` | Venv (3.12.4), harness, gate pass/fail proven |
| P0-T3 | Ollama models + capability probe | DONE | 2026-09-14 | `docs/proof/P0-T3.md` | Probe all ok; `think:false` supported; emb 768; live test passes |
| P0-T4 | `Settings` + `events.py` | DONE | 2026-09-14 | `docs/proof/P0-T4.md` | Settings + events; 10 unit tests pass; state contract vs TS |
| P1-T1 | Server app factory, event hub, crash fix, `FakeLLM` | TODO | | | |
| P1-T2 | `voice_main.py` fix, key via settings, guard tests | TODO | | | |
| P1-T3 | `user_text` over WS, state events, UI mapping, preload | TODO | | | |
| P2-T1 | `LLMClient` (Ollama native, streaming, embeddings) | TODO | | | |
| P2-T2 | `BaseTool`, `ToolRegistry`, `get_time`, `calculate` | TODO | | | |
| P2-T3 | `Session` + `build_system_prompt` | TODO | | | |
| P2-T4 | Permission gates + `Orchestrator` agent loop | TODO | | | |
| P2-T5 | `web_search`, `fetch_page`, `get_weather` | TODO | | | |
| P2-T6 | Orchestrator into server + live conversation proof | TODO | | | |
| P3-T1 | Model downloader + `Synthesizer` + sentence splitting | TODO | | | |
| P3-T2 | `Transcriber` + TTS→STT round trip | TODO | | | |
| P3-T3 | `SpeechSegmenter` (Silero VAD) | TODO | | | |
| P3-T4 | `WakeWordDetector` (openWakeWord) | TODO | | | |
| P3-T5 | Audio IO, `EchoGuard`, `VoiceController` + barge-in | TODO | | | |
| P3-T6 | Voice into server, remove old stack, latency proof | TODO | | | |
| P4-T1 | `MemoryDB` + `redact` + turn logging | TODO | | | |
| P4-T2 | `MemoryManager` remember/search/forget + prompt injection | TODO | | | |
| P4-T3 | Fact extraction + memory tools | TODO | | | |
| P4-T4 | Restart-persistence live proof | TODO | | | |
| P5-T1 | `open_app`, `open_url`, `media_control` | TODO | | | |
| P5-T2 | `search_files`, `read_file` | TODO | | | |
| P5-T3 | `read_screen` (OCR) | TODO | | | |
| P5-T4 | Reminders + scheduler | TODO | | | |
| P5-T5 | `MCPBridge` (filesystem server proof) | TODO | | | |
| P5-T6 | `ToolSelector` + dead-code removal | TODO | | | |
| P6-T1 | `lib/jarvisSocket.ts` + store + streaming UI | TODO | | | |
| P6-T2 | `CommandInput` + `PermissionPrompt` | TODO | | | |
| P6-T3 | Playwright end-to-end with screenshots | TODO | | | |
| P6-T4 | `start_jarvis.ps1` launcher | TODO | | | |
| P6-T5 | Eval suite ≥ 85 % | TODO | | | |
| P6-T6 | Cleanup, README, final verification, push | TODO | | | |

## Blocked items

_None yet. For each BLOCKED task record: the exact error output, the three attempts made, and what would unblock it._

## Push log

| Date | After task | `git rev-parse HEAD` | `git ls-remote --heads origin testing` matches |
|---|---|---|---|
