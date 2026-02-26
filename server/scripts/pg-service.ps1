<#
.SYNOPSIS
    Manage PostgreSQL 16 as a Windows service for MES AI development.

.DESCRIPTION
    Installs, starts, stops, or uninstalls PostgreSQL 16 as a Windows service.
    Expects PostgreSQL binaries to be on PATH or at the default install location.

.PARAMETER Action
    install   — Initialise the data directory and register the Windows service.
    start     — Start the PostgreSQL service.
    stop      — Stop the PostgreSQL service.
    restart   — Stop then start the service.
    status    — Show current service state.
    uninstall — Stop the service and remove it from Windows.

.EXAMPLE
    .\pg-service.ps1 install
    .\pg-service.ps1 start
    .\pg-service.ps1 stop
    .\pg-service.ps1 uninstall
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("install", "start", "stop", "restart", "status", "uninstall")]
    [string]$Action
)

# ── Configuration ────────────────────────────────────────────────
$ServiceName = "postgresql-mes"
$PgPort = 5432
$PgUser = "postgres"
$PgPassword = "postgres"
$PgDatabase = "mes_ai"
$DataDir = Join-Path $PSScriptRoot "..\pgdata"
$DataDir = [System.IO.Path]::GetFullPath($DataDir)

# ── Locate PostgreSQL binaries ───────────────────────────────────

function Find-PgBin {
    # 1. Check PATH
    $initdb = Get-Command initdb -ErrorAction SilentlyContinue
    if ($initdb) { return Split-Path $initdb.Source }

    # 2. Check common install locations
    $candidates = @(
        "C:\Program Files\PostgreSQL\16\bin",
        "C:\Program Files\PostgreSQL\17\bin",
        "C:\Program Files\PostgreSQL\15\bin",
        "C:\pgsql\bin"
    )
    foreach ($dir in $candidates) {
        if (Test-Path (Join-Path $dir "initdb.exe")) { return $dir }
    }

    Write-Error @"
PostgreSQL binaries not found.
Install PostgreSQL 16 from https://www.postgresql.org/download/windows/
or add the bin\ directory to your PATH.
"@
    exit 1
}

$PgBin = Find-PgBin
$pg_ctl   = Join-Path $PgBin "pg_ctl.exe"
$initdb   = Join-Path $PgBin "initdb.exe"
$psqlExe  = Join-Path $PgBin "psql.exe"

Write-Host "PostgreSQL binaries : $PgBin" -ForegroundColor DarkGray
Write-Host "Data directory      : $DataDir" -ForegroundColor DarkGray
Write-Host ""

# ── Require elevation ────────────────────────────────────────────

function Assert-Admin {
    $current = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $current.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Error "This action requires an elevated (Administrator) PowerShell prompt."
        exit 1
    }
}

# ── Actions ──────────────────────────────────────────────────────

function Invoke-PgInstall {
    Assert-Admin

    # 1. Initialise data directory
    if (-not (Test-Path (Join-Path $DataDir "PG_VERSION"))) {
        Write-Host "--- Initialising data directory ---" -ForegroundColor Cyan

        # Write password to a temp file for initdb --pwfile
        $pwFile = Join-Path $env:TEMP "pg_pw_$PID.txt"
        Set-Content -Path $pwFile -Value $PgPassword -NoNewline
        & $initdb -D $DataDir -U $PgUser -A md5 --pwfile=$pwFile --encoding=UTF8
        $initResult = $LASTEXITCODE
        Remove-Item $pwFile -ErrorAction SilentlyContinue
        if ($initResult -ne 0) {
            Write-Error "initdb failed (exit code $initResult)."
            exit 1
        }
        Write-Host "[OK] Data directory initialised." -ForegroundColor Green

        # Set port in postgresql.conf
        $confFile = Join-Path $DataDir "postgresql.conf"
        (Get-Content $confFile) -replace "^#?port\s*=.*", "port = $PgPort" |
            Set-Content $confFile
        Write-Host "[OK] Port set to $PgPort in postgresql.conf." -ForegroundColor Green
    }
    else {
        Write-Host "[OK] Data directory already exists — skipping initdb." -ForegroundColor Yellow
    }

    # 2. Register Windows service
    $existingSvc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingSvc) {
        Write-Host "[OK] Service '$ServiceName' is already registered." -ForegroundColor Yellow
    }
    else {
        Write-Host "--- Registering Windows service ---" -ForegroundColor Cyan
        & $pg_ctl register -N $ServiceName -D $DataDir -S demand -o "-p $PgPort"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to register service (exit code $LASTEXITCODE)."
            exit 1
        }
        Write-Host "[OK] Service '$ServiceName' registered (manual start)." -ForegroundColor Green
    }

    # 3. Start the service
    Invoke-PgStart

    # 4. Create the mes_ai database if it doesn't exist
    Write-Host "--- Ensuring database '$PgDatabase' exists ---" -ForegroundColor Cyan
    Start-Sleep -Seconds 2  # Give the service a moment to accept connections
    $env:PGPASSWORD = $PgPassword
    $dbExists = & $psqlExe -h localhost -p $PgPort -U $PgUser -tAc "SELECT 1 FROM pg_database WHERE datname='$PgDatabase'" 2>$null
    if ($dbExists -ne "1") {
        & $psqlExe -h localhost -p $PgPort -U $PgUser -c "CREATE DATABASE $PgDatabase" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Database '$PgDatabase' created." -ForegroundColor Green
        }
        else {
            Write-Warning "Could not create database '$PgDatabase'. You may need to create it manually."
        }
    }
    else {
        Write-Host "[OK] Database '$PgDatabase' already exists." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "=== PostgreSQL installation complete ===" -ForegroundColor Green
    Write-Host "  Connection: postgresql://postgres:postgres@localhost:$PgPort/$PgDatabase"
    Write-Host ""
}

