<#
.SYNOPSIS
    Serve a MES AI client application from its production build (dist/).

.DESCRIPTION
    Builds the selected client if no dist/ folder exists (or when -Build is
    given), then serves the production bundle via 'vite preview', which
    honours the same vite.config.ts proxy rules used by the dev server.

    The build version (from package.json) and build timestamp (from
    dist/index.html) are printed before the server starts.

.PARAMETER Client
    Required. Client to run (case-insensitive):
      dt-client        Design-Time client          (default port 4173)
      rt-client        Run-Time client             (default port 4176)
      erp-sim          ERP Simulator               (default port 4174)
      equipment-sim    Equipment Simulator         (default port 4175)

.PARAMETER Port
    Optional. Override the preview server port.

.PARAMETER ServerUrl
    Optional. URL of the MES server to proxy API calls to.
    Defaults to http://localhost:8082.
    Sets the MES_SERVER_URL environment variable read by vite.config.ts.

.PARAMETER Build
    Force a fresh npm run build before starting the preview server.

.PARAMETER Help
    Show this help message.

.EXAMPLE
    .\run-client-production.ps1 dt-client
    .\run-client-production.ps1 rt-client -Port 4000
    .\run-client-production.ps1 rt-client -ServerUrl http://localhost:8083
    .\run-client-production.ps1 erp-sim -Build
    .\run-client-production.ps1 equipment-sim
    .\run-client-production.ps1 -Help
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
    [switch]$Build,

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
  .\run-client-production.ps1 <Client> [options]

ARGUMENTS
  Client               (required)  Client application to serve (case-insensitive):
                                     dt-client       Design-Time client     (port 4173)
                                     rt-client       Run-Time client        (port 4176)
                                     erp-sim         ERP Simulator          (port 4174)
                                     equipment-sim   Equipment Simulator    (port 4175)

OPTIONS
  -Port       NUM   Override the Vite preview server port.
  -ServerUrl  URL   MES server to proxy API calls to (default: http://localhost:8082).
                    Sets MES_SERVER_URL env var read by vite.config.ts.
  -Build            Force a fresh production build before serving.
  -Help             Show this help message.

EXAMPLES
  .\run-client-production.ps1 dt-client
  .\run-client-production.ps1 rt-client -Port 4000
  .\run-client-production.ps1 rt-client -ServerUrl http://localhost:8083
  .\run-client-production.ps1 erp-sim -Build
  .\run-client-production.ps1 equipment-sim

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
    "dt-client"      = @{ Dir = "clients\design_time";         DefaultPort = 4173; Label = "Design-Time Client" }
    "rt-client"      = @{ Dir = "clients\run_time";            DefaultPort = 4176; Label = "Run-Time Client" }
    "erp-sim"        = @{ Dir = "clients\erp_simulator";       DefaultPort = 4174; Label = "ERP Simulator" }
    "equipment-sim"  = @{ Dir = "clients\equipment_simulator"; DefaultPort = 4175; Label = "Equipment Simulator" }
}

$key = $Client.ToLower()
if (-not $clientMap.ContainsKey($key)) {
    Write-Error "Unknown client '$Client'.`nValid options: dt-client, rt-client, erp-sim, equipment-sim`nRun .\run-client-production.ps1 -Help for usage."
    exit 1
}

$info             = $clientMap[$key]
$scriptRoot       = $PSScriptRoot
$clientDir        = Join-Path $scriptRoot $info.Dir
$effectivePort    = if ($Port -gt 0) { $Port } else { $info.DefaultPort }
$effectiveServerUrl = if ($ServerUrl -ne "") { $ServerUrl } else { "http://localhost:8082" }
$distDir          = Join-Path $clientDir "dist"
$packageJsonPath  = Join-Path $clientDir "package.json"

if (-not (Test-Path $clientDir)) {
    Write-Error "Client directory not found: $clientDir"
    exit 1
}

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
# Build if dist/ is missing or -Build requested
# ---------------------------------------------------------------------------
if ($Build -or -not (Test-Path $distDir)) {
    if (-not (Test-Path $distDir)) {
        Write-Host "No dist/ folder found - running production build..."
    } else {
        Write-Host "Running production build (-Build flag set)..."
    }
    Push-Location $clientDir
    try {
        $env:MES_SERVER_URL = $effectiveServerUrl
        npm run build
        if ($LASTEXITCODE -ne 0) {
            Write-Error "npm run build failed (exit code $LASTEXITCODE)."
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
    }
}

# ---------------------------------------------------------------------------
# Build version
# ---------------------------------------------------------------------------
$buildVersion   = "unknown"
$buildTimestamp = "unknown"

if (Test-Path $packageJsonPath) {
    try {
        $pkg = Get-Content $packageJsonPath -Raw | ConvertFrom-Json
        $buildVersion = $pkg.version
    } catch { }
}

$distIndex = Join-Path $distDir "index.html"
if (Test-Path $distIndex) {
    $buildTimestamp = (Get-Item $distIndex).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "MES AI Client - Production"
Write-Host "=========================="
Write-Host "  Client        : $($info.Label)"
Write-Host "  Version       : $buildVersion"
Write-Host "  Built         : $buildTimestamp"
Write-Host "  Serving from  : $distDir"
Write-Host "  URL           : http://localhost:${effectivePort}"
Write-Host "  MES Server    : $effectiveServerUrl"
Write-Host ""

# ---------------------------------------------------------------------------
# Start Vite preview server (serves dist/ with vite.config.ts proxy rules)
# ---------------------------------------------------------------------------
Write-Host "Starting $($info.Label) (production)..."
Write-Host "Press Ctrl+C to stop."
Write-Host ""

$env:MES_SERVER_URL = $effectiveServerUrl
Push-Location $clientDir
try {
    if ($Port -gt 0) {
        npx vite preview --port $effectivePort
    } else {
        npx vite preview --port $effectivePort
    }
} finally {
    Pop-Location
}
