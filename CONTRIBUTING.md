# Contributing to JARVIS Assistant

This project follows a strict TDD and proof workflow. Every change must be accompanied by tests that fail before the fix and pass after, and a proof file documenting the exact commands and outputs.

## Workflow

1. **Find the task** — Read `docs/PROGRESS.md` and `docs/plan/phase-*.md` for the current task.
2. **Write failing tests first** — Unit tests for the new interfaces.
3. **Implement** — Make the tests pass without weakening them.
4. **Run the gate** — `scripts/verify_all.ps1 -Quick` must exit 0.
5. **Write the proof** — Create `docs/proof/<TASK-ID>.md` with exact commands, exit codes, and pasted output (last 40+ lines).
6. **Commit** — One commit per task, message format:
   ```
   <type>(<scope>): <summary> [<TASK-ID>]

   Proof: docs/proof/<TASK-ID>.md
   ```
   Types: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`.
7. **Push** — `git push origin testing` after each phase (or every 3 DONE tasks).

## Code Standards

- **Python**: type hints everywhere, small single-purpose modules, `logging` not `print`, no hardcoded secrets/paths/model names/URLs — read from `assistant.config.Settings`.
- **TypeScript**: keep existing R3F holographic visuals; do not modify `components/jarvis/layers/*`, `components/jarvis/shaders/*`, or `components/jarvis/JarvisCoreEngine.tsx` unless a task says so.
- **Tests**: never need real hardware; audio tests use generated fixtures (Kokoro → WAV); LLM unit tests use `httpx.MockTransport` or `FakeLLM`.

## Gate Commands

```powershell
# Quick (pre-commit)
scripts/verify_all.ps1 -Quick

# Full (pre-push)
scripts/verify_all.ps1
```

The gate runs:
- Forbidden path scan (no `.env`, `key.txt`, `.venv/`, `node_modules/`, `.next/`, `models/`, `data/`, `*.db`, `*.onnx`, `*.bin`, `*.wav`, `*.mp3`, `PROJECT_CONTEXT.md`, `PROJECT_RAW_DUMP.md`)
- Secret scan (staged + untracked)
- Python unit tests (`pytest -m "not live and not models and not e2e"`)
- TypeScript (`npx tsc --noEmit`)
- Vitest (`npx vitest run`)

## Branching

- Work **only** on `testing`.
- Never commit to, push to, check out, merge into, or delete `main` or `Test`.
- Never force-push, rebase, `reset --hard`, `clean`, `filter-branch`, amend pushed commits, or rewrite history.

## Questions?

The owner reviews `testing` with Claude Code. Do not open pull requests.