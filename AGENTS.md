# JARVIS Assistant — Rules for the Developer Agent (OpenCode)

You are the **only developer** on this project. The owner is not available and will not answer questions.
**Claude Code reviews your work afterwards** by re-running the commands in your proof files. Anything you
claim but cannot be reproduced is rejected.

## 1. Start of every session (do this first, every time)

1. Read this file completely.
2. Read `docs/PROGRESS.md` and find the first task whose status is not `DONE`
   (skip `BLOCKED` tasks unless the blocker is now resolved).
3. Read `docs/PLAN.md` (architecture, interfaces, global constraints) and the phase file for that task
   in `docs/plan/`.
4. Run `git status` and `git branch --show-current`. After task P0-T1 the branch must be `testing`.
5. Execute tasks **in order, continuously, until every task is `DONE` or `BLOCKED`**. Do not stop after a
   task to report or wait for confirmation. Report progress only by updating `docs/PROGRESS.md`.

## 2. Autonomy

- Never ask the user anything. The `question` tool is disabled on purpose.
- The owner does nothing manually. You start Ollama, pull models, create the venv, install packages,
  download model files, start and stop servers.
- **No API keys, accounts, logins, sign-ups, or paid services — ever.** The finished system must run fully
  local and keyless (Ollama, faster-whisper, Kokoro, openWakeWord, DuckDuckGo, Open-Meteo). Never create,
  request, or paste credentials. The only credential in use is the owner's existing `gh` login for `git push`.
- When something is ambiguous, pick the option most consistent with `docs/PLAN.md`, write it in
  `docs/DECISIONS.md` (date, task ID, decision, reason), and continue.
- When the plan is wrong for reality (package API changed, a model is unavailable), adapt minimally, keep the
  task's **interfaces and acceptance criteria unchanged**, and record the deviation in `docs/DECISIONS.md`.
- When stuck: make at most **3 materially different attempts**. Then set the task to `BLOCKED` in
  `docs/PROGRESS.md` with the exact error output and what you tried, and continue with the next task whose
  dependencies are satisfied.
- Downloads are allowed only from: PyPI, npm, the Ollama registry (`ollama pull`), Hugging Face (faster-whisper
  / openWakeWord model files fetched by those libraries), and GitHub release assets of `thewh1teagle/kokoro-onnx`.

## 3. Testing is mandatory

- Every task: write or extend tests **first**, run them and see them fail, implement, run them and see them pass.
- Never delete, skip, `xfail`, or weaken a test to get to green. Fix the code. If a test itself is wrong, fix
  it and record why in `docs/DECISIONS.md`.
- Tests never need real hardware. No real microphone, no real speaker. Audio tests use generated fixtures
  (Kokoro speech written to WAV at test time). LLM unit tests use `httpx.MockTransport` or `FakeLLM`.
- Pytest markers (defined in `pytest.ini`):
  - no marker — pure unit tests, fast, offline.
  - `live` — needs the local Ollama server and pulled models.
  - `models` — needs downloaded model files (Whisper, Kokoro, openWakeWord) but no network after download.
  - `e2e` — starts real servers / browser.
- **Gates**
  - Before every commit: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick`
    **and** the task's own verification commands from its phase file (including its `live` / `models` tests).
  - Before every push: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1` (full).
  - A gate passes only when it exits `0`.
- A task is `DONE` only when all four are true: acceptance criteria met, its tests pass, the gate passes, the proof
  file is written and committed.

## 4. Proof (non-negotiable)

For every task create `docs/proof/<TASK-ID>.md` using the template in `docs/proof/README.md`:
exact commands run, exit codes, and **real pasted output** (at least the last 40 lines of each command).
UI tasks also save a screenshot under `docs/proof/img/<TASK-ID>-*.png`. Never fabricate, paraphrase, or trim
failures out of output. If a command's output differs when Claude Code re-runs it, the task is rejected.

## 5. Git rules (strict)

- Repository: `https://github.com/AtharvaPatil15/Jarvis`. Work **only** on branch `testing`.
- Never commit to, push to, check out, merge into, or delete `main` or `Test`.
- Never force-push, rebase, `reset --hard`, `clean`, `filter-branch`, amend pushed commits, or rewrite history.
  (These are also denied in `opencode.json`.)
- One commit per `DONE` task. Message format:
  ```
  <type>(<scope>): <summary> [<TASK-ID>]

  Proof: docs/proof/<TASK-ID>.md
  ```
  `type` ∈ feat, fix, refactor, test, chore, docs.
- Stage explicit paths with `git add <path> ...`. Do not use `git add -A` / `git add .` (task P0-T1 is the only
  exception and has its own checks).
