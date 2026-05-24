<#
.SYNOPSIS
    Manage a MES AI Vite client application as a Windows service using NSSM.

.DESCRIPTION
    Installs, uninstalls, starts, stops, restarts, or queries the status of
    a MES AI Vite client (dt-client, rt-client, erp-sim, or equipment-sim)
    as a native Windows service.  NSSM is checked for and installed
    automatically when needed.

    All runtime parameters are read from a configuration file so that
    nothing sensitive appears on the command line.

.PARAMETER Action
    Required.  One of: install | uninstall | start | stop | restart | status

.PARAMETER ConfigFile
    Path to the configuration file.
    Default: rt-service.conf in the same directory as this script.
    See rt-service.conf for the full list of keys.

.EXAMPLE
    # Install the RT-client service:
    .\run-client-service.ps1 install

.EXAMPLE
    # Use a custom config file (e.g. for the DT client):
    .\run-client-service.ps1 install -ConfigFile .\dt-service.conf

.EXAMPLE
    .\run-client-service.ps1 status
    .\run-client-service.ps1 restart
    .\run-client-service.ps1 uninstall
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Action = "",

    [Parameter(Position = 1)]
    [string]$ConfigFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colours ──────────────────────────────────────────────────────────────────
function Write-Step  { param([string]$Msg) Write-Host "  >> $Msg" -ForegroundColor Cyan }
function Write-OK    { param([string]$Msg) Write-Host "  OK $Msg" -ForegroundColor Green }
function Write-Warn  { param([string]$Msg) Write-Host " WARN $Msg" -ForegroundColor Yellow }
function Write-Fatal { param([string]$Msg) Write-Host "FATAL $Msg" -ForegroundColor Red; exit 1 }

# ── Resolve paths ─────────────────────────────────────────────────────────────
$ScriptRoot = $PSScriptRoot

if ($ConfigFile -eq "") {
    $ConfigFile = Join-Path $ScriptRoot "rt-service.conf"
}

# ── Client directory map ──────────────────────────────────────────────────────
$ClientMap = @{
    "dt-client"      = @{ Dir = "clients\design_time";        DefaultPort = 5173; Label = "Design-Time Client" }
    "rt-client"      = @{ Dir = "clients\run_time";           DefaultPort = 5176; Label = "Run-Time Client" }
    "erp-sim"        = @{ Dir = "clients\erp_simulator";      DefaultPort = 5174; Label = "ERP Simulator" }
    "equipment-sim"  = @{ Dir = "clients\equipment_simulator"; DefaultPort = 5175; Label = "Equipment Simulator" }
}

# ── Config parsing ────────────────────────────────────────────────────────────
function Read-Config {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        Write-Fatal "Configuration file not found: $Path`nCopy rt-service.conf and edit it."
    }
    $cfg = @{}
    $lineNo = 0
    foreach ($line in Get-Content $Path) {
        $lineNo++
        $trimmed = $line.Trim()
        if ($trimmed -eq "" -or $trimmed.StartsWith("#")) { continue }
        if ($trimmed -notmatch '^([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            Write-Warn "Ignoring unrecognised line $lineNo in ${Path}: $line"
            continue
        }
        $cfg[$Matches[1].Trim()] = $Matches[2].Trim()
    }
    return $cfg
}

function Get-CfgValue {
    param([hashtable]$Cfg, [string]$Key, [string]$Default = "")
    if ($Cfg.ContainsKey($Key) -and $Cfg[$Key] -ne "") { return $Cfg[$Key] }
    return $Default
}

# ── Node.js discovery ─────────────────────────────────────────────────────────
function Find-Node {
    $found = Get-Command node -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }

    $candidates = @(
        "$env:ProgramFiles\nodejs\node.exe",
        "${env:ProgramFiles(x86)}\nodejs\node.exe",
        "$env:APPDATA\nvm\v*\node.exe"
    )
    foreach ($c in $candidates) {
        $expanded = Resolve-Path $c -ErrorAction SilentlyContinue
        if ($expanded) { return $expanded.Path }
    }
    return $null
}

