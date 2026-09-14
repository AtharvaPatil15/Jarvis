param([switch]$Start, [switch]$Stop, [switch]$Fake, [switch]$NoVoice, [int]$Port = 8000, [int]$TimeoutSec = 120)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force -Path 'docs/proof/tmp' | Out-Null
$pidFile = 'docs/proof/tmp/backend.pid'

if ($Stop) {
    if (Test-Path $pidFile) {
        $procId = [int](Get-Content $pidFile)
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Remove-Item $pidFile
        Write-Output "backend stopped (pid $procId)"
    } else {
        Write-Output 'backend not running'
    }
    exit 0
}

if ($Start) {
    if ($Fake) { $env:JARVIS_LLM_BACKEND = 'fake' } else { Remove-Item Env:JARVIS_LLM_BACKEND -ErrorAction SilentlyContinue }
    if ($NoVoice) { $env:JARVIS_VOICE_ENABLED = 'false' } else { Remove-Item Env:JARVIS_VOICE_ENABLED -ErrorAction SilentlyContinue }
    $proc = Start-Process -FilePath '.venv/Scripts/python.exe' `
        -ArgumentList @('-m', 'uvicorn', 'server:create_app', '--factory', '--host', '127.0.0.1', '--port', "$Port") `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput 'docs/proof/tmp/backend.out.log' -RedirectStandardError 'docs/proof/tmp/backend.err.log'
    Set-Content -Path $pidFile -Value $proc.Id
    for ($i = 0; $i -lt ($TimeoutSec * 2); $i++) {
        if ($proc.HasExited) {
            Write-Output 'backend exited early'
            Get-Content 'docs/proof/tmp/backend.err.log' -Tail 40
            exit 1
        }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
            Write-Output ($health | ConvertTo-Json -Compress)
            exit 0
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    Write-Output "backend not healthy within $TimeoutSec s"
    Get-Content 'docs/proof/tmp/backend.err.log' -Tail 40
    exit 1
}

Write-Output 'usage: backend.ps1 -Start [-Fake] [-NoVoice] [-Port 8000] [-TimeoutSec 120] | -Stop'
exit 2