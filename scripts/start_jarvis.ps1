param([switch]$Stop, [switch]$NoElectron, [switch]$Fake, [switch]$Rebuild, [int]$TimeoutSec = 300)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$state = 'data/launcher'
New-Item -ItemType Directory -Force -Path $state | Out-Null

function Stop-Jarvis {
    foreach ($name in 'electron', 'ui', 'backend') {
        $file = Join-Path $state "$name.pid"
        if (Test-Path $file) {
            $procId = [int](Get-Content $file)
            taskkill /PID $procId /T /F 2>$null | Out-Null
            Remove-Item $file
            Write-Output "stopped $name (pid $procId)"
        }
    }
}

function Wait-Http([string]$Url, [string]$What) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) { Write-Host "$What ready: $Url"; return $true }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    # Write-Host, not Write-Output: pipeline output would become part of the return value and make it truthy (D-026).
    Write-Host "$What not ready within $TimeoutSec s (see $state)"
    return $false
}

if ($Stop) { Stop-Jarvis; exit 0 }

if (-not (Test-Path '.venv/Scripts/python.exe')) { Write-Output 'Python environment missing (.venv). Run task P0-T2.'; exit 1 }
Stop-Jarvis

if ($Fake) {
    $env:JARVIS_LLM_BACKEND = 'fake'
    $env:JARVIS_VOICE_ENABLED = 'false'
} else {
    Remove-Item Env:JARVIS_LLM_BACKEND, Env:JARVIS_VOICE_ENABLED -ErrorAction SilentlyContinue
    & .venv/Scripts/python.exe scripts/ensure_ollama.py --no-pull
    if ($LASTEXITCODE -ne 0) { Write-Output 'Ollama is not ready.'; exit 1 }
}

$backend = Start-Process -FilePath '.venv/Scripts/python.exe' -WindowStyle Hidden -PassThru `
    -ArgumentList @('-m', 'uvicorn', 'server:create_app', '--factory', '--host', '127.0.0.1', '--port', '8000') `
    -RedirectStandardOutput "$state/backend.out.log" -RedirectStandardError "$state/backend.err.log"
Set-Content "$state/backend.pid" $backend.Id
if (-not (Wait-Http 'http://127.0.0.1:8000/health' 'backend')) { Stop-Jarvis; exit 1 }

if ($Rebuild -or -not (Test-Path '.next/BUILD_ID')) {
    npm run build
    if ($LASTEXITCODE -ne 0) { Write-Output 'UI build failed.'; Stop-Jarvis; exit 1 }
}
$ui = Start-Process -FilePath 'npx.cmd' -WindowStyle Hidden -PassThru `
    -ArgumentList @('next', 'start', '--hostname', '127.0.0.1', '--port', '3000') `
    -RedirectStandardOutput "$state/ui.out.log" -RedirectStandardError "$state/ui.err.log"
Set-Content "$state/ui.pid" $ui.Id
if (-not (Wait-Http 'http://127.0.0.1:3000' 'ui')) { Stop-Jarvis; exit 1 }

if ($NoElectron) {
    Write-Output 'JARVIS is running without a window. Stop it with: scripts/start_jarvis.ps1 -Stop'
    exit 0
}

$electron = Start-Process -FilePath 'npx.cmd' -ArgumentList @('electron', 'electron/main.js') -PassThru
Set-Content "$state/electron.pid" $electron.Id
$electron.WaitForExit()
Stop-Jarvis
exit 0