# ── NSSM installation ─────────────────────────────────────────────────────────
function Find-Nssm {
    $found = Get-Command nssm -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    $candidates = @(
        "$env:ProgramFiles\NSSM\nssm.exe",
        "${env:ProgramFiles(x86)}\NSSM\nssm.exe",
        "C:\ProgramData\chocolatey\bin\nssm.exe",
        "C:\tools\nssm\win64\nssm.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

function Install-Nssm {
    Write-Step "NSSM not found — attempting automatic installation..."

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Step "Installing NSSM via winget..."
        winget install --id NSSM.NSSM --silent --accept-source-agreements --accept-package-agreements | Out-Host
        if ($LASTEXITCODE -eq 0) {
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("Path", "User")
            $path = Find-Nssm
            if ($path) { Write-OK "NSSM installed via winget at: $path"; return $path }
        }
    }

    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Step "Installing NSSM via Chocolatey..."
        choco install nssm -y --no-progress | Out-Host
        if ($LASTEXITCODE -eq 0) {
            $path = Find-Nssm
            if ($path) { Write-OK "NSSM installed via Chocolatey at: $path"; return $path }
        }
    }

    Write-Step "Downloading NSSM 2.24 (64-bit)..."
    $nssmZip  = Join-Path $env:TEMP "nssm-2.24.zip"
    $nssmDir  = Join-Path $env:TEMP "nssm-2.24"
    $nssmDest = Join-Path $env:ProgramFiles "NSSM"
    try {
        Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" `
            -OutFile $nssmZip -UseBasicParsing
        Expand-Archive -Path $nssmZip -DestinationPath $env:TEMP -Force
        $nssmExe = Join-Path $nssmDir "win64\nssm.exe"
        if (-not (Test-Path $nssmExe)) {
            Write-Fatal "NSSM archive did not contain the expected binary at: $nssmExe"
        }
        New-Item -ItemType Directory -Path $nssmDest -Force | Out-Null
        Copy-Item $nssmExe -Destination $nssmDest -Force
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        if ($machinePath -notlike "*$nssmDest*") {
            [System.Environment]::SetEnvironmentVariable("Path", "$machinePath;$nssmDest", "Machine")
        }
        $env:Path = $env:Path + ";$nssmDest"
        $installed = Join-Path $nssmDest "nssm.exe"
        Write-OK "NSSM installed to: $installed"
        return $installed
    } catch {
        Write-Fatal "Automatic NSSM installation failed: $_`n`nInstall it manually:`n  winget install NSSM.NSSM`n  -or-  https://nssm.cc/download"
    }
}

function Get-NssmPath {
    $path = Find-Nssm
    if (-not $path) {
        $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
        if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            Write-Fatal "NSSM is not installed and this script is not running as Administrator.`nRe-run as Administrator to allow automatic installation."
        }
        $path = Install-Nssm
        if (-not $path) { Write-Fatal "Could not install NSSM.  Install it manually and re-run." }
    }
    return $path
}

# ── Service helpers ───────────────────────────────────────────────────────────
function Get-ServiceStatus {
    param([string]$Name)
    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $svc) { return "not-installed" }
    return $svc.Status.ToString().ToLower()
}

function Assert-Admin {
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Fatal "This action requires Administrator privileges.  Re-run as Administrator."
    }
}

# ── Resolve client info from config ──────────────────────────────────────────
function Resolve-ClientInfo {
    param([hashtable]$Cfg)
    $clientKey = (Get-CfgValue $Cfg "Client" "rt-client").ToLower()
    if (-not $ClientMap.ContainsKey($clientKey)) {
        Write-Fatal "Unknown Client '$clientKey'.`nValid values: dt-client, rt-client, erp-sim, equipment-sim"
    }
    return $ClientMap[$clientKey]
}

# ── Main ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "MES AI Client Service Manager" -ForegroundColor White
Write-Host "=============================" -ForegroundColor White

if ($Action -eq "") {
    Write-Host ""
    Write-Host "USAGE" -ForegroundColor Yellow
    Write-Host "  .\run-client-service.ps1 <action> [-ConfigFile <path>]"
    Write-Host ""
    Write-Host "ACTIONS" -ForegroundColor Yellow
    Write-Host "  install    Register the Vite client as a Windows service (requires Admin)"
    Write-Host "  uninstall  Remove the Windows service (requires Admin)"
    Write-Host "  start      Start the service (requires Admin)"
    Write-Host "  stop       Stop the service (requires Admin)"
    Write-Host "  restart    Restart the service (requires Admin)"
    Write-Host "  status     Show current service status"
    Write-Host ""
    Write-Host "OPTIONS" -ForegroundColor Yellow
    Write-Host "  -ConfigFile <path>   Path to config file (default: rt-service.conf)"
    Write-Host ""
    Write-Host "EXAMPLES" -ForegroundColor Yellow
    Write-Host "  .\run-client-service.ps1 install"
    Write-Host "  .\run-client-service.ps1 install -ConfigFile .\dt-service.conf"
    Write-Host "  .\run-client-service.ps1 start"
    Write-Host "  .\run-client-service.ps1 status"
    Write-Host "  .\run-client-service.ps1 uninstall"
    Write-Host ""
    Write-Host "  See rt-service.conf for all available configuration keys."
    Write-Host ""
    exit 0
}

