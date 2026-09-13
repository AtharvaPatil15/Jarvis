# Starting and resuming OpenCode on this project

## Recommended: autopilot with offline fallback

Open a terminal (for example VS Code's) in `C:\Users\athar\Documents\Jarvis-Assistant` and run:

```powershell
opencode-autopilot
```

It works the same in any project that has a `docs/PROGRESS.md` task table (or use `opencode-autopilot -Prompt "..."` for a
one-off job). It first runs `opencode-doctor`, then runs OpenCode session after session until every task is DONE or BLOCKED.
It uses your global cloud model when reachable and switches to the local `qwen3-8b-32k` model through Ollama when the
internet or the API is down or keeps failing. Each session's output is saved in `.opencode-autopilot/`. Press `Ctrl+C` to
stop; running it again resumes from `docs/PROGRESS.md`.

The local model writes noticeably weaker code (in testing it used forbidden `eval()` where the cloud model wrote a safe
parser), so offline work is treated as a draft: it is never committed or marked DONE, and the next cloud session must
review and fix everything written offline before it continues. To stop coding completely while offline instead, run
`opencode-autopilot -OfflineMode pause`.

`opencode-doctor` also runs daily from Task Scheduler ("OpenCode Doctor"). Run it yourself any time with
`opencode-doctor -Force`; its log is `%USERPROFILE%\.opencode-kit\doctor.log`.

The manual way below still works if you prefer to watch OpenCode's own interface.

## Start

1. Open a terminal in `C:\Users\athar\Documents\Jarvis-Assistant` and run `opencode`.
   (`opencode.json` in this folder already allows it to edit, run commands and browse without asking, and blocks
   destructive git commands.)
2. Paste the **first prompt** below and leave it running.

Nothing else is needed: OpenCode starts Ollama, pulls the models, creates the Python environment, downloads the speech
models, and pushes verified work to the `testing` branch.

## First prompt

```text
You are the sole developer of this repository, working fully autonomously on Windows. The owner will not answer questions and will not do anything manually - not even start Ollama.

Before doing anything else, read these files completely, in this order:
1. AGENTS.md - your binding rules for autonomy, testing, proof and git.
2. docs/PLAN.md - architecture, interfaces, global constraints and the task index.
3. docs/PROGRESS.md - task status. Start at the first task that is not DONE.
4. The phase file in docs/plan/ that contains that task.

Then execute the tasks in order, one at a time, until every task in docs/PROGRESS.md is DONE or BLOCKED. For every task:
- follow its steps exactly: write the tests first, run them and confirm they fail, implement, run them and confirm they pass;
- run the task's own verification commands, then the gate: scripts/verify_all.ps1 -Quick before every commit, the full scripts/verify_all.ps1 before every push;
- write docs/proof/<TASK-ID>.md containing the exact commands and their real output, update docs/PROGRESS.md, and commit on branch testing using the commit format in AGENTS.md;
- push to origin testing at the end of each phase.

Hard rules: never ask me anything; never use API keys, accounts, logins or paid services; never commit to, push to or check out main or Test; never force-push, rebase or rewrite history; never skip, delete or weaken a test to get a green run; never claim a result you did not observe. When the plan does not match reality, adapt minimally, keep the task's interfaces and acceptance criteria, and record the change in docs/DECISIONS.md. If a task is still failing after three materially different attempts, mark it BLOCKED in docs/PROGRESS.md with the evidence and continue with the next task whose dependencies are met.

Do not stop between tasks to summarise or wait for confirmation - keep working until the whole plan is finished. Begin now by reading AGENTS.md.
```

## Resume prompt

Use this if OpenCode stops for any reason (context limit, crash, closed terminal, or it ends its turn early):

```text
Continue the JARVIS build autonomously. Re-read AGENTS.md, docs/PLAN.md and docs/PROGRESS.md, then run git status, git branch --show-current and git log --oneline -5. If a task is IN_PROGRESS, restart it from its first step and re-run its tests from scratch; otherwise start the first task that is not DONE. Same rules as before: tests first, proof files with real output, gate before every commit, commits only on branch testing, push after each phase, no questions, no API keys. Keep going until every task is DONE or BLOCKED.
```

## Checking progress

- `docs/PROGRESS.md` shows each task's status and proof link.
- `docs/DECISIONS.md` lists every deviation from the plan and why.
- `git log --oneline origin/testing` shows one commit per finished task, each tagged `[P#-T#]`.

## Reviewing with Claude Code

Ask Claude Code to review the `testing` branch. The review checks each task by:
1. Reading `docs/proof/<TASK-ID>.md` and re-running its "How to re-verify" commands.
2. Running `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1` on a clean checkout.
3. Comparing the code with the interfaces in `docs/PLAN.md` §3 and each task's acceptance criteria.
