<#
.SYNOPSIS
    Manage the MES AI server as a Windows service using NSSM.

.DESCRIPTION
    Installs, uninstalls, starts, stops, restarts, or queries the status of
    the MES AI uvicorn server as a native Windows service.  NSSM (Non-Sucking
    Service Manager) is checked for and installed automatically when needed.

    All runtime parameters are read from a configuration file so that no
    credentials appear on the command line or in process lists.

.PARAMETER Action
    Required.  One of: install | uninstall | start | stop | restart | status

.PARAMETER ConfigFile
    Path to the configuration file.
    Default: mes-service.conf in the same directory as this script.
    See mes-service.conf.example for the full list of keys.

.PARAMETER RunMigrations
    When present with the 'install' or 'start' actions, runs
    'alembic upgrade head' before (re-)starting the service.
    Use this on first install or after a schema change.

.EXAMPLE
    # Install the service (first-time setup):
    .\run-service.ps1 install -RunMigrations

.EXAMPLE
    # Use a custom config file:
    .\run-service.ps1 install -ConfigFile C:\mes\production.conf

.EXAMPLE
    # Stop, run migrations, start:
    .\run-service.ps1 stop
    .\run-service.ps1 install -RunMigrations
    .\run-service.ps1 start

.EXAMPLE
    .\run-service.ps1 status
    .\run-service.ps1 restart
    .\run-service.ps1 uninstall
#>

[CmdletBinding()]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingPlainTextForPassword', 'Password',
    Justification = 'Password is read from a config file and stored only in NSSM environment block.')]
param(
    [Parameter(Position = 0)]
    [string]$Action = "",

    [Parameter(Position = 1)]
    [string]$ConfigFile = "",

    [switch]$RunMigrations
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colours ─────────────────────────────────────────────────────────────────
function Write-Step  { param([string]$Msg) Write-Host "  >> $Msg" -ForegroundColor Cyan }
function Write-OK    { param([string]$Msg) Write-Host "  OK $Msg" -ForegroundColor Green }
function Write-Warn  { param([string]$Msg) Write-Host " WARN $Msg" -ForegroundColor Yellow }
function Write-Fatal { param([string]$Msg) Write-Host "FATAL $Msg" -ForegroundColor Red; exit 1 }

# ── Resolve paths ────────────────────────────────────────────────────────────
$ScriptRoot  = $PSScriptRoot
$ServerDir   = Join-Path $ScriptRoot "server"
$VenvPython  = Join-Path $ScriptRoot ".venv\Scripts\python.exe"
$VenvAlembic = Join-Path $ScriptRoot ".venv\Scripts\alembic.exe"

if ($ConfigFile -eq "") {
    $ConfigFile = Join-Path $ScriptRoot "mes-service.conf"
}

# ── Parse config file ────────────────────────────────────────────────────────
function Read-Config {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Fatal "Configuration file not found: $Path`nCopy mes-service.conf.example to mes-service.conf and edit it."
    }

    $cfg = @{}
    $lineNo = 0
    foreach ($line in Get-Content $Path) {
        $lineNo++
        $trimmed = $line.Trim()
        if ($trimmed -eq "" -or $trimmed.StartsWith("#")) { continue }
        if ($trimmed -notmatch '^([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            Write-Warn "Ignoring unrecognised line $lineNo in $Path`: $line"
            continue
        }
        $key   = $Matches[1].Trim()
        $value = $Matches[2].Trim()
        $cfg[$key] = $value
    }
    return $cfg
}

function Get-CfgValue {
    param([hashtable]$Cfg, [string]$Key, [string]$Default = "")
    if ($Cfg.ContainsKey($Key) -and $Cfg[$Key] -ne "") { return $Cfg[$Key] }
    return $Default
}

