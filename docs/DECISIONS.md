# Decisions Log

Append one entry per decision. Never edit or delete old entries — add a new one that supersedes it.

Format:
```
## D-NNN — <short title>
- Date: YYYY-MM-DD
- Task: <TASK-ID or "planning">
- Decision: <what was chosen>
- Reason: <why, with evidence>
- Alternatives rejected: <what and why>
```

---

## D-001 — Keep the flat layout; do not adopt the `origin/Test` monorepo
- Date: 2026-09-13
- Task: planning
- Decision: Build on the current folder (`assistant/`, Next.js at root, `electron/`). Branch `testing` starts from `origin/main`.
- Reason: The local folder holds the newest UI work (e.g. `OrbitalRings.tsx`, June 2026 edits) and builds cleanly. `origin/Test`
  moves every file into `apps/*`; its backend additions (keyword planner, 2-sentence regex truncation, dict tool registry)
  are superseded by P2 tasks. Its useful fixes (`conv_manager` wiring, Electron `preload.js`) are ported in P1.
- Alternatives rejected: Rebase onto `origin/Test` (high churn, conflicts with every task, no functional gain).

## D-002 — Ollama instead of LM Studio
- Date: 2026-09-13
- Task: planning
- Decision: All LLM calls go to Ollama's native API (`/api/chat`, `/api/embed`).
- Reason: Owner requires zero manual steps. Ollama 0.34 is installed, starts headless (`ollama serve`), pulls models from the
  command line, supports tools, streaming, `think:false`, and embeddings in one server.
- Alternatives rejected: LM Studio (needs the GUI or extra CLI setup; owner will not launch it).

## D-003 — `qwen3:8b` as the default chat model
- Date: 2026-09-13
- Task: planning
- Decision: Default `chat_model = qwen3:8b`, fallback `qwen2.5:7b` if P0-T3's probe shows unreliable tool calls.
- Reason: 8 GB VRAM (RTX 5060 Laptop). The previous 14B model does not fit alongside Whisper on the GPU. Qwen3 8B has native
  tool calling.
- Alternatives rejected: Qwen 2.5 14B (VRAM), llama3.2:3b (weak tool calling).

## D-004 — openWakeWord replaces Porcupine; no API keys anywhere
- Date: 2026-09-13
- Task: planning
- Decision: Wake word "hey jarvis" via openWakeWord (bundled pre-trained model, no key). Porcupine is removed in P3-T6.
- Reason: Keyless operation is a hard requirement; the old Porcupine access key is also exposed in public git history.
- Alternatives rejected: Porcupine custom "jarvis" keyword (requires a Picovoice account and key).

## D-005 — Leaked Porcupine key is not scrubbed from git history
- Date: 2026-09-13
- Task: planning
- Decision: Remove the key from the working tree (P0-T1) and stop using Porcupine (P3-T6). Do not rewrite history.
- Reason: Scrubbing needs a force-push to `main`, which the owner has not authorised and `AGENTS.md` forbids. Once Porcupine is
  gone the key has no function in this project. Revoking it in the Picovoice console is an owner-only action.
- Alternatives rejected: `git filter-repo` + force-push (destructive to shared history).

## D-006 — Speech stack
- Date: 2026-09-13
- Task: planning
- Decision: faster-whisper `small.en` (CUDA float16, automatic CPU int8 fallback), Kokoro via `kokoro-onnx` (CPU, British male voice
  `bm_george`), Silero VAD for endpointing, sentence-level TTS streaming, barge-in with echo suppression.
- Reason: All local and keyless; replaces cloud Google STT and edge-tts, removes the network round trips, and allows interruption.
- Alternatives rejected: Speech-to-speech models (not viable on 8 GB alongside a tool-calling LLM).

## D-007 — OpenCode developer model and provider timeout
- Date: 2026-09-13
- Task: planning (setup verification)
- Decision: OpenCode uses `nvidia/deepseek-ai/deepseek-v4-flash-0731` for both `model` and `small_model` (project `opencode.json`),
  with `provider.nvidia.options.headerTimeout = 120000`.
- Reason: Live checks on 13 Sep 2026 against the owner's NVIDIA key. The global default `nvidia/minimaxai/minimax-m3` and
  `deepseek-v4-pro`, `minimax-m2.7`, `glm-5.2`, `qwen3-coder-480b`, `qwen3.5-397b`, `gpt-oss-120b` all return HTTP 410 (end of
  life); `glm-5.3-flash` returns 404. `deepseek-v4-flash-0731` completed a read + PowerShell pipe test in 3.9 s.
  `deepseek-v4-pro-0813` works but took 178 s and `kimi-k3` 506 s for the same test. NVIDIA's free endpoint sometimes sends no
  response headers for 5 minutes; a 2-minute header timeout makes OpenCode retry sooner.
- Alternatives rejected: `deepseek-v4-pro-0813` (too slow for a long autonomous run), `kimi-k3` (too slow).

