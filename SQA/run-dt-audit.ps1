<#
.SYNOPSIS
    Run the DT-CLIENT SQA audit: health checks + pytest + Playwright.

.PARAMETER Scope
    Portion of the DT suite to run.
    - uom            : Units of Measure tests only
    - users-and-groups : Users and Roles tests only
    - reasons        : Reason Codes tests only
    - physical-model : Sites/Areas/Lines/Work Cells tests only
    - data-definitions : Data Definitions tests only
    - storage-locations : Storage Locations tests only
    - materials      : Materials tests only
    - routes         : Standalone Route Editor tests only
    - equipment      : Equipment DT tests only
    - products       : Products and BOM DT tests only
    - work-schedule  : Work Schedule tests only
    - all            : All DT-CLIENT SQA tests

.PARAMETER Headed
    Launch Playwright browser in headed mode (visible window). Default: headless.

.PARAMETER ServerUrl
    MES server base URL. Default: http://localhost:8082

.PARAMETER DtUrl
    DT-CLIENT base URL. Default: http://localhost:5173

.EXAMPLE
    .\run-dt-audit.ps1 -Scope all
    .\run-dt-audit.ps1 -Scope uom
    .\run-dt-audit.ps1 -Scope users-and-groups
    .\run-dt-audit.ps1 -Scope reasons
    .\run-dt-audit.ps1 -Scope physical-model
    .\run-dt-audit.ps1 -Scope data-definitions
    .\run-dt-audit.ps1 -Scope storage-locations
    .\run-dt-audit.ps1 -Scope materials
    .\run-dt-audit.ps1 -Scope routes
    .\run-dt-audit.ps1 -Scope equipment
    .\run-dt-audit.ps1 -Scope products
    .\run-dt-audit.ps1 -Scope work-schedule -Headed
    .\run-dt-audit.ps1 -Scope all -ServerUrl http://localhost:8082 -DtUrl http://localhost:5173
#>
param(
    [ValidateSet("uom", "users-and-groups", "reasons", "physical-model", "data-definitions", "storage-locations", "materials", "routes", "equipment", "products", "work-schedule", "all")]
    [string]$Scope,
    [switch]$Headed,
    [switch]$Help,
    [string]$ServerUrl = "http://localhost:8082",
    [string]$DtUrl     = "http://localhost:5173"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot  = Split-Path $PSScriptRoot -Parent
$Python    = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$Heartbeat = Join-Path $PSScriptRoot "HEARTBEAT.md"

function Show-Usage {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\run-dt-audit.ps1 -Scope <uom|users-and-groups|reasons|physical-model|data-definitions|storage-locations|materials|routes|equipment|products|work-schedule|all> [-Headed] [-ServerUrl <url>] [-DtUrl <url>]"
    Write-Host ""
    Write-Host "Scopes:" -ForegroundColor Yellow
    Write-Host "  uom            Run Units of Measure DT tests only"
    Write-Host "  users-and-groups Run Users and Roles DT tests only"
    Write-Host "  reasons        Run Reason Codes DT tests only"
    Write-Host "  physical-model Run Sites/Areas/Lines/Work Cells DT tests only"
    Write-Host "  data-definitions Run Data Definitions DT tests only"
    Write-Host "  storage-locations Run Storage Locations DT tests only"
    Write-Host "  materials      Run Materials DT tests only"
    Write-Host "  routes         Run Standalone Route Editor DT tests only"
    Write-Host "  equipment      Run Equipment DT tests only"
    Write-Host "  products       Run Products and BOM DT tests only"
    Write-Host "  work-schedule  Run Work Schedule DT tests only"
    Write-Host "  all            Run the full DT SQA suite"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\run-dt-audit.ps1 -Scope uom"
    Write-Host "  .\run-dt-audit.ps1 -Scope users-and-groups"
    Write-Host "  .\run-dt-audit.ps1 -Scope reasons"
    Write-Host "  .\run-dt-audit.ps1 -Scope physical-model"
    Write-Host "  .\run-dt-audit.ps1 -Scope data-definitions"
    Write-Host "  .\run-dt-audit.ps1 -Scope storage-locations"
    Write-Host "  .\run-dt-audit.ps1 -Scope materials"
    Write-Host "  .\run-dt-audit.ps1 -Scope routes"
    Write-Host "  .\run-dt-audit.ps1 -Scope equipment"
    Write-Host "  .\run-dt-audit.ps1 -Scope products"
    Write-Host "  .\run-dt-audit.ps1 -Scope work-schedule -Headed"
    Write-Host "  .\run-dt-audit.ps1 -Scope all -ServerUrl http://localhost:8082 -DtUrl http://localhost:5173"
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
        "uom" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_uom_crud.py")
            )
        }
        "users-and-groups" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_auth_admin_crud.py")
            )
        }
        "reasons" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_reason_crud.py")
            )
        }
        "physical-model" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_physical_model_crud.py")
            )
        }
        "data-definitions" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_data_definition_crud.py")
            )
        }
        "storage-locations" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_storage_location_crud.py")
            )
        }
        "materials" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_material_crud.py")
            )
        }
        "routes" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_route_editor_crud.py")
            )
        }
        "equipment" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_equipment_crud.py")
            )
        }
        "products" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_product_crud.py"),
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_product_route_crud.py"),
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_product_bom_crud.py")
            )
        }
        "work-schedule" {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_work_schedule_crud.py"),
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_work_schedule_shift_crud.py"),
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_work_schedule_rotation_crud.py"),
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_work_schedule_team_crud.py"),
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_work_schedule_non_working_period_crud.py"),
                (Join-Path $PSScriptRoot "modules\SQA-DT\test_work_schedule_queries.py")
            )
        }
        default {
            return @(
                (Join-Path $PSScriptRoot "modules\SQA-DT")
            )
        }
    }
}

