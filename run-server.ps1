<#
.SYNOPSIS
    Start the MES AI server with a specified database backend.

.DESCRIPTION
    Sets the DATABASE_URL environment variable, activates the Python virtual
    environment, runs Alembic migrations to the latest revision, then starts
    the uvicorn web server.

.PARAMETER Database
    Required. Database engine: PostgreSQL | MSSQL | Oracle

.PARAMETER DbName
    Optional. Name of the MES database. Default: mes_ai

.PARAMETER DbServer
    Optional. Database host and port as "host:port" or just "host".
    Defaults to localhost with the database engine's standard port.

.PARAMETER Username
    Optional. Database username. Defaults to "postgres" for PostgreSQL.
    Required for MySQL, MSSQL, Oracle, CockroachDB, DB2.

.PARAMETER Password
    Optional. Database password. Defaults to "postgres" for PostgreSQL.

.PARAMETER UvicornPort
    Optional. Port for the uvicorn web server. Default: 8082

.PARAMETER Help
    Show usage information, supported databases, and example connection strings.

.EXAMPLE
    .\run-server.ps1 PostgreSQL
    .\run-server.ps1 PostgreSQL -DbName prod_mes -Username postgres -Password secret
    .\run-server.ps1 MSSQL mes_ai -Username sa -Password MyPass123
    .\run-server.ps1 Oracle mes_ai -DbServer oracle-host:1521 -Username mes -Password oracle
    .\run-server.ps1 -Help
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Database,

    [Parameter(Position = 1)]
    [string]$DbName = "mes_ai",

    [Parameter()]
    [string]$DbServer = "",

    [Parameter()]
    [string]$Username = "",

    [Parameter()]
    [string]$Password = "",

    [Parameter()]
    [int]$UvicornPort = 8082,

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
  .\run-server.ps1 <Database> [DbName] [options]

ARGUMENTS
  Database             (required)  Database engine (case-insensitive):
                                     PostgreSQL | MSSQL | Oracle
  DbName               (optional)  MES database name.  Default: mes_ai

OPTIONS
  -DbServer  HOST[:PORT]  DB host and optional port.
                          Default: localhost with the engine's standard port.
  -Username  USER         DB username.  Defaults to "postgres" for PostgreSQL.
                          Required for MSSQL and Oracle.
  -Password  PASS         DB password.  Defaults to "postgres" for PostgreSQL.
  -UvicornPort  PORT      uvicorn port.  Default: 8082
  -Help                   Show this help message.

SUPPORTED DATABASES
  Engine        Default Port  Async Driver  Example Connection String
  ----------    ------------  ------------  ------------------------------------------------
  PostgreSQL        5432      asyncpg       postgresql+asyncpg://user:pass@host:5432/mes_ai
  MSSQL             1433      pyodbc        mssql+pyodbc://user:pass@host:1433/mes_ai?driver=ODBC+Driver+18+for+SQL+Server
  Oracle            1521      oracledb      oracle+oracledb://user:pass@host:1521/mes_ai

EXAMPLES
  .\run-server.ps1 PostgreSQL
  .\run-server.ps1 PostgreSQL mes_ai -Username postgres -Password secret
  .\run-server.ps1 MSSQL mes_ai -Username sa -Password MyPass123 -UvicornPort 8090
  .\run-server.ps1 Oracle mes_ai -DbServer oracle-host:1521 -Username mes -Password oracle

"@
}

if ($Help -or [string]::IsNullOrEmpty($Database)) {
    Show-Help
    exit 0
}

# ---------------------------------------------------------------------------
# Default ports per engine
# ---------------------------------------------------------------------------
$defaultPorts = @{
    postgresql = 5432
    mssql      = 1433
    oracle     = 1521
}

$dbType = $Database.ToLower()

if (-not $defaultPorts.ContainsKey($dbType)) {
    Write-Error "Unknown database '$Database'.`nValid options: PostgreSQL, MSSQL, Oracle"
    exit 1
}

# ---------------------------------------------------------------------------
# Resolve host and port
# ---------------------------------------------------------------------------
$dbHost = "localhost"
$dbPort = $defaultPorts[$dbType]

