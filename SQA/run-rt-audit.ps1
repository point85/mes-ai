<#
.SYNOPSIS
    Run the RT-CLIENT SQA audit: health checks + pytest + Playwright.

.PARAMETER Scope
    Portion of the RT suite to run.
    - inventory : Inventory RT tests only
    - wip       : WIP RT tests only
    - all       : All RT-CLIENT SQA tests

.PARAMETER Headed
    Launch Playwright browser in headed mode (visible window). Default: headless.

.PARAMETER ServerUrl
    MES server base URL. Default: http://localhost:8082

.PARAMETER RtUrl
    RT-CLIENT base URL. Default: http://localhost:5176

.EXAMPLE
    .\run-rt-audit.ps1 -Scope inventory

.EXAMPLE
    .\run-rt-audit.ps1 -Scope wip -RtUrl http://localhost:5176 -ServerUrl http://localhost:8082
#>
param(
    [ValidateSet("inventory", "wip", "all")]
    [string]$Scope,
    [switch]$Headed,
    [switch]$Help,
    [string]$ServerUrl = "http://localhost:8082",
    [string]$RtUrl     = "http://localhost:5176"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot  = Split-Path $PSScriptRoot -Parent
$Python    = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$PrepScript = Join-Path $RepoRoot "server\scripts\prepare_rt_inventory.py"
$Timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$Heartbeat = Join-Path $PSScriptRoot "HEARTBEAT.md"

function Show-Usage {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\run-rt-audit.ps1 -Scope <inventory|wip|all> [-Headed] [-ServerUrl <url>] [-RtUrl <url>]"
    Write-Host ""
    Write-Host "Scopes:" -ForegroundColor Yellow
    Write-Host "  inventory      Run Inventory RT tests only"
    Write-Host "  wip            Run WIP RT tests only"
    Write-Host "  all            Run the full RT SQA suite"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\run-rt-audit.ps1 -Scope inventory"
    Write-Host "  .\run-rt-audit.ps1 -Scope wip"
    Write-Host "  .\run-rt-audit.ps1 -Scope all -Headed"
    Write-Host "  .\run-rt-audit.ps1 -Scope wip -ServerUrl http://localhost:8082 -RtUrl http://localhost:5176"
}

if ($Help) {
    Show-Usage
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Scope)) {
    Show-Usage
    exit 2
}

function Resolve-TestTargets {
    param([string]$SelectedScope)

    switch ($SelectedScope) {
        "inventory" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-RT\test_inventory_operations.py")
            )
        }
        "wip" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-RT\test_wip_operations.py")
            )
        }
        default {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-RT")
            )
        }
    }
}

$TestTargets = Resolve-TestTargets -SelectedScope $Scope

Write-Host ""
Write-Host "MES AI - RT SQA Audit" -ForegroundColor Cyan
Write-Host "  Scope     : $Scope"
Write-Host "  Targets   :"
foreach ($target in $TestTargets) {
    Write-Host "    - $target"
}
Write-Host "  Server    : $ServerUrl"
Write-Host "  RT-CLIENT : $RtUrl"
Write-Host "  Headed    : $($Headed.IsPresent)"
Write-Host ""

Write-Host "[1/3] Health checks..." -ForegroundColor Yellow

# Check MES server - parse JSON and print each adapter's health.
# A timeout or connection error is a WARNING only; tests continue.
$serverOk = $false
$healthUrl = "$ServerUrl/health"
try {
    $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) {
        $serverOk = $true
        Write-Host "  [OK]   MES server ($healthUrl) -> 200" -ForegroundColor Green
        try {
            $body = $r.Content | ConvertFrom-Json
            Write-Host "         status=$($body.status)  auth=$($body.auth_mode)  plugins=$($body.plugins_loaded)" -ForegroundColor DarkGray
            if ($body.adapters) {
                foreach ($prop in $body.adapters.PSObject.Properties) {
                    $icon   = if ($prop.Value) { "[OK]  " } else { "[WARN]" }
                    $colour = if ($prop.Value) { "DarkGray" } else { "Yellow" }
                    Write-Host "         adapter $icon $($prop.Name)" -ForegroundColor $colour
                }
            }
        } catch { <# JSON parse failure is non-fatal #> }
    }
    else {
        Write-Host "  [WARN] MES server ($healthUrl) -> $($r.StatusCode) - continuing anyway" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  [WARN] MES server ($healthUrl) -> $($_.Exception.Message) - continuing anyway" -ForegroundColor Yellow
}

# Check RT-CLIENT - hard stop if unreachable (browser tests need the UI).
$rtOk = $false
try {
    $r = Invoke-WebRequest -Uri $RtUrl -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) {
        $rtOk = $true
        Write-Host "  [OK]   RT-CLIENT ($RtUrl) -> $($r.StatusCode)" -ForegroundColor Green
    }
    else {
        Write-Host "  [FAIL] RT-CLIENT ($RtUrl) -> $($r.StatusCode)" -ForegroundColor Red
    }
}
catch {
    Write-Host "  [FAIL] RT-CLIENT ($RtUrl) -> $($_.Exception.Message)" -ForegroundColor Red
}

if (-not $rtOk) {
    Write-Host ""
    Write-Host "ERROR: RT-CLIENT is not reachable. Start the client before running the audit." -ForegroundColor Red
    exit 1
}

if (-not $serverOk) {
    Write-Host "  [WARN] MES server unreachable - API-level tests may fail." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/4] Normalizing demo inventory..." -ForegroundColor Yellow

Push-Location (Join-Path $RepoRoot "server")
try {
    & $Python $PrepScript
    if ($LASTEXITCODE -ne 0) {
        throw "Inventory normalization failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "[3/4] Running pytest ($Scope)..." -ForegroundColor Yellow

$env:SQA_SERVER_URL = $ServerUrl
$env:SQA_RT_URL     = $RtUrl
$env:SQA_HEADED     = if ($Headed) { "1" } else { "0" }

Push-Location $RepoRoot
try {
    & $Python -m pytest $TestTargets -v --tb=short
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "[4/4] Updating HEARTBEAT.md..." -ForegroundColor Yellow

if ($ExitCode -eq 0) {
    $icon   = "PASS"
    $detail = "all tests passed"
}
else {
    $icon   = "FAIL"
    $detail = "FAILURES - see SQA/reports/latest/report.html"
}

$entry = @"

## $Timestamp - RT-AUDIT [$icon]
- Scope  : $Scope
- Server : $ServerUrl  RT-CLIENT : $RtUrl
- pytest : $detail
- Report : SQA/reports/latest/report.html
"@

Add-Content -Path $Heartbeat -Value $entry

Write-Host "  HEARTBEAT.md updated."
Write-Host ""
Write-Host "Audit complete - [$icon]"
exit $ExitCode