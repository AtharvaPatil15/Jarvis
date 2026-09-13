<#
OpenCode autopilot - runs OpenCode in any project, session after session, until every task in the progress file is DONE
or BLOCKED, with automatic fallback to a local model.

  * Before starting (and after repeated provider errors) runs opencode-doctor, which repairs retired models.
  * Uses the project's pinned model, otherwise the global model, while the provider is reachable.
  * Switches to the local Ollama model when the internet/provider is down, or after MaxConsecutiveErrors provider errors in a
    session (for LocalCooldownMinutes), then goes back to the cloud model.
  * Restarts sessions that make no progress for StallMinutes. Every new session resumes from the progress file.
  * Without a progress file it runs a single session with -Prompt.

Usage (in a project folder):
  opencode-autopilot                                  loop until docs/PROGRESS.md is finished
  opencode-autopilot -Prompt "Fix the failing tests"  single session with fallback protection
  Options: -ProgressFile <file> -DryRun -ForceLocal -Once -MaxConsecutiveErrors 8 -StallMinutes 25 -SkipDoctor
           -OfflineMode review   (default) the local model drafts code offline without committing; the next cloud
                                 session must review and fix everything written offline before continuing
           -OfflineMode pause    no coding while offline; wait for the cloud model
Progress file format: a Markdown table whose first column is the task id and third column the status
(TODO, IN_PROGRESS, DONE, BLOCKED).
#>
param(
    [string]$ProjectDir = (Get-Location).Path,
    [string]$ProgressFile = 'docs/PROGRESS.md',
    [string]$TaskIdPattern = '',
    [string]$CloudModel = '',
    [string]$LocalModel = 'ollama/qwen3-8b-32k',
    [string]$Prompt = '',
    [int]$MaxSessions = 300,
    [int]$MaxConsecutiveErrors = 8,
    [int]$StallMinutes = 25,
    [int]$LocalCooldownMinutes = 20,
    [ValidateSet('review', 'pause')]
    [string]$OfflineMode = 'review',
    [switch]$ForceLocal,
    [switch]$DryRun,
    [switch]$Once,
    [switch]$SkipDoctor
)

$ErrorActionPreference = 'Continue'
$ProjectDir = (Resolve-Path $ProjectDir).Path
Set-Location $ProjectDir
$logDir = Join-Path $ProjectDir '.opencode-autopilot'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$gitignore = Join-Path $logDir '.gitignore'
if (-not (Test-Path $gitignore)) { Set-Content -Path $gitignore -Value '*' -Encoding ascii }
$opencodeLog = Join-Path $env:USERPROFILE '.local/share/opencode/log/opencode.log'
$ollamaExe = Join-Path $env:LOCALAPPDATA 'Programs/Ollama/ollama.exe'
$doctor = Join-Path $env:USERPROFILE '.opencode-kit/opencode-doctor.ps1'

function Get-OpenCodeExe {
    # Prefer the real executable: going through opencode.cmd adds cmd.exe, which fails in folders with very long paths.
    $shim = Get-Command 'opencode.cmd' -ErrorAction SilentlyContinue
    if ($shim) {
        $exe = Join-Path (Split-Path $shim.Source) 'node_modules\opencode-ai\bin\opencode.exe'
        if (Test-Path $exe) { return $exe }
        return $shim.Source
    }
    $direct = Get-Command 'opencode.exe' -ErrorAction SilentlyContinue
    if ($direct) { return $direct.Source }
    return $null
}
$openCodeExe = Get-OpenCodeExe
if (-not $openCodeExe) { Write-Host 'opencode is not installed or not on PATH'; exit 2 }
$hasProgress = Test-Path (Join-Path $ProjectDir $ProgressFile)
if (-not $hasProgress -and -not $Prompt) {
    Write-Host "no progress file ($ProgressFile) and no -Prompt given; nothing to do"
    exit 2
}
if (-not $hasProgress) { $Once = $true }

$resume = "Continue working autonomously. Re-read AGENTS.md if it exists, the plan documents it references, and $ProgressFile; then run git status and git log --oneline -5. If a task is IN_PROGRESS, restart it from its first step and re-run its tests from scratch; otherwise start the first task that is not DONE. Follow AGENTS.md exactly. Never ask questions. Keep going until every task is DONE or BLOCKED."
$basePrompt = if ($Prompt) { $Prompt } else { $resume }
$offlineNote = ' IMPORTANT: the internet or the cloud model is unavailable, so you are a smaller local model running offline and your work is a DRAFT that a cloud model will review. Only do work that needs no network: writing code and running offline tests. Do not run installs, downloads, git push or tests that need the internet. Do not commit and never mark a task DONE: leave every task you touch IN_PROGRESS with the note OFFLINE-DRAFT (add PENDING-NETWORK and the exact remaining steps if it needs the network). Never edit tests, hardcode expected values, or use shortcuts such as eval or exec. Re-run the tests after every change.'
$offlineBaseFile = Join-Path $logDir 'offline-base.txt'
$reviewNote = 'IMPORTANT FIRST STEP: earlier sessions ran on a weak offline model and may have written wrong or unsafe code. Before continuing, review every change since commit {0} (run git diff {0} and git status, and read uncommitted files too). Check it against the plan and AGENTS.md: tests must be unchanged, no hardcoded answers, no eval/exec or other unsafe shortcuts, and the behaviour must match the specification. Fix or rewrite anything wrong, re-run all tests, record what you changed, and only then continue. '