if ($DbServer -ne "") {
    if ($DbServer -match '^(.+):(\d+)$') {
        $dbHost = $Matches[1]
        $dbPort = [int]$Matches[2]
    } else {
        $dbHost = $DbServer
    }
}

# ---------------------------------------------------------------------------
# Credential defaults / validation
# ---------------------------------------------------------------------------
if ($Username -eq "") {
    if ($dbType -eq "postgresql") {
        $Username = "postgres"
        if ($Password -eq "") { $Password = "postgres" }
        Write-Host "INFO: No credentials supplied — using PostgreSQL defaults (postgres/postgres)."
    } else {
        Write-Error "-Username is required for $Database."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# MSSQL: verify ODBC driver is installed
# ---------------------------------------------------------------------------
if ($dbType -eq "mssql") {
    $odbcDrivers = Get-ItemProperty "HKLM:\SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers" -ErrorAction SilentlyContinue
    $driver18    = $odbcDrivers."ODBC Driver 18 for SQL Server"
    $driver17    = $odbcDrivers."ODBC Driver 17 for SQL Server"

    if ($driver18 -eq "Installed") {
        Write-Host "INFO: ODBC Driver 18 for SQL Server detected."
        $odbcDriverName = "ODBC+Driver+18+for+SQL+Server"
    } elseif ($driver17 -eq "Installed") {
        Write-Host "INFO: ODBC Driver 17 for SQL Server detected (18 preferred)."
        $odbcDriverName = "ODBC+Driver+17+for+SQL+Server"
    } else {
        Write-Error @"
ODBC Driver for SQL Server not found.
Install 'ODBC Driver 18 for SQL Server' from:
  https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
"@
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Build connection string
# ---------------------------------------------------------------------------
$connStr = switch ($dbType) {
    "postgresql" { "postgresql+asyncpg://${Username}:${Password}@${dbHost}:${dbPort}/${DbName}" }
    "mssql"      { "mssql+pyodbc://${Username}:${Password}@${dbHost}:${dbPort}/${DbName}?driver=${odbcDriverName}" }
    "oracle"     { "oracle+oracledb://${Username}:${Password}@${dbHost}:${dbPort}/${DbName}" }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "MES AI Server Startup"
Write-Host "====================="
Write-Host "  Database  : $Database"
Write-Host "  DB Name   : $DbName"
Write-Host "  DB Server : ${dbHost}:${dbPort}"
Write-Host "  Username  : $Username"
Write-Host "  URL       : $connStr"
Write-Host "  API Port  : $UvicornPort"
Write-Host ""

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
$scriptRoot    = $PSScriptRoot
$venvActivate  = Join-Path $scriptRoot ".venv\Scripts\Activate.ps1"
$serverDir     = Join-Path $scriptRoot "server"

if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtual environment not found at: $venvActivate`nCreate it with:  python -m venv .venv`n                 pip install -e server/[dev]"
    exit 1
}
if (-not (Test-Path $serverDir)) {
    Write-Error "Server directory not found: $serverDir"
    exit 1
}

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
$env:MES_DATABASE_URL = $connStr
if (-not $env:MES_AUTH_MODE) { $env:MES_AUTH_MODE = "none" }

# ---------------------------------------------------------------------------
# Activate virtual environment
# ---------------------------------------------------------------------------
Write-Host "Activating virtual environment..."
& $venvActivate

# ---------------------------------------------------------------------------
# Alembic migrations
# ---------------------------------------------------------------------------
Write-Host "Running Alembic migrations..."
Push-Location $serverDir
try {
    alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Alembic migration failed (exit code $LASTEXITCODE)."
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

# ---------------------------------------------------------------------------
# Uvicorn
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Starting MES server..."
Write-Host "  Health  : http://localhost:${UvicornPort}/health"
Write-Host "  API     : http://localhost:${UvicornPort}/api/v1/docs"
Write-Host ""
Write-Host "Press Ctrl+C to stop."
Write-Host ""

Push-Location $serverDir
try {
    uvicorn mes.main:app --reload --host 0.0.0.0 --port $UvicornPort
} finally {
    Pop-Location
}