# ── NSSM installation ────────────────────────────────────────────────────────
function Find-Nssm {
    # 1. Already on PATH
    $found = Get-Command nssm -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }

    # 2. Common install locations
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

    # Try winget (Windows 11 / Server 2022+)
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Step "Installing NSSM via winget..."
        winget install --id NSSM.NSSM --silent --accept-source-agreements --accept-package-agreements | Out-Host
        if ($LASTEXITCODE -eq 0) {
            # winget installs to a path that may not be on PATH yet; refresh
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("Path", "User")
            $path = Find-Nssm
            if ($path) { Write-OK "NSSM installed via winget at: $path"; return $path }
        }
    }

    # Try Chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Step "Installing NSSM via Chocolatey..."
        choco install nssm -y --no-progress | Out-Host
        if ($LASTEXITCODE -eq 0) {
            $path = Find-Nssm
            if ($path) { Write-OK "NSSM installed via Chocolatey at: $path"; return $path }
        }
    }

    # Manual download fallback (64-bit, latest release)
    Write-Step "Downloading NSSM 2.24 (64-bit)..."
    $nssmZip  = Join-Path $env:TEMP "nssm-2.24.zip"
    $nssmDir  = Join-Path $env:TEMP "nssm-2.24"
    $nssmDest = Join-Path $env:ProgramFiles "NSSM"

    try {
        Invoke-WebRequest `
            -Uri "https://nssm.cc/release/nssm-2.24.zip" `
            -OutFile $nssmZip `
            -UseBasicParsing
        Expand-Archive -Path $nssmZip -DestinationPath $env:TEMP -Force
        $nssmExe = Join-Path $nssmDir "win64\nssm.exe"
        if (-not (Test-Path $nssmExe)) {
            Write-Fatal "NSSM archive did not contain the expected binary at: $nssmExe"
        }
        New-Item -ItemType Directory -Path $nssmDest -Force | Out-Null
        Copy-Item $nssmExe -Destination $nssmDest -Force
        # Add to machine PATH
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        if ($machinePath -notlike "*$nssmDest*") {
            [System.Environment]::SetEnvironmentVariable(
                "Path", "$machinePath;$nssmDest", "Machine")
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
        # Must be admin to install
        $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
        if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            Write-Fatal "NSSM is not installed and this script is not running as Administrator.`nRe-run as Administrator to allow automatic installation."
        }
        $path = Install-Nssm
        if (-not $path) {
            Write-Fatal "Could not install NSSM.  Install it manually and re-run."
        }
    }
    return $path
}

# ── Build DATABASE_URL from config ───────────────────────────────────────────
function Build-ConnectionString {
    param([hashtable]$Cfg)

    $dbType = (Get-CfgValue $Cfg "Database" "postgresql").ToLower()
    $dbName = Get-CfgValue $Cfg "DbName"    "mes_ai"
    $user   = Get-CfgValue $Cfg "Username"  "postgres"
    $pass   = Get-CfgValue $Cfg "Password"  "postgres"
    $server = Get-CfgValue $Cfg "DbServer"  "localhost"

    # Default ports
    $defaultPorts = @{ postgresql = 5432; mssql = 1433; oracle = 1521 }
    if (-not $defaultPorts.ContainsKey($dbType)) {
        Write-Fatal "Unknown Database value '$dbType'.  Valid options: PostgreSQL, MSSQL, Oracle"
    }

    $dbHost = "localhost"
    $dbPort = $defaultPorts[$dbType]
    if ($server -match '^(.+):(\d+)$') {
        $dbHost = $Matches[1]; $dbPort = [int]$Matches[2]
    } elseif ($server -ne "") {
        $dbHost = $server
    }

    $url = switch ($dbType) {
        "postgresql" { "postgresql+asyncpg://${user}:${pass}@${dbHost}:${dbPort}/${dbName}" }
        "mssql"      {
            # Detect ODBC driver version
            $odbcDrivers = Get-ItemProperty "HKLM:\SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers" `
                -ErrorAction SilentlyContinue
            $drv = if ($odbcDrivers."ODBC Driver 18 for SQL Server" -eq "Installed") {
                       "ODBC+Driver+18+for+SQL+Server"
                   } elseif ($odbcDrivers."ODBC Driver 17 for SQL Server" -eq "Installed") {
                       "ODBC+Driver+17+for+SQL+Server"
                   } else {
                       Write-Fatal "ODBC Driver for SQL Server is not installed.`nDownload from: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server"
                   }
            "mssql+pyodbc://${user}:${pass}@${dbHost}:${dbPort}/${dbName}?driver=${drv}"
        }
        "oracle"     { "oracle+oracledb://${user}:${pass}@${dbHost}:${dbPort}/${dbName}" }
    }

    return @{ Url = $url; DbType = $dbType; DbHost = $dbHost; DbPort = $dbPort; DbName = $dbName; User = $user }
}

# ── Alembic migrations ───────────────────────────────────────────────────────
function Invoke-Migrations {
    param([string]$DatabaseUrl)

    if (-not (Test-Path $VenvAlembic)) {
        Write-Warn "alembic.exe not found at $VenvAlembic — skipping migrations."
        return
    }

    Write-Step "Running Alembic migrations (alembic upgrade head)..."
    Push-Location $ServerDir
    try {
        $env:MES_DATABASE_URL = $DatabaseUrl
        & $VenvAlembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            Write-Fatal "Alembic migration failed (exit $LASTEXITCODE).`nFix the schema issue, then re-run without -RunMigrations."
        }
        Write-OK "Migrations applied."
    } finally {
        Pop-Location
    }
}

# ── Service helpers ──────────────────────────────────────────────────────────
function Get-ServiceStatus {
    param([string]$Name)
    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $svc) { return "not-installed" }
    return $svc.Status.ToString().ToLower()  # running | stopped | paused …
}

