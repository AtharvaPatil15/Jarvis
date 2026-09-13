# Proof files

Every task writes `docs/proof/<TASK-ID>.md`. Claude Code verifies a task by re-running the commands listed here and comparing
the results. Output must be pasted verbatim — never retyped, summarised, or edited to remove failures.

Screenshots go in `docs/proof/img/<TASK-ID>-<name>.png`. Scratch logs go in `docs/proof/tmp/` (git-ignored).

## Template

````markdown
# Proof — <TASK-ID>: <task title>

- Date: YYYY-MM-DD HH:MM (local)
- Branch: testing
- Base commit before this task: <output of `git rev-parse --short HEAD` before starting>

## What changed
- <file>: <one line>

## Tests written
- `<test file>::<test name>` — <behaviour it proves>

## Red: tests failing before the implementation
Command:
```
<exact command>
```
Exit code: <n>
```
<last 40+ lines of real output>
```

## Green: tests passing after the implementation
Command:
```
<exact command>
```
Exit code: 0
```
<last 40+ lines of real output>
```

## Task-specific verification
<one block per command from the task's "Verify" step: command, exit code, real output>

## Gate
Command: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick`
```
<the full === SUMMARY === block and the final line>
```

## Acceptance criteria
- [x] <criterion copied from the phase file> — evidence: <which block above>

## Deviations from the plan
<"None" or a pointer to the docs/DECISIONS.md entry>

## How to re-verify
```
<the minimal command list a reviewer runs to reproduce the green result>
```
````

Evidence that can only exist after a commit (push output, `git ls-remote`) is appended to the same proof file under
`## Post-commit verification` and committed together with the next task.
