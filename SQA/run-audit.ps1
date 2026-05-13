<#
.SYNOPSIS
    Run the SQA audit: health checks + pytest + Playwright, no external agent required.

.PARAMETER Module
    SQA module folder under SQA/modules/ or a specific pytest file path under SQA/modules.
    Default: SQA-DT

.PARAMETER Headed
    Launch Playwright browser in headed mode (visible window). Default: headless.

.PARAMETER ServerUrl
    MES server base URL. Default: http://localhost:8081

.PARAMETER DtUrl
    DT-CLIENT base URL. Default: http://localhost:5177

.EXAMPLE
    .\run-audit.ps1
    .\run-audit.ps1 -Module SQA-DT -Headed
    .\run-audit.ps1 -Module SQA\modules\SQA-DT\test_work_schedule_team_crud.py
    .\run-audit.ps1 -ServerUrl http://localhost:8082 -DtUrl http://localhost:5173
#>
param(
    [string]$Module    = "SQA-DT",
    [switch]$Headed,
    [string]$ServerUrl = "http://localhost:8081",
    [string]$DtUrl     = "http://localhost:5177"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot  = Split-Path $PSScriptRoot -Parent
$Python    = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$Heartbeat = Join-Path $PSScriptRoot "HEARTBEAT.md"

function Resolve-TestTarget {
    param([string]$ModuleArg)

    $candidatePaths = @(
        $ModuleArg,
        (Join-Path $RepoRoot $ModuleArg),
        (Join-Path $PSScriptRoot ("modules\" + $ModuleArg))
    )

    foreach ($candidate in $candidatePaths) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    return (Join-Path $PSScriptRoot ("modules\" + $ModuleArg))
}

$TestTarget = Resolve-TestTarget -ModuleArg $Module

Write-Host ""
Write-Host "MES AI - SQA Audit" -ForegroundColor Cyan
Write-Host "  Module    : $Module"
Write-Host "  Target    : $TestTarget"
Write-Host "  Server    : $ServerUrl"
Write-Host "  DT-CLIENT : $DtUrl"
Write-Host "  Headed    : $($Headed.IsPresent)"
Write-Host ""

# --- 1. Health checks --------------------------------------------------------
Write-Host "[1/3] Health checks..." -ForegroundColor Yellow

function Test-Url {
    param([string]$Url, [string]$Label)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
            Write-Host "  [OK]   $Label ($Url) -> $($r.StatusCode)" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "  [FAIL] $Label ($Url) -> $($r.StatusCode)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  [FAIL] $Label ($Url) -> $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

$serverOk = Test-Url -Url "$ServerUrl/health" -Label "MES server"
$dtOk     = Test-Url -Url $DtUrl              -Label "DT-CLIENT"

if (-not $serverOk -or -not $dtOk) {
    Write-Host ""
    Write-Host "ERROR: One or more services are not reachable. Start the stack before running the audit." -ForegroundColor Red
    exit 1
}

# --- 2. Run pytest + Playwright ----------------------------------------------
Write-Host ""
Write-Host "[2/3] Running pytest ($Module)..." -ForegroundColor Yellow

$env:SQA_SERVER_URL = $ServerUrl
$env:SQA_DT_URL     = $DtUrl
$env:SQA_HEADED     = if ($Headed) { "1" } else { "0" }

Push-Location $RepoRoot
try {
    & $Python -m pytest $TestTarget -v --tb=short
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

# --- 3. Update HEARTBEAT.md --------------------------------------------------
Write-Host ""
Write-Host "[3/3] Updating HEARTBEAT.md..." -ForegroundColor Yellow

if ($ExitCode -eq 0) {
    $icon   = "PASS"
    $colour = "Green"
    $detail = "all tests passed"
}
else {
    $icon   = "FAIL"
    $colour = "Red"
    $detail = "FAILURES - see SQA/reports/latest/report.html"
}

$entry = @"

## $Timestamp - $Module [$icon]
- Server : $ServerUrl  DT-CLIENT : $DtUrl
- pytest : $detail
- Report : SQA/reports/latest/report.html
"@

Add-Content -Path $Heartbeat -Value $entry
Write-Host "  HEARTBEAT.md updated." -ForegroundColor $colour

Write-Host ""
Write-Host "Audit complete - [$icon]" -ForegroundColor $colour
exit $ExitCode
