<#
.SYNOPSIS
    Reset MES authentication mode to "none" in server/.env.

.DESCRIPTION
    Emergency recovery script for when the MES_AUTH_MODE has been set to
    "local" or "oidc" and access to dt-client is lost.

    Sets MES_AUTH_MODE=none in server/.env so the server accepts all
    requests without credentials after a restart.

    After regaining access, reconfigure authentication in the dt-client
    Settings page (Admin -> Settings).

.EXAMPLE
    .\reset-auth.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile    = Join-Path $ScriptDir "server\.env"

function Write-Ok($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  [  ]  $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [XX]  $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "MES Authentication Reset" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

# --- Verify .env exists -----------------------------------------------------
if (-not (Test-Path $EnvFile)) {
    Write-Err "server\.env not found at: $EnvFile"
    Write-Warn "Run install.ps1 first to create the environment file."
    exit 1
}

Write-Info "Found: $EnvFile"

# --- Read current value -----------------------------------------------------
$lines       = Get-Content $EnvFile
$currentMode = $null
foreach ($line in $lines) {
    if ($line -match '^\s*MES_AUTH_MODE\s*=\s*(.+)$') {
        $currentMode = $Matches[1].Trim()
        break
    }
}

if ($currentMode -eq "none") {
    Write-Ok "MES_AUTH_MODE is already set to 'none'. No changes needed."
    Write-Host ""
    exit 0
}

if ($null -ne $currentMode) {
    Write-Info "Current MES_AUTH_MODE: $currentMode"
} else {
    Write-Info "MES_AUTH_MODE not found in .env - it will be appended."
}

# --- Rewrite .env with MES_AUTH_MODE=none -----------------------------------
$found    = $false
$newLines = [System.Collections.Generic.List[string]]::new()

foreach ($line in $lines) {
    if ($line -match '^\s*MES_AUTH_MODE\s*=') {
        $newLines.Add("MES_AUTH_MODE=none")
        $found = $true
    } else {
        $newLines.Add($line)
    }
}

if (-not $found) {
    $newLines.Add("MES_AUTH_MODE=none")
}

$newLines | Set-Content $EnvFile -Encoding UTF8

Write-Ok "MES_AUTH_MODE set to 'none' in server\.env"

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart the MES server (run-server.ps1)."
Write-Host "  2. Open dt-client - login is no longer required."
Write-Host "  3. Go to Admin -> Settings to reconfigure authentication."
Write-Host ""
