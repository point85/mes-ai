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
    Optional. Database password as a SecureString. Defaults to "postgres" for PostgreSQL.
    Pass with: -Password (ConvertTo-SecureString 'pass' -AsPlainText -Force)
    Or prompt:  -Password (Read-Host -AsSecureString 'DB Password')

.PARAMETER UvicornPort
    Optional. Port for the uvicorn web server. Default: 8082

.PARAMETER Stamp
    Purge the alembic_version table and re-stamp to the current head before
    running migrations.  Use this when an existing database has a stale
    revision (e.g. after a migration consolidation).

.PARAMETER Help
    Show usage information, supported databases, and example connection strings.

.EXAMPLE
    .\run-server.ps1 PostgreSQL
    .\.run-server.ps1 PostgreSQL -DbName prod_mes -Username postgres -Password (ConvertTo-SecureString 'secret' -AsPlainText -Force)
    .\.run-server.ps1 MSSQL mes_ai -Username sa -Password (Read-Host -AsSecureString 'DB Password')
    .\.run-server.ps1 Oracle mes_ai -DbServer oracle-host:1521 -Username mes -Password (Read-Host -AsSecureString 'DB Password')
    .\run-server.ps1 -Help
#>

[CmdletBinding()]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingPlainTextForPassword', 'Password',
    Justification = 'Parameter is typed as [SecureString]; plain text is never stored or logged.')]
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
    [SecureString]$Password = (New-Object SecureString),

    [Parameter()]
    [int]$UvicornPort = 8082,

    [Parameter()]
    [switch]$Stamp,

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
  -Stamp                  Purge stale Alembic revision and re-stamp to head
                          before running migrations (use after consolidation).
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
        if ($Password.Length -eq 0) { $Password = ConvertTo-SecureString "postgres" -AsPlainText -Force }
        Write-Host "INFO: No credentials supplied - using PostgreSQL defaults (postgres/postgres)."
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
        Write-Host "INFO: ODBC Driver 17 for SQL Server detected. Driver 18 is preferred."
        $odbcDriverName = "ODBC+Driver+17+for+SQL+Server"
    } else {
        Write-Host "Error: ODBC Driver for SQL Server not found." -ForegroundColor Red
        Write-Host "Install 'ODBC Driver 18 for SQL Server' from:" -ForegroundColor Red
        Write-Host "  https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server" -ForegroundColor Red
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Build connection string
# ---------------------------------------------------------------------------
# Decrypt SecureString to plain text only at the moment the URL is assembled.
# The plain-text variable is local and never written to output or logs.
$bstr        = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
$plainPwd    = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

$connStr = switch ($dbType) {
    "postgresql" { "postgresql+asyncpg://${Username}:${plainPwd}@${dbHost}:${dbPort}/${DbName}" }
    "mssql"      { "mssql+pyodbc://${Username}:${plainPwd}@${dbHost}:${dbPort}/${DbName}?driver=${odbcDriverName}" }
    "oracle"     { "oracle+oracledb://${Username}:${plainPwd}@${dbHost}:${dbPort}/${DbName}" }
}
Remove-Variable plainPwd

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
$maskedUrl = $connStr -replace '(?<=://[^:]+:)[^@]+(?=@)', '****'
Write-Host "  URL       : $maskedUrl"
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
# Check database exists (PostgreSQL / MSSQL; Oracle uses service names)
# ---------------------------------------------------------------------------
Write-Host "Checking database '$DbName' exists on ${dbHost}:${dbPort}..."
if ($dbType -eq "postgresql") {
    if (Get-Command psql -ErrorAction SilentlyContinue) {
        $bstrChk         = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $env:PGPASSWORD  = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstrChk)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstrChk)
        $dbExists        = & psql -U $Username -h $dbHost -p $dbPort -tAc "SELECT 1 FROM pg_database WHERE datname='$DbName'" postgres 2>&1
        $env:PGPASSWORD  = ""
        if (($dbExists -join "").Trim() -ne "1") {
            Write-Error "Database '$DbName' does not exist on ${dbHost}:${dbPort}.`nCreate it first:`n  psql -U $Username -h $dbHost -p $dbPort -c `"CREATE DATABASE `\`"$DbName`\`";`""
            exit 1
        }
    } else {
        Write-Host "  WARNING: psql not found - skipping database existence check." -ForegroundColor Yellow
    }
} elseif ($dbType -eq "mssql") {
    if (Get-Command sqlcmd -ErrorAction SilentlyContinue) {
        $bstrChk = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
        $tmpPwd  = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstrChk)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstrChk)
        $result  = & sqlcmd -S "${dbHost},${dbPort}" -U $Username -P $tmpPwd -Q "SET NOCOUNT ON; IF DB_ID('$DbName') IS NULL PRINT 'MISSING'" -h -1 2>&1
        Remove-Variable tmpPwd
        if ($result -match "MISSING") {
            Write-Error "Database '$DbName' does not exist on ${dbHost}:${dbPort}.`nCreate it first:`n  sqlcmd -S ${dbHost},${dbPort} -U $Username -Q `"CREATE DATABASE [$DbName]`""
            exit 1
        }
    } else {
        Write-Host "  WARNING: sqlcmd not found - skipping database existence check." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Alembic migrations
# ---------------------------------------------------------------------------
Write-Host "Running Alembic migrations..."

# Auto-detect empty database: if alembic_version does not exist, stamp first
# so upgrade head runs from a clean baseline rather than failing on a missing revision.
if (-not $Stamp -and $dbType -eq "postgresql" -and (Get-Command psql -ErrorAction SilentlyContinue)) {
    $bstrChk        = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstrChk)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstrChk)
    $avExists = & psql -U $Username -h $dbHost -p $dbPort -d $DbName -tAc `
        "SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version'" 2>&1
    $env:PGPASSWORD = ""
    if (($avExists -join "").Trim() -ne "1") {
        Write-Host "  Empty database detected - stamping to current head before upgrade."
        $Stamp = $true
    }
}

Push-Location $serverDir
try {
    if ($Stamp) {
        Write-Host "  Stamping database to current head (purging stale revision)..."
        alembic stamp head --purge
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Alembic stamp failed (exit code $LASTEXITCODE)."
            exit $LASTEXITCODE
        }
    }
    alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Alembic migration failed (exit code $LASTEXITCODE).`nIf the database has a stale revision from a prior migration consolidation, re-run with -Stamp to reset it."
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
