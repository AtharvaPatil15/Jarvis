param([switch]$Quick)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root '.venv/Scripts/python.exe'
New-Item -ItemType Directory -Force -Path 'docs/proof/tmp' | Out-Null
$log = "docs/proof/tmp/verify-$(Get-Date -Format yyyyMMdd-HHmmss).log"
$results = [ordered]@{}

$forbidden = '(^|/)\.env$|(^|/)key\.txt$|^\.venv/|(^|/)node_modules/|^\.next/|^models/|^data/|\.(db|onnx|bin|wav|mp3)$|^PROJECT_(CONTEXT|RAW_DUMP)\.md$'
$secretPattern = ('ycGaIQ' + 'bL2ZWI8r2M') + '|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}'

function Invoke-Gate {
    param([string]$Name, [scriptblock]$Command, [int[]]$OkCodes = @(0))
    Write-Output "=== $Name ==="
    Add-Content -Path $log -Value "=== $Name ==="
    $global:LASTEXITCODE = 0
    & $Command 2>&1 | ForEach-Object {
        $line = "$_"
        Write-Output $line
        Add-Content -Path $log -Value $line
    }
    $code = $global:LASTEXITCODE
    Add-Content -Path $log -Value "exit=$code"
    if ($OkCodes -contains $code) { $results[$Name] = 'ok' } else { $results[$Name] = "FAILED (exit $code)" }
}

Invoke-Gate 'FORBIDDEN PATHS' {
    $bad = @(git ls-files) + @(git diff --cached --name-only) | Sort-Object -Unique | Where-Object { $_ -match $forbidden }
    if ($bad) { $bad; $global:LASTEXITCODE = 1 } else { 'none'; $global:LASTEXITCODE = 0 }
}

# git grep exits 1 when nothing matches, which is the passing case. -l prints file names only, never secrets.
Invoke-Gate 'SECRET SCAN (index)' { git grep --cached -lIE $secretPattern } @(1)

Invoke-Gate 'SECRET SCAN (untracked)' {
    $hits = git ls-files --others --exclude-standard |
        Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
        ForEach-Object { Select-String -LiteralPath $_ -Pattern $secretPattern -List }
    if ($hits) { $hits | ForEach-Object { "$($_.Path):$($_.LineNumber)" }; $global:LASTEXITCODE = 1 }
    else { 'none'; $global:LASTEXITCODE = 0 }
}

# pytest exit 5 = no tests collected for that marker, which is fine early in the project.
Invoke-Gate 'PYTHON UNIT' { & $py -m pytest -m 'not live and not models and not e2e' -q } @(0, 5)
Invoke-Gate 'TYPESCRIPT' { npx tsc --noEmit }
if (Test-Path 'vitest.config.ts') { Invoke-Gate 'VITEST' { npx vitest run } }

if (-not $Quick) {
    if (Test-Path 'scripts/ensure_ollama.py') { Invoke-Gate 'OLLAMA READY' { & $py scripts/ensure_ollama.py --no-pull } }
    Invoke-Gate 'PYTHON LIVE' { & $py -m pytest -m live -q } @(0, 5)
    Invoke-Gate 'PYTHON MODELS' { & $py -m pytest -m models -q } @(0, 5)
    Invoke-Gate 'PYTHON E2E' { & $py -m pytest -m e2e -q } @(0, 5)
    Invoke-Gate 'NEXT BUILD' { npm run build }
    if (Test-Path 'playwright.config.ts') { Invoke-Gate 'PLAYWRIGHT' { npx playwright test } }
}

Write-Output '=== SUMMARY ==='
$failed = @()
foreach ($key in $results.Keys) {
    Write-Output ('{0,-26} {1}' -f $key, $results[$key])
    if ($results[$key] -ne 'ok') { $failed += $key }
}
Write-Output "log: $log"
if ($failed.Count -gt 0) { Write-Output "GATES FAILED: $($failed -join ', ')"; exit 1 }
Write-Output 'ALL GATES PASSED'
exit 0