function Assert-Admin {
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Fatal "This action requires Administrator privileges.  Re-run as Administrator."
    }
}

# ── Main ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "MES AI Service Manager" -ForegroundColor White
Write-Host "======================" -ForegroundColor White

# ── No arguments → print usage and exit ──────────────────────────────────────
if ($Action -eq "") {
    Write-Host ""
    Write-Host "USAGE" -ForegroundColor Yellow
    Write-Host "  .\run-service.ps1 <action> [-ConfigFile <path>] [-RunMigrations]"
    Write-Host ""
    Write-Host "ACTIONS" -ForegroundColor Yellow
    Write-Host "  install    Register and configure the MES AI Windows service (requires Admin)"
    Write-Host "  uninstall  Remove the Windows service (requires Admin)"
    Write-Host "  start      Start the service (requires Admin)"
    Write-Host "  stop       Stop the service (requires Admin)"
    Write-Host "  restart    Restart the service (requires Admin)"
    Write-Host "  status     Show current service status"
    Write-Host ""
    Write-Host "OPTIONS" -ForegroundColor Yellow
    Write-Host "  -ConfigFile <path>   Path to config file (default: mes-service.conf)"
    Write-Host "  -RunMigrations       Run 'alembic upgrade head' before starting/installing"
    Write-Host ""
    Write-Host "EXAMPLES" -ForegroundColor Yellow
    Write-Host "  .\run-service.ps1 install -RunMigrations"
    Write-Host "  .\run-service.ps1 install -ConfigFile C:\mes\prod.conf -RunMigrations"
    Write-Host "  .\run-service.ps1 start"
    Write-Host "  .\run-service.ps1 status"
    Write-Host "  .\run-service.ps1 uninstall"
    Write-Host ""
    Write-Host "  See mes-service.conf.example for all available configuration keys."
    Write-Host ""
    exit 0
}

$validActions = @("install", "uninstall", "start", "stop", "restart", "status")
if ($Action.ToLower() -notin $validActions) {
    Write-Host "ERROR: Unknown action '$Action'.  Valid actions: $($validActions -join ', ')" -ForegroundColor Red
    Write-Host "Run .\run-service.ps1 with no arguments to see usage."
    exit 1
}

# ── STATUS ───────────────────────────────────────────────────────────────────
if ($Action -ieq "status") {
    $cfg  = Read-Config $ConfigFile
    $name = Get-CfgValue $cfg "ServiceName" "MesAI"
    $status = Get-ServiceStatus $name
    $colour = if ($status -eq "running") { "Green" }
              elseif ($status -eq "not-installed") { "Yellow" }
              else { "Red" }
    Write-Host "  Service  : $name"
    Write-Host "  Status   : $status" -ForegroundColor $colour
    exit 0
}

# ── STOP ─────────────────────────────────────────────────────────────────────
if ($Action -ieq "stop") {
    Assert-Admin
    $cfg    = Read-Config $ConfigFile
    $name   = Get-CfgValue $cfg "ServiceName" "MesAI"
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
    $name   = Get-CfgValue $cfg "ServiceName" "MesAI"
    $nssm   = Get-NssmPath
    $status = Get-ServiceStatus $name
    if ($status -eq "not-installed") { Write-Fatal "Service '$name' is not installed.  Run: .\run-service.ps1 install" }
    if ($status -eq "running")       { Write-Warn "Service '$name' is already running."; exit 0 }

    if ($RunMigrations) {
        $db  = Build-ConnectionString $cfg
        Invoke-Migrations $db.Url
    }

    Write-Step "Starting service '$name'..."
    & $nssm start $name
    Write-OK "Service started."
    exit 0
}

# ── RESTART ──────────────────────────────────────────────────────────────────
if ($Action -ieq "restart") {
    Assert-Admin
    $cfg  = Read-Config $ConfigFile
    $name = Get-CfgValue $cfg "ServiceName" "MesAI"
    $nssm = Get-NssmPath
    if ((Get-ServiceStatus $name) -eq "not-installed") {
        Write-Fatal "Service '$name' is not installed.  Run: .\run-service.ps1 install"
    }

    if ($RunMigrations) {
        $db  = Build-ConnectionString $cfg
        Invoke-Migrations $db.Url
    }

    Write-Step "Restarting service '$name'..."
    & $nssm restart $name
    Write-OK "Service restarted."
    exit 0
}