function Write-Status([string]$Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Write-Host $line
    Add-Content -Path (Join-Path $logDir 'autopilot.log') -Value $line
}

function Get-JsonValue([string]$Path, [string]$Key) {
    if (-not (Test-Path $Path)) { return $null }
    if ([System.IO.File]::ReadAllText($Path) -match "(?m)^\s*`"$Key`"\s*:\s*`"([^`"]+)`"") { return $Matches[1] }
    return $null
}

function Get-CloudModel {
    if ($CloudModel) { return $CloudModel }
    $pinned = Get-JsonValue (Join-Path $ProjectDir 'opencode.json') 'model'
    if ($pinned) { return $pinned }
    return Get-JsonValue (Join-Path $env:USERPROFILE '.config/opencode/opencode.json') 'model'
}

function Get-HealthUrl([string]$Model) {
    switch -Regex ($Model) {
        '^nvidia/' { return 'https://integrate.api.nvidia.com/v1/models' }
        '^opencode/' { return 'https://opencode.ai' }
        '^anthropic/' { return 'https://api.anthropic.com' }
        '^openai/' { return 'https://api.openai.com' }
        '^openrouter/' { return 'https://openrouter.ai/api/v1/models' }
        default { return 'https://www.msftconnecttest.com/connecttest.txt' }
    }
}

function Test-PlanFinished {
    if (-not $hasProgress) { return $false }
    $id = if ($TaskIdPattern) { $TaskIdPattern } else { '[^|]+?' }
    $statuses = foreach ($line in Get-Content (Join-Path $ProjectDir $ProgressFile)) {
        if ($line -match "^\|\s*($id)\s*\|[^|]*\|\s*(TODO|IN_PROGRESS|DONE|BLOCKED)\b") { $Matches[2] }
    }
    if (-not $statuses) { return $false }
    return -not ($statuses | Where-Object { $_ -notin @('DONE', 'BLOCKED') })
}

function Test-CloudReachable([string]$Model) {
    if ($ForceLocal -or -not $Model -or $Model -like 'ollama/*') { return $false }
    try {
        Invoke-WebRequest -Uri (Get-HealthUrl $Model) -Method Get -TimeoutSec 15 -UseBasicParsing | Out-Null
        return $true
    } catch {
        return [bool]$_.Exception.Response
    }
}

function Test-AbandonCloud([string]$Model, [int]$Errors, [ref]$CheckedAt) {
    # The free NVIDIA endpoint often stalls for several 2-minute header timeouts in a row and then recovers (worst streak
    # seen: 4 errors over 7 minutes), so give up early only when the network or API is actually unreachable.
    if ($Errors -ge $MaxConsecutiveErrors) { return $true }
    if ($Model -like 'ollama/*' -or $Errors -lt 2 -or $Errors -eq $CheckedAt.Value) { return $false }
    $CheckedAt.Value = $Errors
    return -not (Test-CloudReachable $Model)
}

function Test-LocalReady {
    $name = $LocalModel -replace '^ollama/', ''
    try {
        $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
    } catch {
        if (Test-Path $ollamaExe) { Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden }
        Start-Sleep -Seconds 8
        try { $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5 } catch { return $false }
    }
    return [bool]($tags.models | Where-Object { $_.name -eq $name -or $_.name -eq "${name}:latest" })
}

function Invoke-Doctor([switch]$Live) {
    if ($SkipDoctor -or $DryRun -or -not (Test-Path $doctor)) { return }
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $doctor, '-Quiet', '-ProjectDir', $ProjectDir)
    if ($Live) { $arguments += '-Force' }
    & powershell @arguments
    Write-Status "doctor exit code: $LASTEXITCODE"
}

function Read-NewLogText([ref]$Offset) {
    if (-not (Test-Path $opencodeLog)) { return '' }
    $length = (Get-Item $opencodeLog).Length
    if ($length -lt $Offset.Value) { $Offset.Value = 0 }
    if ($length -eq $Offset.Value) { return '' }
    $stream = [System.IO.File]::Open($opencodeLog, 'Open', 'Read', 'ReadWrite')
    try {
        $null = $stream.Seek($Offset.Value, 'Begin')
        $text = (New-Object System.IO.StreamReader($stream)).ReadToEnd()
    } finally {
        $stream.Dispose()
    }
    $Offset.Value = $length
    return $text
}

function Invoke-Session([string]$Model, [string]$SessionPrompt, [int]$Index) {
    $out = Join-Path $logDir ('session-{0:D3}.log' -f $Index)
    Write-Status "session ${Index}: starting on $Model (output: $out)"
    if ($DryRun) { return 'dry-run' }
    $offset = if (Test-Path $opencodeLog) { (Get-Item $opencodeLog).Length } else { 0 }
    $quotedPrompt = '"' + ($SessionPrompt -replace '"', "'") + '"'
    $proc = Start-Process -FilePath $openCodeExe -ArgumentList @('run', '--auto', '--model', $Model, $quotedPrompt) `
        -WorkingDirectory $ProjectDir -PassThru -NoNewWindow -RedirectStandardOutput $out -RedirectStandardError "$out.err"
    $null = $proc.Handle
    $errors = 0
    $checkedAt = 0
    $sessionStart = Get-Date
    $lastProgress = $sessionStart
    # OpenCode writes every instance to one shared log; only count lines from this session's run id.
    $leaf = [regex]::Escape((Split-Path $ProjectDir -Leaf))
    $runId = $null
    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 15
        foreach ($line in ((Read-NewLogText ([ref]$offset)) -split "`n")) {
            if (-not $runId -and $line -match "run=(\w+) message=`"creating instance`" directory=`"[^`"]*$leaf`"") {
                $runId = $Matches[1]
            }
            $mine = ($runId -eq 'any') -or ($runId -and $line -match "run=$runId\b")
            if (-not $mine) { continue }
            if ($line -match 'message="stream error"') { $errors++ }
            elseif ($line -match 'message=(loop|evaluated)\b') { $errors = 0; $checkedAt = 0; $lastProgress = Get-Date }
        }
        if (-not $runId -and ((Get-Date) - $sessionStart).TotalMinutes -ge 2) {
            $runId = 'any'
            Write-Status "session ${Index}: could not identify its OpenCode log lines, watching all of them"
        }
        if (Test-AbandonCloud $Model $errors ([ref]$checkedAt)) {
            Write-Status "session ${Index}: $errors consecutive model errors and the provider is unreachable or the limit of $MaxConsecutiveErrors is reached, stopping this session"
            taskkill /PID $proc.Id /T /F 2>$null | Out-Null
            return 'provider-errors'
        }
        if (((Get-Date) - $lastProgress).TotalMinutes -ge $StallMinutes) {
            Write-Status "session ${Index}: no progress for $StallMinutes minutes, stopping this session"
            taskkill /PID $proc.Id /T /F 2>$null | Out-Null
            return 'stalled'
        }
    }
    Write-Status "session ${Index}: OpenCode exited with code $($proc.ExitCode)"
    return 'exited'
}

Invoke-Doctor
$preferLocalUntil = Get-Date
for ($session = 1; $session -le $MaxSessions; $session++) {
    if (Test-PlanFinished) { Write-Status 'every task is DONE or BLOCKED, autopilot finished'; exit 0 }
    $cloud = Get-CloudModel
    $cloudOk = Test-CloudReachable $cloud
    $localOk = Test-LocalReady
    Write-Status "health: cloud model=$cloud reachable=$cloudOk, local model ready=$localOk"
    $useCloud = $cloudOk -and (((Get-Date) -ge $preferLocalUntil) -or -not $localOk)
    if ($useCloud) {
        $cloudPrompt = $basePrompt
        $reviewing = Test-Path $offlineBaseFile
        if ($reviewing) {
            $base = (Get-Content $offlineBaseFile -Raw).Trim()
            if (-not $base) { $base = 'HEAD' }
            $cloudPrompt = ($reviewNote -f $base) + $basePrompt
            Write-Status "session ${session}: cloud model will first review offline drafts since $base"
        }
        $result = Invoke-Session $cloud $cloudPrompt $session
        if ($result -eq 'exited' -and $reviewing) {
            Remove-Item $offlineBaseFile -Force
            Write-Status 'offline drafts reviewed by the cloud model'
        }
        if ($result -eq 'provider-errors') {
            $preferLocalUntil = (Get-Date).AddMinutes($LocalCooldownMinutes)
            Write-Status "cloud model unhealthy, preferring the local model for $LocalCooldownMinutes minutes"
            Invoke-Doctor -Live
        }
    } elseif ($localOk -and $OfflineMode -eq 'review') {
        if (-not (Test-Path $offlineBaseFile) -and -not $DryRun) {
            $head = git -C $ProjectDir rev-parse HEAD 2>$null
            Set-Content -Path $offlineBaseFile -Value ([string]$head) -Encoding ascii
        }
        $result = Invoke-Session $LocalModel ($basePrompt + $offlineNote) $session
    } else {
        $why = if ($localOk) { 'offline mode is pause' } else { 'the local model is not available' }
        Write-Status "cloud model unavailable and $why, retrying in 60 seconds"
        if ($DryRun -or $Once) { exit 2 }
        Start-Sleep -Seconds 60
        continue
    }
    if ($DryRun -or $Once) { exit 0 }
    Start-Sleep -Seconds 10
}
Write-Status "stopped after $MaxSessions sessions"
exit 1