$validActions = @("install", "uninstall", "start", "stop", "restart", "status")
if ($Action.ToLower() -notin $validActions) {
    Write-Host "ERROR: Unknown action '$Action'.  Valid actions: $($validActions -join ', ')" -ForegroundColor Red
    Write-Host "Run .\run-client-service.ps1 with no arguments to see usage."
    exit 1
}

# ── STATUS ───────────────────────────────────────────────────────────────────
if ($Action -ieq "status") {
    $cfg    = Read-Config $ConfigFile
    $name   = Get-CfgValue $cfg "ServiceName" "MesAI-RtClient"
    $info   = Resolve-ClientInfo $cfg
    $status = Get-ServiceStatus $name
    $colour = if ($status -eq "running") { "Green" }
              elseif ($status -eq "not-installed") { "Yellow" }
              else { "Red" }
    Write-Host "  Client   : $($info.Label)"
    Write-Host "  Service  : $name"
    Write-Host "  Status   : $status" -ForegroundColor $colour
    exit 0
}

# ── STOP ─────────────────────────────────────────────────────────────────────
if ($Action -ieq "stop") {
    Assert-Admin
    $cfg    = Read-Config $ConfigFile
    $name   = Get-CfgValue $cfg "ServiceName" "MesAI-RtClient"
    $nssm   = Get-NssmPath
    $status = Get-ServiceStatus $name
    if ($status -eq "not-installed") { Write-Warn "Service '$name' is not installed."; exit 0 }
    if ($status -ne "running")       { Write-Warn "Service '$name' is already stopped (status: $status)."; exit 0 }
    Write-Step "Stopping service '$name'..."
    & $nssm stop $name confirm
    Write-OK "Service stopped."
    exit 0
}

# ── START ─────────────────────────────────────────────────────────────────────
if ($Action -ieq "start") {
    Assert-Admin
    $cfg    = Read-Config $ConfigFile
    $name   = Get-CfgValue $cfg "ServiceName" "MesAI-RtClient"
    $nssm   = Get-NssmPath
    $status = Get-ServiceStatus $name
    if ($status -eq "not-installed") { Write-Fatal "Service '$name' is not installed.  Run: .\run-client-service.ps1 install" }
    if ($status -eq "running")       { Write-Warn "Service '$name' is already running."; exit 0 }
    Write-Step "Starting service '$name'..."
    & $nssm start $name
    Write-OK "Service started."
    exit 0
}

# ── RESTART ───────────────────────────────────────────────────────────────────
if ($Action -ieq "restart") {
    Assert-Admin
    $cfg  = Read-Config $ConfigFile
    $name = Get-CfgValue $cfg "ServiceName" "MesAI-RtClient"
    $nssm = Get-NssmPath
    if ((Get-ServiceStatus $name) -eq "not-installed") {
        Write-Fatal "Service '$name' is not installed.  Run: .\run-client-service.ps1 install"
    }
    Write-Step "Restarting service '$name'..."
    & $nssm restart $name
    Write-OK "Service restarted."
    exit 0
}

# ── UNINSTALL ─────────────────────────────────────────────────────────────────
if ($Action -ieq "uninstall") {
    Assert-Admin
    $cfg    = Read-Config $ConfigFile
    $name   = Get-CfgValue $cfg "ServiceName" "MesAI-RtClient"
    $nssm   = Get-NssmPath
    $status = Get-ServiceStatus $name
    if ($status -eq "not-installed") { Write-Warn "Service '$name' is not installed."; exit 0 }
    if ($status -eq "running") {
        Write-Step "Stopping running service before removal..."
        & $nssm stop $name confirm
    }
    Write-Step "Removing service '$name'..."
    & $nssm remove $name confirm
    Write-OK "Service '$name' removed."
    exit 0
}

# ── INSTALL ───────────────────────────────────────────────────────────────────
Assert-Admin

$cfg = Read-Config $ConfigFile

# Resolve client
$clientKey  = (Get-CfgValue $cfg "Client" "rt-client").ToLower()
$info       = Resolve-ClientInfo $cfg
$clientDir  = Join-Path $ScriptRoot $info.Dir

if (-not (Test-Path $clientDir)) {
    Write-Fatal "Client directory not found: $clientDir"
}

# Ensure node_modules is present
$nodeModules = Join-Path $clientDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Step "node_modules not found — running npm install in $clientDir ..."
    Push-Location $clientDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { Write-Fatal "npm install failed (exit $LASTEXITCODE)." }
    } finally { Pop-Location }
    Write-OK "npm install complete."
}