## D-008 — Offline fallback through an autopilot supervisor
- Date: 2026-09-13
- Task: planning (setup verification)
- Decision: Add an `ollama` provider with `qwen3-8b-32k` (qwen3:8b with `num_ctx 32768`, `scripts/ollama/qwen3-8b-32k.Modelfile`)
  and run OpenCode through `scripts/opencode_autopilot.ps1`, which picks the cloud or local model before each session,
  restarts a session on the local model after 3 consecutive provider errors (for 20 minutes), restarts stalled sessions,
  and keeps starting new sessions until `docs/PROGRESS.md` is all DONE/BLOCKED.
- Reason: OpenCode 1.18.30's config schema has no fallback, retry or failover setting (checked 13 Sep 2026). Running the
  supervisor outside OpenCode needs no API keys and also covers OpenCode ending its turn early. OpenCode's docs recommend
  16k–32k context for tool calling with Ollama; qwen3:8b fits the 8 GB GPU.
- Limits: the local 8B model writes weaker code and has no internet, so offline sessions are told to do offline coding and
  tests only and leave network steps as PENDING-NETWORK for the next cloud session.
- Alternatives rejected: a LiteLLM proxy with router fallbacks (would require copying the owner's NVIDIA key into another
  config file); switching models by hand (not autonomous).

## D-009 — Model and fallback settings are global and self-healing
- Date: 2026-09-14
- Task: planning (setup hardening, requested by the owner for every project)
- Decision: Model, small_model, the NVIDIA header timeout and the Ollama provider live only in the global config
  (`%USERPROFILE%\.config\opencode\opencode.json`); this project's `opencode.json` keeps only instructions and permissions.
  `%USERPROFILE%\.opencode-kit\` holds `opencode-doctor` (replaces retired models using `model-preferences.json`, keeps the
  local fallback model present) and the general `opencode-autopilot`; both are on PATH via `%APPDATA%\npm`. The doctor runs
  daily from Task Scheduler and before every autopilot run. Autopilot's consecutive-error trigger is 4 (was 3).
- Reason: NVIDIA retired seven models between June and September 2026; a model pinned in a project would override any
  global repair and break again. Three errors in a row also switched away from NVIDIA moments before it recovered in testing.
- Alternatives rejected: pinning the model per project (breaks on every retirement).

## D-010 — Offline work is a draft that the cloud model must review
- Date: 2026-09-14
- Task: planning (evidence from a controlled trial)
- Decision: In `opencode-autopilot`'s default `-OfflineMode review`, local-model sessions may write code but must not commit
  or mark tasks DONE (tasks stay IN_PROGRESS with OFFLINE-DRAFT). The autopilot records the commit where offline work began;
  the next cloud session is told to review and fix everything since that commit before continuing. `-OfflineMode pause`
  disables offline coding entirely.
- Reason: In a three-task sandbox trial on 13–14 Sep 2026 the cloud model wrote a correct AST-whitelist calculator that
  passed its tests, while `qwen3-8b-32k` on the same task used `eval()` (explicitly forbidden), left arbitrary code execution
  open, broke the constants `e`/`pi` with string replacement, and hung its own tests on `9 ** 9 ** 9`.
- Alternatives rejected: trusting local-model output (unsafe); removing the offline fallback (the owner wants work to
  continue when the network or API fails).

## D-011 — Leave the cloud model only when it is unreachable or silent for about 15 minutes
- Date: 2026-09-14
- Task: planning (evidence from a controlled trial); supersedes the error trigger in D-009
- Decision: `opencode-autopilot` stops a cloud session after 2 consecutive model errors only if the provider's health URL is
  unreachable; otherwise it keeps waiting until 8 consecutive errors (`-MaxConsecutiveErrors 8`).
- Reason: The cloud trial on 13–14 Sep 2026 finished all three tasks (27/27 visible and 23/23 hidden tests) despite 29 of
  57 requests failing, all `ProviderHeaderTimeoutError`. Error streaks were 1×7, 2×4, 3×2 and 4×2, each recovering within
  7 minutes. A trigger of 4 would have abandoned a working session twice for 20 minutes of weaker offline drafts.
- Alternatives rejected: keeping 4 (needless fallbacks); no limit at all (a dead provider would stall work forever).

## D-012 — P0-T3 probe confirms `qwen3:8b` + `nomic-embed-text` defaults
- Date: 2026-09-14
- Task: P0-T3
- Decision: Keep `chat_model = qwen3:8b`, `embed_model = nomic-embed-text`, and `llm_disable_thinking = True` as the defaults
  for P0-T4. No fallback model is needed.
- Reason: The probe against the live Ollama server passed every capability check: `think_false_supported = true`, plain chat
  returned "pong" with no thinking block, tool_call hit 3/3 on `get_time`, the tool-result round trip returned the injected
  time, streaming produced 20 chunks, and embeddings returned dimension 768 for both inputs.
- Alternatives rejected: `qwen2.5:7b` (not needed — `qwen3:8b` tool calls were reliable), `llm_disable_thinking = False`
  (the model honours `think:false`).
