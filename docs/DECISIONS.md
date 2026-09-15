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

## D-013 — P1 phase-end `git push origin testing` is blocked by the permission config
- Date: 2026-09-14
- Task: P1-T3 (phase-end push)
- Decision: Do not push after P1-T3. `git push origin testing` is rejected by `opencode.json` because the deny rule
  `git push origin Test*` is matched case-insensitively and so also matches the branch `testing`. Leave the two committed
  phase-1 commits unpushed and retry `git push origin testing` after each later phase.
- Reason: `opencode.json` has `"git push origin Test*": "deny"` and the permission matcher is case-insensitive, so it catches
  `testing`. `AGENTS.md` §5 forbids touching `Test`/`main` and forbids editing `opencode.json` model settings; bypassing the
  deny rule (e.g. `git push origin refs/heads/testing`) would defeat a security control the owner configured, so it was not
  attempted. The branch `testing` is the required, safe target; this is purely a rule-matching overreach, not a history rewrite.
- Alternatives rejected: pushing `refs/heads/testing` (would circumvent the deny control), editing `opencode.json` to fix the
  pattern (owner-owned config; changing a deny into an allow is not mine to make).

## D-014 — Two bugs in the P2-T1 plan's provided code/test were fixed
- Date: 2026-09-14
- Task: P2-T1
- Decision: (a) `_partial_suffix` in `assistant/brain/llm.py` now only treats a partial opening-tag suffix as worth holding back
  when it is at least 2 characters (`range(..., 1, -1)` instead of `range(..., 0, -1)`). (b) The streaming think-split test
  fixture used a non-standard ` thinking` tag; changed the chunk contents to `" thi"` / `"nking\n response"` so it forms a real
  ` thinking…response` block, matching `_OPEN`/`_CLOSE` and the non-stream strip regex.
- Reason: As provided, the plan's implementation failed two of its own unit tests. A single trailing space matches the 1-char
  prefix of `" thinking"`, so `_partial_suffix` wrongly withheld `"The "`'s space and it leaked into later chunks
  (`['The', ' answer', ' is 4.']`). Separately, the fixture joined to `" thinkingsecret responseHi"`, which the
  ` thinking…response` filter cannot strip (no leading space before "think"), so no ` thinking…response` span ever formed.
  Fixing both makes the implementation and tests mutually consistent without weakening any assertion.
- Alternatives rejected: implementing a second ` thinking`-tag stripping path (the model is told `think:false`; the plan's
  single ` thinking…response` format is the documented contract), weakening the streaming fidelity assertion (wrong).