$TestTargets = Resolve-TestTargets -SelectedScope $Scope

Write-Host ""
Write-Host "MES AI - DT SQA Audit" -ForegroundColor Cyan
Write-Host "  Scope     : $Scope"
Write-Host "  Targets   :"
foreach ($target in $TestTargets) {
    Write-Host "    - $target"
}
Write-Host "  Server    : $ServerUrl"
Write-Host "  DT-CLIENT : $DtUrl"
Write-Host "  Headed    : $($Headed.IsPresent)"
Write-Host ""

# --- 1. Health checks --------------------------------------------------------
Write-Host "[1/3] Health checks..." -ForegroundColor Yellow

# Check MES server — parse JSON and print each adapter's health.
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

# Check DT-CLIENT — hard stop if unreachable (browser tests need the UI).
$dtOk = $false
try {
    $r = Invoke-WebRequest -Uri $DtUrl -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) {
        $dtOk = $true
        Write-Host "  [OK]   DT-CLIENT ($DtUrl) -> $($r.StatusCode)" -ForegroundColor Green
    }
    else {
        Write-Host "  [FAIL] DT-CLIENT ($DtUrl) -> $($r.StatusCode)" -ForegroundColor Red
    }
}
catch {
    Write-Host "  [FAIL] DT-CLIENT ($DtUrl) -> $($_.Exception.Message)" -ForegroundColor Red
}

if (-not $dtOk) {
    Write-Host ""
    Write-Host "ERROR: DT-CLIENT is not reachable. Start the client before running the audit." -ForegroundColor Red
    exit 1
}

if (-not $serverOk) {
    Write-Host "  [WARN] MES server unreachable - API-level tests may fail." -ForegroundColor Yellow
}

# --- 2. Run pytest + Playwright ----------------------------------------------
Write-Host ""
Write-Host "[2/3] Running pytest ($Scope)..." -ForegroundColor Yellow

$env:SQA_SERVER_URL = $ServerUrl
$env:SQA_DT_URL     = $DtUrl
$env:SQA_HEADED     = if ($Headed) { "1" } else { "0" }

Push-Location $RepoRoot
try {
    & $Python -m pytest $TestTargets -v --tb=short
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

## $Timestamp - DT-AUDIT [$icon]
- Scope  : $Scope
- Server : $ServerUrl  DT-CLIENT : $DtUrl
- pytest : $detail
- Report : SQA/reports/latest/report.html
"@

Add-Content -Path $Heartbeat -Value $entry
Write-Host "  HEARTBEAT.md updated." -ForegroundColor $colour

Write-Host ""
Write-Host "Audit complete - [$icon]" -ForegroundColor $colour
exit $ExitCode
