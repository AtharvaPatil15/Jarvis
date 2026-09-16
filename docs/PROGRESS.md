# Progress Tracker

Update this file in the **same commit** as each task. Status values: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`.
Find a task's commit with `git log --oneline --grep "<TASK-ID>"`. Proof files live in `docs/proof/`.

| ID | Task | Status | Date | Proof | Notes |
|---|---|---|---|---|---|
| P0-T1 | Git baseline on branch `testing` | DONE | 2026-09-14 | `docs/proof/P0-T1.md` | Branch `testing` built on `origin/main`; key removed; ignore rules added |
| P0-T2 | Python venv, test harness, `verify_all.ps1` | DONE | 2026-09-14 | `docs/proof/P0-T2.md` | Venv (3.12.4), harness, gate pass/fail proven |
| P0-T3 | Ollama models + capability probe | DONE | 2026-09-14 | `docs/proof/P0-T3.md` | Probe all ok; `think:false` supported; emb 768; live test passes |
| P0-T4 | `Settings` + `events.py` | DONE | 2026-09-14 | `docs/proof/P0-T4.md` | Settings + events; 10 unit tests pass; state contract vs TS |
| P1-T1 | Server app factory, event hub, crash fix, `FakeLLM` | DONE | 2026-09-14 | `docs/proof/P1-T1.md` | `create_app()` factory, ordered hub, conv_manager crash fix, FakeLLM; 27 unit pass; gate ok |
| P1-T2 | `voice_main.py` fix, key via settings, guard tests | DONE | 2026-09-14 | `docs/proof/P1-T2.md` | STT call fixed; key from settings; 5 guard tests pass; gate ok |
| P1-T3 | `user_text` over WS, state events, UI mapping, preload | DONE | 2026-09-14 | `docs/proof/P1-T3.md` | Ordered state sequence; WS tolerant of bad input; vitest/tsc/gate pass |
| P2-T1 | `LLMClient` (Ollama native, streaming, embeddings) | DONE | 2026-09-14 | `docs/proof/P2-T1.md` | LLMClient + _ThinkFilter; 15 unit + 4 live pass; gate ok (D-014 fix) |
| P2-T2 | `BaseTool`, `ToolRegistry`, `get_time`, `calculate` | DONE | 2026-09-14 | `docs/proof/P2-T2.md` | Typed tool framework, registry, get_time + safe calculator; 20 unit pass; gate ok |
| P2-T3 | `Session` + `build_system_prompt` | DONE | 2026-09-14 | `docs/proof/P2-T3.md` | Turn-safe session + spoken system prompt; 7 unit pass; gate ok |
| P2-T4 | Permission gates + `Orchestrator` agent loop | DONE | 2026-09-14 | `docs/proof/P2-T4.md` | Agent loop + permission gates; 18 new unit tests pass; gate ok |
| P2-T5 | `web_search`, `fetch_page`, `get_weather` | DONE | 2026-09-14 | `docs/proof/P2-T5.md` | Web + weather tools registered; 17 unit + 3 live pass; gate ok |
| P2-T6 | Orchestrator into server + live conversation proof | DONE | 2026-09-16 | `docs/proof/P2-T6.md` | Agent loop in server + CLI, legacy brain deleted; 116 unit + 4 live pass; transcript 391/782; backend -Stop tree fix (D-018); finished by Claude Code |
| P3-T1 | Model downloader + `Synthesizer` + sentence splitting | DONE | 2026-09-16 | `docs/proof/P3-T1.md` | Kokoro `bm_george` offline, sentence splitter/buffer, audio utils, downloader; 14 unit + 3 models pass; `/models/` ignore fix (D-019); finished by Claude Code |
| P3-T2 | `Transcriber` + TTS→STT round trip | DONE | 2026-09-16 | `docs/proof/P3-T2.md` | faster-whisper small.en on cuda/float16 (GPU libs installed); WER 0.111/0/0; RTF 0.021; 7 unit + 5 models pass; finished by Claude Code |
| P3-T3 | `SpeechSegmenter` (Silero VAD) | DONE | 2026-09-16 | `docs/proof/P3-T3.md` | Silero VAD (pysilero-vad 3.4.0) segments real Kokoro speech at pauses, silence+noise ignored; 5 unit + 3 models pass; finished by Claude Code |
| P3-T4 | `WakeWordDetector` (openWakeWord) | DONE | 2026-09-16 | `docs/proof/P3-T4.md` | Keyless `hey_jarvis` (openwakeword 0.6.0); 4/4 voices trigger (0.996–0.999), no trigger on silence/noise/speech at 0.5; 3 unit + 3 models pass; finished by Claude Code |
| P3-T5 | Audio IO, `EchoGuard`, `VoiceController` + barge-in | DONE | 2026-09-16 | `docs/proof/P3-T5.md` | Sources/sinks, echo guard, hands-free controller with streaming speech + barge-in; sentence-order bug in plan code fixed (D-020); 5+4+6 pass, controller 5/5 runs; finished by Claude Code |
| P3-T6 | Voice into server, remove old stack, latency proof | DONE | 2026-09-16 | `docs/proof/P3-T6.md` | Local voice pipeline in server (health voice:true), legacy Porcupine/Google/edge-tts/pygame removed; pipeline model test pass; median first audio 0.32 s (cuda); finished by Claude Code |
| P4-T1 | `MemoryDB` + `redact` + turn logging | DONE | 2026-09-16 | `docs/proof/P4-T1.md` | SQLite messages/facts/reminders, redaction before write, every turn logged; legacy memory modules removed; 6 db + 11 redact + 2 logging pass; tests isolated from ./data; finished by Claude Code |
| P4-T2 | `MemoryManager` remember/search/forget + prompt injection | DONE | 2026-09-16 | `docs/proof/P4-T2.md` | Embedded facts with near-duplicate skip, semantic search, forget; relevant facts injected into the system prompt, search failure never breaks a turn; 4 manager + 2 recall pass; finished by Claude Code |
| P4-T3 | Fact extraction + memory tools | DONE | 2026-09-16 | `docs/proof/P4-T3.md` | Background fact extraction after each reply; remember/recall/forget tools (forget needs permission); 7 extraction + 2 tool unit + 3 live pass; finished by Claude Code |
| P4-T4 | Restart-persistence live proof | DONE | 2026-09-16 | `docs/proof/P4-T4.md` | Live test remember→restart→recall→forget passes; two-process transcript recalls teal after a real restart (pid 29448 → 31000); finished by Claude Code |
| P5-T1 | `open_app`, `open_url`, `media_control` | DONE | 2026-09-16 | `docs/proof/P5-T1.md` | Start-menu shortcut resolution (uninstallers filtered), aliases, http/https-only URLs, media keys; 6 unit pass; test helper fix (D-024); finished by Claude Code |
| P5-T2 | `search_files`, `read_file` | DONE | 2026-09-16 | `docs/proof/P5-T2.md` | Name search inside Documents/Desktop/Downloads (excluded + hidden folders skipped), permission-gated text reading, traversal refused; 7 unit pass; newline fix (D-025); finished by Claude Code |
| P5-T3 | `read_screen` (OCR) | DONE | 2026-09-16 | `docs/proof/P5-T3.md` | Local RapidOCR reads the primary screen, permission-gated, untrusted header, 3000-char cap; 4 unit + 2 models pass; finished by Claude Code |
| P5-T4 | Reminders + scheduler | DONE | 2026-09-16 | `docs/proof/P5-T4.md` | Scheduler with background thread, reminder tools, UI events, voice speak; 7 tests pass |
| P5-T5 | `MCPBridge` (filesystem server proof) | DONE | 2026-09-16 | `docs/proof/P5-T5.md` | MCPBridge with echo + filesystem servers; 5 unit + 3 e2e pass; one failing server never blocks others |
| P5-T6 | `ToolSelector` + dead-code removal | DONE | 2026-09-16 | `docs/proof/P5-T6.md` | Embedding-based tool selection (k=12), fallback on failure, FakeLLM dim 256; dead code removed (ai-core, ui, install_ui_deps); 4 new unit tests + 223 existing pass; gate ok; UI build ok |
| P6-T1 | `lib/jarvisSocket.ts` + store + streaming UI | DONE | 2026-09-16 | `docs/proof/P6-T1.md` | Reconnecting socket with back-off, streaming deltas, permission/reminder state; 19 vitest pass; gate ok |
| P6-T2 | `CommandInput` + `PermissionPrompt` | DONE | 2026-09-16 | `docs/proof/P6-T2.md` | Typed commands, permission prompt with Allow/Deny, jsdom tests pass; vitest+react plugin; gate ok |
| P6-T3 | Playwright end-to-end with screenshots | DONE | 2026-09-16 | `docs/proof/P6-T3.md` | 3 browser tests pass (typed command, permission allow/deny), screenshots captured; FakeLLM /tool hook; gate ok |
| P6-T4 | `start_jarvis.ps1` launcher | DONE | 2026-09-16 | `docs/proof/P6-T4.md` | One-command start/stop (real launch llm+voice true), Electron smoke loads UI; 2 e2e pass; launcher-test pipe hang and truthy `Wait-Http` fixed (D-026); finished by Claude Code |
| P6-T5 | Eval suite ≥ 85 % | DONE | 2026-09-16 | `docs/proof/P6-T5.md` | 28/28 pass (100%); injection guard OK; report committed |
| P6-T6 | Cleanup, README, final verification, push | TODO | | | |

## Blocked items

_None yet. For each BLOCKED task record: the exact error output, the three attempts made, and what would unblock it._

## Push log

| Date | After task | `git rev-parse HEAD` | `git ls-remote --heads origin testing` matches |
|---|---|---|---|
| 2026-09-16 | P2-T6 (end of phase 2; first successful push since P0-T4, see D-013/D-015) | `59af2e84ec41558c2e42310712df1544e2ca214d` | yes |
| 2026-09-16 | P3-T4 (end of phase 3a: P3-T1..P3-T4; full gate `verify-20260916-011339.log`) | `7830c5e0738fb1ae88248b632dc8a849ca668dc1` | yes |
| 2026-09-16 | P3-T6 (end of phase 3; full gate `verify-20260916-012709.log`) | `572ccfb80686b4d2a88f0fe3a74206d7617a5812` | yes |
| 2026-09-16 | P4-T4 (end of phase 4; full gate `verify-20260916-094107.log`) | `2921f78701d00a0c589097e9694dfcedb9b5f41e` | yes |
| 2026-09-16 | P5-T3 (after P5-T1..P5-T3; full gate `verify-20260916-095250.log`) | `eea4718176aef76a1859016f759a96d15b76bfe5` | yes |
| 2026-09-16 | P5-T6 (end of phase 5; full gate `verify-20260916-104348.log`) | `f136284` | yes |