# ── UNINSTALL ────────────────────────────────────────────────────────────────
if ($Action -ieq "uninstall") {
    Assert-Admin
    $cfg    = Read-Config $ConfigFile
    $name   = Get-CfgValue $cfg "ServiceName" "MesAI"
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
# (Reaches here only for 'install')
Assert-Admin

$cfg = Read-Config $ConfigFile

# ── Validate required tools ──────────────────────────────────────────────────
if (-not (Test-Path $VenvPython)) {
    Write-Fatal "Python virtual environment not found at: $VenvPython`nRun .\install.ps1 first."
}
if (-not (Test-Path $ServerDir)) {
    Write-Fatal "Server directory not found: $ServerDir"
}

$nssm = Get-NssmPath

# ── Read config values ───────────────────────────────────────────────────────
$svcName    = Get-CfgValue $cfg "ServiceName"        "MesAI"
$svcDisplay = Get-CfgValue $cfg "ServiceDisplayName" "MES AI Server"
$svcDesc    = Get-CfgValue $cfg "ServiceDescription" "MES AI Manufacturing Execution System Server"
$port       = Get-CfgValue $cfg "UvicornPort"        "8082"
$workers    = Get-CfgValue $cfg "Workers"            "4"
$authMode   = Get-CfgValue $cfg "AuthMode"           "none"
$startType  = Get-CfgValue $cfg "StartType"          "auto"
$logDir     = Get-CfgValue $cfg "LogDir"             ""

# ── Build connection string ───────────────────────────────────────────────────
$db = Build-ConnectionString $cfg
$connUrl = $db.Url

# ── Log directory ─────────────────────────────────────────────────────────────
if ($logDir -eq "") { $logDir = Join-Path $ServerDir "logs" }
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

# ── Run migrations if requested ───────────────────────────────────────────────
if ($RunMigrations) {
    Invoke-Migrations $connUrl
}

# ── Summary ───────────────────────────────────────────────────────────────────
$maskedUrl = $connUrl -replace '(?<=://[^:]+:)[^@]+(?=@)', '****'
Write-Host ""
Write-Host "  Service   : $svcName"
Write-Host "  Display   : $svcDisplay"
Write-Host "  Database  : $($db.DbType)  ($maskedUrl)"
Write-Host "  Port      : $port"
Write-Host "  Workers   : $workers"
Write-Host "  Auth Mode : $authMode"
Write-Host "  Start Type: $startType"
Write-Host "  Log Dir   : $logDir"
Write-Host ""

# ── Remove existing service if present ────────────────────────────────────────
$existing = Get-ServiceStatus $svcName
if ($existing -ne "not-installed") {
    Write-Step "Existing service '$svcName' found (status: $existing) — removing before reinstall..."
    if ($existing -eq "running") { & $nssm stop $svcName confirm }
    & $nssm remove $svcName confirm
    Write-OK "Old service removed."
}

# ── Register service with NSSM ─────────────────────────────────────────────────
Write-Step "Installing service '$svcName'..."

$uvicornArgs = "mes.main:app --host 0.0.0.0 --port $port --workers $workers"

& $nssm install $svcName $VenvPython
& $nssm set     $svcName AppParameters       "-m uvicorn $uvicornArgs"
& $nssm set     $svcName AppDirectory        $ServerDir
& $nssm set     $svcName DisplayName         $svcDisplay
& $nssm set     $svcName Description         $svcDesc

# Environment variables (NSSM uses \0-delimited multi-value)
$envBlock = "MES_DATABASE_URL=$connUrl`0MES_AUTH_MODE=$authMode`0MES_LOG_FILE=mes_server_${port}.log"
& $nssm set $svcName AppEnvironmentExtra $envBlock

# Logging
& $nssm set $svcName AppStdout         (Join-Path $logDir "${svcName}-stdout.log")
& $nssm set $svcName AppStderr         (Join-Path $logDir "${svcName}-stderr.log")
& $nssm set $svcName AppRotateFiles    1
& $nssm set $svcName AppRotateOnline   1
& $nssm set $svcName AppRotateSeconds  86400   # rotate daily
& $nssm set $svcName AppRotateBytes    10485760 # cap at 10 MB per file

# Restart on failure: restart after 5 s, reset failure count after 1 h
& $nssm set $svcName AppExit          Default Restart
& $nssm set $svcName AppRestartDelay  5000
& $nssm set $svcName AppThrottle      0

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
Write-Host "  Health check : http://localhost:${port}/health"
Write-Host "  API docs     : http://localhost:${port}/api/v1/docs"
Write-Host "  Logs         : $logDir"
Write-Host ""
Write-Host "  Start now    : .\run-service.ps1 start  -ConfigFile `"$ConfigFile`""
Write-Host "  Stop         : .\run-service.ps1 stop   -ConfigFile `"$ConfigFile`""
Write-Host "  Status       : .\run-service.ps1 status -ConfigFile `"$ConfigFile`""
Write-Host "  Uninstall    : .\run-service.ps1 uninstall -ConfigFile `"$ConfigFile`""
Write-Host ""
