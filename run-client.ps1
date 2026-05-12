<#
.SYNOPSIS
    Start a MES AI client application (Vite dev server).

.DESCRIPTION
    Installs npm dependencies if node_modules is missing, then starts the
    Vite development server for the selected client.  An optional port
    overrides the client's default.

.PARAMETER Client
    Required. Client to run (case-insensitive):
      dt-client        Design-Time client          (default port 5173)
      rt-client        Run-Time client             (default port 5176)
      erp-sim          ERP Simulator               (default port 5174)
      equipment-sim    Equipment Simulator         (default port 5175)

.PARAMETER Port
    Optional. Override the Vite dev server port.

.PARAMETER ServerUrl
    Optional. URL of the MES server to proxy API calls to.
    Defaults to http://localhost:8082.
    Sets the MES_SERVER_URL environment variable read by vite.config.ts.

.PARAMETER Help
    Show this help message.

.EXAMPLE
    .\run-client.ps1 dt-client
    .\run-client.ps1 rt-client -Port 3000
    .\run-client.ps1 rt-client -ServerUrl http://localhost:8083
    .\run-client.ps1 erp-sim
    .\run-client.ps1 equipment-sim -Port 5200
    .\run-client.ps1 -Help
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Client = "",

    [Parameter()]
    [int]$Port = 0,

    [Parameter()]
    [string]$ServerUrl = "",

    [Parameter()]
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
function Show-Help {
    Write-Host @"

USAGE
  .\run-client.ps1 <Client> [options]

ARGUMENTS
  Client               (required)  Client application to start (case-insensitive):
                                     dt-client       Design-Time client     (port 5173)
                                     rt-client       Run-Time client        (port 5176)
                                     erp-sim         ERP Simulator          (port 5174)
                                     equipment-sim   Equipment Simulator    (port 5175)

OPTIONS
  -Port       NUM   Override the Vite dev server port.
  -ServerUrl  URL   MES server to proxy API calls to (default: http://localhost:8082).
                    Sets MES_SERVER_URL env var read by vite.config.ts.
  -Help             Show this help message.

EXAMPLES
  .\run-client.ps1 dt-client
  .\run-client.ps1 rt-client -Port 3000
  .\run-client.ps1 rt-client -ServerUrl http://localhost:8083
  .\run-client.ps1 erp-sim
  .\run-client.ps1 equipment-sim -Port 5200

"@
}

if ($Help -or $Client -eq "") {
    Show-Help
    exit 0
}

# ---------------------------------------------------------------------------
# Resolve client
# ---------------------------------------------------------------------------
$clientMap = @{
    "dt-client"      = @{ Dir = "clients\design_time";       DefaultPort = 5173; Label = "Design-Time Client" }
    "rt-client"      = @{ Dir = "clients\run_time";          DefaultPort = 5176; Label = "Run-Time Client" }
    "erp-sim"        = @{ Dir = "clients\erp_simulator";     DefaultPort = 5174; Label = "ERP Simulator" }
    "equipment-sim"  = @{ Dir = "clients\equipment_simulator"; DefaultPort = 5175; Label = "Equipment Simulator" }
}

$key = $Client.ToLower()
if (-not $clientMap.ContainsKey($key)) {
    Write-Error "Unknown client '$Client'.`nValid options: dt-client, rt-client, erp-sim, equipment-sim`nRun .\run-client.ps1 -Help for usage."
    exit 1
}

$info        = $clientMap[$key]
$scriptRoot  = $PSScriptRoot
$clientDir   = Join-Path $scriptRoot $info.Dir
$effectivePort = if ($Port -gt 0) { $Port } else { $info.DefaultPort }

if (-not (Test-Path $clientDir)) {
    Write-Error "Client directory not found: $clientDir"
    exit 1
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "MES AI Client Startup"
Write-Host "====================="
$effectiveServerUrl = if ($ServerUrl -ne "") { $ServerUrl } else { "http://localhost:8082" }
Write-Host "  Client     : $($info.Label)"
Write-Host "  Dir        : $clientDir"
Write-Host "  URL        : http://localhost:${effectivePort}"
Write-Host "  MES Server : $effectiveServerUrl"
Write-Host ""

# ---------------------------------------------------------------------------
# Install dependencies if needed
# ---------------------------------------------------------------------------
$nodeModules = Join-Path $clientDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "Installing npm dependencies..."
    Push-Location $clientDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Error "npm install failed (exit code $LASTEXITCODE)."
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
    }
}

# ---------------------------------------------------------------------------
# Start Vite dev server
# ---------------------------------------------------------------------------
Write-Host "Starting $($info.Label)..."
Write-Host "Press Ctrl+C to stop."
Write-Host ""

$env:MES_SERVER_URL = $effectiveServerUrl
Push-Location $clientDir
try {
    if ($Port -gt 0) {
        npx vite --port $effectivePort
    } else {
        npx vite
    }
} finally {
    Pop-Location
}