function Invoke-PgStart {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Error "Service '$ServiceName' not found. Run '.\pg-service.ps1 install' first."
        exit 1
    }
    if ($svc.Status -eq "Running") {
        Write-Host "[OK] Service '$ServiceName' is already running." -ForegroundColor Yellow
        return
    }
    Write-Host "Starting service '$ServiceName'..." -ForegroundColor Cyan
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 2
    $svc = Get-Service -Name $ServiceName
    if ($svc.Status -eq "Running") {
        Write-Host "[OK] PostgreSQL is running on port $PgPort." -ForegroundColor Green
    }
    else {
        Write-Error "Service failed to start. Check the Windows Event Log for details."
        exit 1
    }
}

function Invoke-PgStop {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Host "Service '$ServiceName' not found — nothing to stop." -ForegroundColor Yellow
        return
    }
    if ($svc.Status -eq "Stopped") {
        Write-Host "[OK] Service '$ServiceName' is already stopped." -ForegroundColor Yellow
        return
    }
    Write-Host "Stopping service '$ServiceName'..." -ForegroundColor Cyan
    Stop-Service -Name $ServiceName -Force
    Write-Host "[OK] PostgreSQL stopped." -ForegroundColor Green
}

function Invoke-PgRestart {
    Invoke-PgStop
    Start-Sleep -Seconds 1
    Invoke-PgStart
}

function Get-PgStatus {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Host "Service '$ServiceName' is not installed." -ForegroundColor Yellow
        return
    }
    $color = if ($svc.Status -eq "Running") { "Green" } else { "Red" }
    Write-Host "Service : $ServiceName" -ForegroundColor $color
    Write-Host "Status  : $($svc.Status)" -ForegroundColor $color
    Write-Host "Startup : $($svc.StartType)"
    Write-Host "Data dir: $DataDir"
    Write-Host "Port    : $PgPort"

    # Quick connectivity test
    if ($svc.Status -eq "Running") {
        $env:PGPASSWORD = $PgPassword
        $result = & $psqlExe -h localhost -p $PgPort -U $PgUser -tAc "SELECT version()" 2>$null
        if ($result) {
            Write-Host "Version : $($result.Trim())" -ForegroundColor DarkGray
        }
    }
}

function Uninstall-Pg {
    Assert-Admin

    # Stop first
    Invoke-PgStop

    # Unregister service
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "--- Removing Windows service ---" -ForegroundColor Cyan
        & $pg_ctl unregister -N $ServiceName
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Service '$ServiceName' removed." -ForegroundColor Green
        }
        else {
            Write-Warning "pg_ctl unregister returned exit code $LASTEXITCODE."
        }
    }
    else {
        Write-Host "Service '$ServiceName' not found — nothing to remove." -ForegroundColor Yellow
    }

    # Ask before deleting data
    if (Test-Path $DataDir) {
        Write-Host ""
        $confirm = Read-Host "Delete data directory '$DataDir'? This destroys all data. [y/N]"
        if ($confirm -eq "y") {
            Remove-Item -Recurse -Force $DataDir
            Write-Host "[OK] Data directory deleted." -ForegroundColor Green
        }
        else {
            Write-Host "Data directory preserved at: $DataDir" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "=== PostgreSQL uninstalled ===" -ForegroundColor Green
}

# ── Dispatch ─────────────────────────────────────────────────────

switch ($Action) {
    "install"   { Invoke-PgInstall }
    "start"     { Invoke-PgStart }
    "stop"      { Invoke-PgStop }
    "restart"   { Invoke-PgRestart }
    "status"    { Get-PgStatus }
    "uninstall" { Uninstall-Pg }
}