- Before each commit run `git diff --cached --name-only` and confirm no forbidden path is staged (the gate also
  scans staged content for secrets).
- Push with `git push origin testing` after each phase completes, and at least after every 3 `DONE` tasks.
- **Forbidden in git:** `.env`, `key.txt`, `.venv/`, `node_modules/`, `.next/`, `models/`, `data/`, `*.db`,
  `*.onnx`, `*.bin`, `*.wav`, `*.mp3`, `PROJECT_CONTEXT.md`, `PROJECT_RAW_DUMP.md`.

## 6. Environment facts (verified 13 Sep 2026)

- Windows 11. Python 3.12.4 (`py -3.12`). Node 22.20, npm 11.7, git 2.55. `gh` logged in as `AtharvaPatil15`
  with `repo` scope.
- GPU: NVIDIA RTX 5060 Laptop, 8 GB VRAM (Blackwell). CUDA libraries can fail on Blackwell —
  **every GPU code path must fall back to CPU** automatically.
- Ollama 0.34 is installed: `C:\Users\athar\AppData\Local\Programs\Ollama\ollama.exe`, API on
  `http://127.0.0.1:11434`. Only llama3-family models are pulled at the start. **LM Studio is not used.**
- Use forward slashes in commands, e.g. `.venv/Scripts/python.exe -m pytest` (works in PowerShell and bash).
- **Your shell tool runs Windows PowerShell** (launched through `cmd.exe`; verified 13 Sep 2026). The PowerShell
  commands in the phase files run as written: pipes, `$env:` variables, `;` separators. Do not use `&&` or bash syntax.
  Because `cmd.exe` sits in front, never write a literal `%NAME%` in a command (cmd expands it); use `$env:NAME`.
- **Long commands:** anything that can exceed ~2 minutes (pip/npm installs, `ollama pull`, model downloads, model or
  e2e test runs, Playwright) must either be given the shell tool's maximum `timeout`, or be started with `Start-Process`
  in the background writing a log under `docs/proof/tmp/`, then polled. A timed-out command is not a failed test — rerun
  it properly before drawing conclusions.
- **Your model** is chosen outside this project, by the owner's global OpenCode config, which `opencode-doctor` keeps healthy
  (it replaces retired models automatically). When the internet or the cloud API is down, `opencode-autopilot` (same script
  as `scripts/opencode_autopilot.ps1`) restarts you on the local fallback `ollama/qwen3-8b-32k` with extra offline
  instructions in your prompt. Follow them: offline work only; the local model's work is a draft, so it never commits and
  never marks a task DONE (tasks stay `IN_PROGRESS` with `OFFLINE-DRAFT`); mark network-dependent leftovers
  `PENDING-NETWORK`. When your prompt starts with a review instruction, first review and fix everything written offline
  since the given commit (tests unchanged, no hardcoded answers, no `eval`/`exec`, behaviour matches the task), re-run all
  tests, and only then continue.
  Never switch models yourself and never add model or provider settings to `opencode.json`. If the API returns HTTP 429
  (rate limit), wait 60 seconds and continue.
- `.opencode-autopilot/` holds the autopilot's own logs and ignores itself in git; never edit or commit it.
- Never delete Ollama models (`ollama rm`) and never stop processes by name (`Stop-Process -Name`, `taskkill /IM`): the
  autopilot, Ollama and other tools may be running. Stop only the process IDs you started yourself.
- Long-running processes (uvicorn on :8000, Next.js on :3000, Ollama on :11434): start them in the background,
  poll until ready, and stop them when the test finishes. Never leave orphan servers running.
- Your file tools cannot read `.env` (OpenCode denies it). All defaults live in `assistant/config.py`; code must
  work with no `.env` file present.

## 7. Files you must not trust

- `PROJECT_CONTEXT.md`, `PROJECT_RAW_DUMP.md` — stale June source dumps. Never use them as the source of truth.
- Git ref `origin/Test` — an old monorepo experiment. Use it only where a task explicitly references it.
- `docs/plan/*` is the plan; the code on disk is the truth about current state.

## 8. Code standards

- Python: type hints everywhere, small single-purpose modules, `logging` (not `print`) in library code, no
  hardcoded secrets, paths, locations, model names, or URLs — read them from `assistant.config.Settings`.
- TypeScript: keep the existing R3F holographic visuals. Do not modify `components/jarvis/layers/*`,
  `components/jarvis/shaders/*`, or `components/jarvis/JarvisCoreEngine.tsx` unless a task says so.
- Keep `docs/PROGRESS.md` current after every task: status, date, commit summary, proof link, notes.