# Locate vite binary and node.exe
$viteBin = Join-Path $clientDir "node_modules\vite\bin\vite.js"
if (-not (Test-Path $viteBin)) {
    Write-Fatal "Vite binary not found at: $viteBin`nRun npm install in $clientDir."
}

$nodeExe = Find-Node
if (-not $nodeExe) {
    Write-Fatal "Node.js not found on PATH or in standard locations.`nInstall Node.js 20+ from https://nodejs.org and re-run."
}

$nssm = Get-NssmPath

# Read config values
$svcName    = Get-CfgValue $cfg "ServiceName"        "MesAI-RtClient"
$svcDisplay = Get-CfgValue $cfg "ServiceDisplayName" "MES AI $($info.Label)"
$svcDesc    = Get-CfgValue $cfg "ServiceDescription" "MES AI $($info.Label) Vite server"
$port       = Get-CfgValue $cfg "Port"               $info.DefaultPort.ToString()
$bindHost   = Get-CfgValue $cfg "BindHost"           "0.0.0.0"
$serverUrl  = Get-CfgValue $cfg "ServerUrl"          "http://localhost:8082"
$startType  = Get-CfgValue $cfg "StartType"          "auto"
$logDir     = Get-CfgValue $cfg "LogDir"             ""

if ($logDir -eq "") { $logDir = Join-Path $clientDir "logs" }
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

# Summary
Write-Host ""
Write-Host "  Client     : $($info.Label)  ($clientKey)"
Write-Host "  Service    : $svcName"
Write-Host "  Display    : $svcDisplay"
Write-Host "  URL        : http://${bindHost}:${port}"
Write-Host "  MES Server : $serverUrl"
Write-Host "  Start Type : $startType"
Write-Host "  Log Dir    : $logDir"
Write-Host "  Node       : $nodeExe"
Write-Host "  Vite       : $viteBin"
Write-Host ""

# Remove existing service if present
$existing = Get-ServiceStatus $svcName
if ($existing -ne "not-installed") {
    Write-Step "Existing service '$svcName' found (status: $existing) — removing before reinstall..."
    if ($existing -eq "running") { & $nssm stop $svcName confirm }
    & $nssm remove $svcName confirm
    Write-OK "Old service removed."
}

# Register with NSSM
Write-Step "Installing service '$svcName'..."

$viteArgs = "`"$viteBin`" --host $bindHost --port $port"

& $nssm install $svcName $nodeExe
& $nssm set     $svcName AppParameters  $viteArgs
& $nssm set     $svcName AppDirectory   $clientDir
& $nssm set     $svcName DisplayName    $svcDisplay
& $nssm set     $svcName Description    $svcDesc

# Environment
& $nssm set $svcName AppEnvironmentExtra "MES_SERVER_URL=$serverUrl"

# Logging
& $nssm set $svcName AppStdout         (Join-Path $logDir "${svcName}-stdout.log")
& $nssm set $svcName AppStderr         (Join-Path $logDir "${svcName}-stderr.log")
& $nssm set $svcName AppRotateFiles    1
& $nssm set $svcName AppRotateOnline   1
& $nssm set $svcName AppRotateSeconds  86400
& $nssm set $svcName AppRotateBytes    10485760

# Restart on failure
& $nssm set $svcName AppExit         Default Restart
& $nssm set $svcName AppRestartDelay 5000
& $nssm set $svcName AppThrottle     0

# Start type
$nssmStart = switch ($startType.ToLower()) {
    "auto"          { "SERVICE_AUTO_START" }
    "delayed-auto"  { "SERVICE_DELAYED_AUTO_START" }
    "manual"        { "SERVICE_DEMAND_START" }
    "disabled"      { "SERVICE_DISABLED" }
    default         { "SERVICE_AUTO_START" }
}
& $nssm set $svcName Start $nssmStart

Write-OK "Service '$svcName' installed."
Write-Host ""
Write-Host "  Client URL : http://localhost:${port}"
Write-Host "  Logs       : $logDir"
Write-Host ""
Write-Host "  Start now  : .\run-client-service.ps1 start  -ConfigFile `"$ConfigFile`""
Write-Host "  Stop       : .\run-client-service.ps1 stop   -ConfigFile `"$ConfigFile`""
Write-Host "  Status     : .\run-client-service.ps1 status -ConfigFile `"$ConfigFile`""
Write-Host "  Uninstall  : .\run-client-service.ps1 uninstall -ConfigFile `"$ConfigFile`""
Write-Host ""