## D-015 — Owner's checker fixed the push rule and repaired an unreviewed offline edit (supersedes D-013)
- Date: 2026-09-15
- Task: P2-T6 (made by the owner's checker, not by OpenCode)
- Decision: (a) `opencode.json` now denies only the exact branch `Test` (`git push origin Test`, `git push origin Test *`,
  `*:Test` refspecs, `git checkout/switch Test`) instead of `Test*`, and adds denies for pushes to `main` or `Test` through
  refspecs, `--delete`, `--mirror` and `+` force refspecs. `git push origin testing` is allowed again: push the unpushed P1
  and P2 commits at the next phase end as AGENTS.md requires, and include `opencode.json` in your next commit.
  (b) `assistant/brain/llm.py`: an offline local-model session on 15 Sep 08:27 left a syntax error (the `chat` signature lost
  its colon and a broken `async def stream(...)::` header was inserted). Only those lines were repaired; the P2-T6 deletions
  of `LocalLLM` and `import requests` were kept. `py_compile` passes and `tests/unit` passes (116 tests).
- Reason: OpenCode's matcher (checked in the 1.18.30 binary) is case-insensitive and treats a trailing ` *` as optional, and
  the last matching rule wins, so `Test*` blocked `testing`. The offline edit was never reviewed because a failed cloud
  session was wrongly counted as a completed review; `opencode-autopilot` now counts only a clean exit.
- Alternatives rejected: reverting all of `llm.py` (would lose correct P2-T6 work); leaving the syntax error for the next
  session (every test run would fail until then).

## D-016 — A stalled cloud model is replaced, not only a retired one
- Date: 2026-09-15
- Task: planning (setup repair by the owner's checker)
- Decision: `opencode-doctor` now probes all preferred models in parallel and switches when the current model is retired or
  does not answer within 150 s, choosing the most preferred model that answers; it switches back when a more preferred model
  answers within 45 s. `opencode-autopilot` asks the doctor for a new model after 3 failed cloud sessions in a row. On
  15 Sep 13:06 it moved the global model from `deepseek-v4-flash-0731` to `nvidia/nvidia/nemotron-3-ultra-550b-a55b`.
- Reason: Between 14 Sep 13:33 and 15 Sep 12:50, 66 of 77 sessions ended with OpenCode exit code 1 on
  `ProviderHeaderTimeoutError`, and no task was committed. Probes on 15 Sep: `deepseek-v4-flash-0731` and `kimi-k3` gave no
  answer in 150–300 s; `deepseek-v4-pro-0813`, `llama-3.3-nemotron-super-49b-v1.5` and `mistral-large-3-675b-instruct-2512`
  return HTTP 410 (removed from the preference list); `nemotron-3-ultra` answered in 91–142 s and `opencode/big-pickle` in 4–11 s.
- Alternatives rejected: keeping a model that is reachable but never answers (no progress); switching to the local model
  (weaker code, D-010).

## D-017 — Tests removed with the legacy brain in P2-T6
- Date: 2026-09-15
- Task: P2-T6
- Decision: Removed `test_legacy_generate_extracts_the_user_line` (`tests/unit/test_fake_llm.py`), and `_class_methods` plus
  `test_voice_main_only_calls_methods_that_exist_on_speech_to_text` (`tests/unit/test_legacy_fixes.py`); replaced
  `test_smart_search_module_imports` with `test_web_search_tool_module_imports`. `requests` stays in `requirements.txt`.
- Reason: The code these tests covered was deleted by this task as the plan requires (`FakeLLM.generate`, `voice_main.py`,
  `assistant/tools/smart_search.py`); they were not removed to make a run pass. `git grep -n "import requests"` still finds
  `install_ui_deps.py`, so the plan's condition for removing `requests` is not met.
- Alternatives rejected: keeping tests for deleted modules (they could only fail); removing `requests` (breaks
  `install_ui_deps.py`).

## D-018 — `backend.ps1 -Stop` stops the whole process tree
- Date: 2026-09-15
- Task: P2-T6 (fixes a P1-T1 script)
- Decision: `scripts/backend.ps1 -Stop` now runs `taskkill /PID <pid> /T /F` on the saved PID before `Stop-Process`.
- Reason: `.venv/Scripts/python.exe` is a launcher that starts `C:\Python312\python.exe` as a child. The saved PID is the
  launcher, so `Stop-Process -Id` alone left the real uvicorn server running on port 8000 (orphans seen on 15 Sep at 13:23 and
  22:44, each a launcher + child pair). Evidence for the fix is in `docs/proof/P2-T6.md` (Step 8).
- Alternatives rejected: saving the child PID (the launcher is what `Start-Process` returns, and its child appears only later);
  stopping processes by name (forbidden by AGENTS.md).

## D-019 — Ignore only the root `models/` folder
- Date: 2026-09-16
- Task: P3-T1
- Decision: `.gitignore` line `models/` became `/models/`.
- Reason: An unanchored `models/` also matches `tests/models/`, so `git check-ignore -v tests/models/conftest.py` reported
  `.gitignore:90:models/` and the plan's `git add tests/models` would have silently skipped the model-backed tests. The
  forbidden path in AGENTS.md and `verify_all.ps1` is `^models/` (the root download folder), which stays ignored.
- Alternatives rejected: `git add -f tests/models` (every later task adding a model test would hit the same trap); renaming
  the test folder (the plan and later tasks use `tests/models`).

## D-020 — `VoiceController` queues every spoken sentence through one scheduling channel
- Date: 2026-09-16
- Task: P3-T5
- Decision: In `VoiceController._respond`, `produce()` now puts its remaining sentences and the end marker with
  `loop.call_soon_threadsafe(sentences.put_nowait, ...)`, the same channel `on_delta` uses, instead of `put_nowait` directly.
- Reason: With the plan's code, `test_wake_word_then_command_is_answered_and_spoken` and
  `test_barge_in_stops_playback_and_the_interruption_is_handled` failed 5 of 5 runs: the first streamed sentence was never
  spoken. `on_delta` schedules released sentences for a later loop turn, but `produce()` put the flushed remainder and `None`
  immediately, so the queue became `['Done.', None, 'Sure.']` and playback stopped at `None`. A standalone reproduction printed
  exactly that order, and `['Sure.', 'Done.', None]` when all puts share `call_soon_threadsafe`. The tests were not changed.
- Alternatives rejected: calling `put_nowait` in `on_delta` when already on the loop thread (two code paths; the real LLM
  stream may call `on_delta` from a worker thread); changing the test timings (forbidden by the plan).
