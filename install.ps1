<#
.SYNOPSIS
    Install and configure the MES AI application.

.DESCRIPTION
    One-shot setup for MES AI.  Checks for Python 3.12+ and Node.js 20+,
    creates a Python virtual environment, installs all server and client
    dependencies, writes the server database configuration, creates the
    application database when supported, and runs Alembic schema migrations.

    If you are using PostgreSQL and it is not yet installed, run
    install-postgresql.ps1 first.

    Safe to run more than once - each step checks whether work is already done.

.PARAMETER DbProvider
    Required. Database provider: PostgreSQL, MSSQL, or Oracle.

.PARAMETER DbName
    Application database name.  Default: mes_ai

.PARAMETER DatabaseUrl
    Full SQLAlchemy database URL.  When supplied, it is used as-is and the
    installer skips automatic database creation.

.PARAMETER DbServer
    Database host, or host:port.  Default: localhost with the selected
    provider's standard port.

.PARAMETER DbUser
    Database username.  Default: postgres for PostgreSQL.

.PARAMETER DbPassword
    Database password.  Default: postgres for PostgreSQL.
    NOTE: for development installations only.  Use a strong password for
    any environment reachable from a network.

.PARAMETER SkipClients
    Skip npm install for the four browser client applications.

.PARAMETER SkipMigrations
    Skip Alembic migrations.  Use when the schema is already at the correct
    revision (e.g. running the installer a second time without schema changes).

.PARAMETER Help
    Show this help message and exit.

.EXAMPLE
    .\install.ps1 -DbProvider PostgreSQL

.EXAMPLE
    .\install-postgresql.ps1
    .\install.ps1 -DbProvider PostgreSQL -DbPassword secret

.EXAMPLE
    .\install.ps1 -DbProvider MSSQL -DbServer sql-host:1433 -DbUser sa -DbPassword secret
#>

[CmdletBinding(PositionalBinding = $false)]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingPlainTextForPassword', 'DbPassword',
    Justification = 'Development installer only; never stored beyond this process.')]
param(
    [ValidateSet("PostgreSQL", "MSSQL", "Oracle")]
    [string]$DbProvider,

    [string]$DbName     = "mes_ai",

    [string]$DatabaseUrl = "",

    [string]$DbServer   = "localhost",

    [string]$DbUser     = "postgres",

    [string]$DbPassword = "postgres",

    [switch]$SkipClients,

    [switch]$SkipMigrations,

    [switch]$Help,

    [Parameter(ValueFromRemainingArguments = $true)]
    $UnknownArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerDir  = Join-Path $ScriptDir "server"
$VenvDir    = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir   "Scripts\python.exe"
$VenvPip    = Join-Path $VenvDir   "Scripts\pip.exe"

# --- Help -------------------------------------------------------------------
function Show-Help {
    Write-Host @'

USAGE
  .\install.ps1 [options]

OPTIONS
    -DbProvider   PROVIDER      Required: PostgreSQL | MSSQL | Oracle
    -DbName       NAME          Database name.              Default: mes_ai
    -DatabaseUrl  URL           Full SQLAlchemy URL.        Skips DB auto-create.
    -DbServer     HOST[:PORT]   Database host/port.         Default: localhost
    -DbUser       USER          Database username.          Default: postgres for PostgreSQL
    -DbPassword   PASS          Database password.          Default: postgres for PostgreSQL
  -SkipClients                Skip npm install for browser clients.
  -SkipMigrations             Skip Alembic schema migrations.
  -Help                       Show this message.

STEPS PERFORMED
  1. Verify Python 3.12+ (install via winget if missing)
  2. Verify Node.js 20+  (install via winget if missing, unless -SkipClients)
  3. Create Python virtual environment      (.venv/)
  4. Install Python server dependencies     (pip install -e ".[<driver>,dev]")
  5. Create server/.env configuration file  (skipped if already present)
    6. Prepare database                       (auto-create for PostgreSQL only)
  7. Run Alembic schema migrations          (skipped with -SkipMigrations)
  8. Install npm dependencies               (clients/*, skipped with -SkipClients)

    To install PostgreSQL first:  .\install-postgresql.ps1

EXAMPLES
    .\install.ps1 -DbProvider PostgreSQL
    .\install.ps1 -DbProvider PostgreSQL -DbName my_mes -DbPassword secret
    .\install.ps1 -DbProvider MSSQL -DbServer sql-host:1433 -DbUser sa -DbPassword secret
    .\install.ps1 -DbProvider Oracle -DatabaseUrl oracle+oracledb://mes:secret@oracle-host:1521/mes_ai

'@
}

if ($UnknownArgs -and @($UnknownArgs).Count -eq 1 -and @('--help', '-h') -contains $UnknownArgs[0]) {
    Show-Help
    exit 0
}

if ($UnknownArgs) {
    Write-Host "Unknown option(s): $($UnknownArgs -join ' ')"
    Show-Help
    exit 1
}

if ($Help) { Show-Help; exit 0 }

if (-not $DbProvider) {
    Write-Host "Error: -DbProvider is required. Choose PostgreSQL, MSSQL, or Oracle."
    Show-Help
    exit 1
}

# --- Output helpers ---------------------------------------------------------
function Write-Step([string]$msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}
function Write-Ok([string]$msg) {
    Write-Host "    OK   $msg" -ForegroundColor Green
}
function Write-Warn([string]$msg) {
    Write-Host "    WARN $msg" -ForegroundColor Yellow
}
function Fail([string]$msg) {
    Write-Host "`nERROR: $msg" -ForegroundColor Red
    exit 1
}

function Test-MssqlOdbcDriver {
    $odbcDrivers = Get-ItemProperty "HKLM:\SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers" -ErrorAction SilentlyContinue
    if ($null -eq $odbcDrivers) {
        Fail ("ODBC Driver registry entries were not found.`n" +
              "Install 'ODBC Driver 18 for SQL Server' before running migrations:`n" +
              "https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
    }

    $driver18Prop = $odbcDrivers.PSObject.Properties["ODBC Driver 18 for SQL Server"]
    $driver17Prop = $odbcDrivers.PSObject.Properties["ODBC Driver 17 for SQL Server"]
    $driver18 = if ($null -ne $driver18Prop) { $driver18Prop.Value } else { $null }
    $driver17 = if ($null -ne $driver17Prop) { $driver17Prop.Value } else { $null }

    if ($driver18 -eq "Installed") {
        Write-Ok "ODBC Driver 18 for SQL Server detected."
    } elseif ($driver17 -eq "Installed") {
        Write-Warn "ODBC Driver 17 for SQL Server detected. Driver 18 is preferred."
    } else {
        Fail ("ODBC Driver for SQL Server not found.`n" +
              "Install 'ODBC Driver 18 for SQL Server' before running migrations:`n" +
              "https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
    }
}

function Test-OracleClientAvailability {
    $oracleCheck = @'
import json, os, sys

try:
    import oracledb
except Exception as exc:
    print(json.dumps({"status": "import_error", "error": str(exc)}))
    sys.exit(0)

client_hints = []
for env_name in ("PATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
    for part in os.environ.get(env_name, "").split(os.pathsep):
        if part and any(token in part.lower() for token in ("oracle", "instantclient")):
            client_hints.append(part)

client_hints = sorted(set(client_hints))

print(json.dumps({
    "status": "ok",
    "version": getattr(oracledb, "__version__", "unknown"),
    "thin_mode": bool(oracledb.is_thin_mode()),
    "client_hints": client_hints,
}))
'@ | & $VenvPython - 2>&1

    if (-not $oracleCheck) {
        Fail "Oracle driver check returned no output. Verify the .venv was created correctly."
    }

    $oracleInfo = $oracleCheck | ConvertFrom-Json
    if ($oracleInfo.status -ne "ok") {
        Fail ("Python 'oracledb' driver is not available in the virtual environment.`n" +
              "Reinstall Python dependencies or inspect the install output.`n" +
              "Details: $($oracleInfo.error)")
    }

    Write-Ok "Oracle Python driver detected: version $($oracleInfo.version)."
    if ($oracleInfo.client_hints.Count -gt 0) {
        Write-Ok "Oracle client libraries appear to be available."
    } elseif ($oracleInfo.thin_mode) {
        Write-Warn "Oracle client libraries were not detected on PATH/LD_LIBRARY_PATH. oracledb thin mode will be used."
    } else {
        Fail ("Oracle client libraries were not detected and thin mode is unavailable.`n" +
              "Install Oracle Instant Client or configure the Oracle client library path before running migrations.")
    }
}

# --- Resolve host / port ----------------------------------------------------
$dbType = $DbProvider.ToLowerInvariant()
$dbHost = "localhost"

$dbPort = switch ($dbType) {
    "postgresql" { 5432 }
    "mssql"      { 1433 }
    "oracle"     { 1521 }
}

if ($DbServer -ne "") {
    if ($DbServer -match '^(.+):(\d+)$') {
        $dbHost = $Matches[1]
        $dbPort = [int]$Matches[2]
    } else {
        $dbHost = $DbServer
    }
}

$dbUrl = if ($DatabaseUrl -ne "") {
    $DatabaseUrl
} else {
    switch ($dbType) {
        "postgresql" { "postgresql+asyncpg://${DbUser}:${DbPassword}@${dbHost}:${dbPort}/${DbName}" }
        "mssql"      { "mssql+pyodbc://${DbUser}:${DbPassword}@${dbHost}:${dbPort}/${DbName}?driver=ODBC+Driver+18+for+SQL+Server" }
        "oracle"     { "oracle+oracledb://${DbUser}:${DbPassword}@${dbHost}:${dbPort}/${DbName}" }
    }
}

# --- Step 1: Python 3.12+ ---------------------------------------------------
Write-Step "Step 1/8 - Checking Python 3.12+"

$pythonCmd = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $verOutput = & $cmd --version 2>&1
        if ($verOutput -match 'Python (\d+)\.(\d+)') {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -eq 3 -and $minor -ge 12) {
                $pythonCmd = $cmd
                break
            }
        }
    } catch { }
}

if ($null -eq $pythonCmd) {
    Write-Warn "Python 3.12+ not found. Attempting install via winget..."

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail ("Python 3.12+ is required but winget is not available.`n" +
              "Install Python 3.12+ from https://www.python.org/downloads/ then rerun.")
    }

    winget install --id Python.Python.3.12 --source winget `
        --accept-source-agreements --accept-package-agreements

    # Refresh PATH so the new Python is visible
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")

    foreach ($cmd in @("python", "python3")) {
        try {
            $verOutput = & $cmd --version 2>&1
            if ($verOutput -match 'Python 3\.1[2-9]') {
                $pythonCmd = $cmd; break
            }
        } catch { }
    }

    if ($null -eq $pythonCmd) {
        Fail ("Python 3.12+ installation succeeded but the executable was not found on PATH.`n" +
              "Close and reopen this terminal, then rerun install.ps1.")
    }

    Write-Ok "Python installed: $((& $pythonCmd --version 2>&1))"
} else {
    Write-Ok "Found: $((& $pythonCmd --version 2>&1))"
}

# --- Step 2: Node.js 20+ ----------------------------------------------------
if (-not $SkipClients) {
    Write-Step "Step 2/8 - Checking Node.js 20+"

    $nodeOk = $false
    try {
        $nodeVer = (& node --version 2>&1).ToString()
        if ($nodeVer -match 'v(\d+)' -and [int]$Matches[1] -ge 20) {
            $nodeOk = $true
        }
    } catch { }

    if (-not $nodeOk) {
        Write-Warn "Node.js 20+ not found. Attempting install via winget..."

        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            Fail ("Node.js 20+ is required for the browser clients but winget is not available.`n" +
                  "Install Node.js 20 LTS from https://nodejs.org, or rerun with -SkipClients.")
        }

        winget install --id OpenJS.NodeJS.LTS --source winget `
            --accept-source-agreements --accept-package-agreements

        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path", "User")

        try { $nodeVer = (& node --version 2>&1).ToString() } catch { }
        if ($nodeVer -notmatch 'v(\d+)' -or [int]$Matches[1] -lt 20) {
            Fail ("Node.js installation succeeded but 'node' was not found on PATH.`n" +
                  "Close and reopen this terminal, then rerun install.ps1.")
        }

        Write-Ok "Node.js installed: $nodeVer"
    } else {
        Write-Ok "Found: $nodeVer"
    }
} else {
    Write-Host "    --   Step 2 skipped (-SkipClients)"
}

# --- Step 3: Python virtual environment ------------------------------------
Write-Step "Step 3/8 - Python virtual environment (.venv)"

if (Test-Path $VenvDir) {
    Write-Ok "Virtual environment already exists at .venv/"
} else {
    & $pythonCmd -m venv $VenvDir
    Write-Ok "Created .venv/"
}

# --- Step 4: Python dependencies --------------------------------------------
Write-Step "Step 4/8 - Installing Python server dependencies"

# Determine the database driver extra that matches the chosen provider.
$dbDriverExtra = switch ($dbType) {
    "postgresql" { "postgres" }
    "mssql"      { "mssql"   }
    "oracle"     { "oracle"  }
    default      { "postgres" }
}

Push-Location $ServerDir
try {
    & $VenvPip install --upgrade pip --quiet
    & $VenvPip install -e ".[${dbDriverExtra},dev]" --quiet
    Write-Ok "Python packages installed (mes-ai + $dbDriverExtra driver + dev extras)."
} finally {
    Pop-Location
}

# --- Step 5: server/.env ----------------------------------------------------
Write-Step "Step 5/8 - Creating server/.env configuration"

$envFile = Join-Path $ServerDir ".env"

if (Test-Path $envFile) {
    Write-Ok "server/.env already exists - skipping. Edit it to change settings."
} else {
    # Generate a cryptographically random 32-byte secret key
    $keyBytes  = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
    $secretKey = [Convert]::ToBase64String($keyBytes)

    $envContent = @"
# MES AI server configuration - generated by install.ps1
# Edit this file to adjust settings before starting the server.

# -- Database ---------------------------------------------------------------
MES_DATABASE_URL=${dbUrl}

# -- Authentication ---------------------------------------------------------
# none  = no authentication (development / evaluation)
# local = built-in username/password authentication
# oidc  = external OpenID Connect identity provider
MES_AUTH_MODE=none

# WARNING: replace with a strong random value before any production use.
MES_SECRET_KEY=${secretKey}

# -- Logging ----------------------------------------------------------------
# DEBUG | INFO | WARNING | ERROR | CRITICAL
MES_LOG_LEVEL=WARNING

# -- Event bus --------------------------------------------------------------
# memory = in-process (single server)
# redis  = distributed (requires Redis, set MES_REDIS_URL)
MES_EVENT_BUS_TYPE=memory
"@

    Set-Content -Path $envFile -Value $envContent -Encoding UTF8
    Write-Ok "Created server/.env"
}

# --- Step 6: Create database -----------------------------------------------
if ($DatabaseUrl -ne "") {
    Write-Host "    --   Step 6 skipped (-DatabaseUrl supplied; ensure the database already exists)"
} elseif ($dbType -ne "postgresql") {
    Write-Host "    --   Step 6 skipped (-DbProvider $DbProvider requires manual database creation)"
    Write-Warn "Automatic database creation is only implemented for PostgreSQL."
    Write-Warn "Ensure database '$DbName' already exists on $DbProvider before migrations run."
} else {
    Write-Step "Step 6/8 - Creating PostgreSQL database '$DbName'"

    # Pass credentials via temporary env vars so the single-quoted Python
    # here-string is never interpolated by PowerShell.
    $env:_MES_INST_HOST   = $dbHost
    $env:_MES_INST_PORT   = $dbPort
    $env:_MES_INST_USER   = $DbUser
    $env:_MES_INST_PASS   = $DbPassword
    $env:_MES_INST_DBNAME = $DbName

    $createDbResult = & $VenvPython -c @'
import asyncio, sys, os
import asyncpg

async def main():
    host    = os.environ["_MES_INST_HOST"]
    port    = int(os.environ["_MES_INST_PORT"])
    user    = os.environ["_MES_INST_USER"]
    password = os.environ["_MES_INST_PASS"]
    db_name  = os.environ["_MES_INST_DBNAME"]

    try:
        conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password,
            database="postgres"
        )
    except Exception as e:
        print(f"CONNECT_ERROR:{e}", file=sys.stderr)
        sys.exit(1)

    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if exists:
            print("EXISTS")
        else:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print("CREATED")
    finally:
        await conn.close()

asyncio.run(main())
'@ 2>&1

    # Clean up temporary env vars
    Remove-Item Env:_MES_INST_HOST, Env:_MES_INST_PORT, Env:_MES_INST_USER,
                Env:_MES_INST_PASS, Env:_MES_INST_DBNAME -ErrorAction SilentlyContinue

    $createDbStr = "$createDbResult"

    if ($createDbStr -match 'CONNECT_ERROR') {
        Write-Warn "Could not connect to PostgreSQL at ${dbHost}:${dbPort}."
        Write-Warn "Details: $($createDbStr -replace 'CONNECT_ERROR:', '')"
        Write-Warn ""
        Write-Warn "Ensure PostgreSQL is running and credentials are correct, then create"
        Write-Warn "the database manually:  CREATE DATABASE `"$DbName`";"
        Write-Warn ""
        Write-Warn "You can continue by rerunning the installer, or by running migrations"
        Write-Warn "manually:  .\run-server.ps1 PostgreSQL -DbName $DbName"
    } elseif ($createDbStr -match 'EXISTS') {
        Write-Ok "Database '$DbName' already exists."
    } elseif ($createDbStr -match 'CREATED') {
        Write-Ok "Database '$DbName' created."
    } else {
        Write-Warn "Unexpected output: $createDbStr"
    }
}

# --- Step 7: Alembic migrations --------------------------------------------
if ($SkipMigrations) {
    Write-Host "    --   Step 7 skipped (-SkipMigrations)"
} else {
    Write-Step "Step 7/8 - Checking database driver prerequisites"

    switch ($dbType) {
        "mssql"  { Test-MssqlOdbcDriver }
        "oracle" { Test-OracleClientAvailability }
        default   { Write-Ok "No additional database driver prerequisites required for $DbProvider." }
    }

    Write-Step "Step 7/8 - Running Alembic schema migrations"

    Push-Location $ServerDir
    try {
        $env:MES_DATABASE_URL = $dbUrl
        & $VenvPython -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            Fail "Alembic migration failed. Check that the database is reachable and credentials are correct."
        }
        Write-Ok "Schema migrations applied."
    } catch {
        Fail "Alembic migration failed: $_`n`nCheck that the database is reachable and credentials are correct."
    } finally {
        Pop-Location
        Remove-Item Env:MES_DATABASE_URL -ErrorAction SilentlyContinue
    }
}

# --- Step 8: npm dependencies ----------------------------------------------
if (-not $SkipClients) {
    Write-Step "Step 8/8 - Installing npm dependencies for browser clients"

    $clients = @(
        [PSCustomObject]@{ Name = "Design-Time client";        Dir = "clients\design_time" },
        [PSCustomObject]@{ Name = "Run-Time client";           Dir = "clients\run_time" },
        [PSCustomObject]@{ Name = "ERP Simulator";             Dir = "clients\erp_simulator" },
        [PSCustomObject]@{ Name = "Equipment Simulator";       Dir = "clients\equipment_simulator" }
    )

    foreach ($c in $clients) {
        $clientDir = Join-Path $ScriptDir $c.Dir
        if (Test-Path (Join-Path $clientDir "package.json")) {
            Write-Host "    Installing $($c.Name)..." -ForegroundColor White
            Push-Location $clientDir
            try {
                npm install --silent
                Write-Ok "$($c.Name) ready."
            } catch {
                Write-Warn "$($c.Name) npm install failed: $_"
            } finally {
                Pop-Location
            }
        } else {
            Write-Warn "$($c.Name): package.json not found at $clientDir - skipped."
        }
    }
} else {
    Write-Host "    --   Step 8 skipped (-SkipClients)"
}

# --- Summary ---------------------------------------------------------------
$summary = @"

================================================================
  MES AI installation complete!
================================================================

  Start the MES server:
        .\run-server.ps1 $DbProvider -DbName $DbName -Username $DbUser

  Start a client (open in a separate terminal):
    .\run-client.ps1 dt-client           # Design-Time (port 5173)
    .\run-client.ps1 rt-client           # Run-Time    (port 5176)
    .\run-client.ps1 erp-sim             # ERP Sim     (port 5174)
    .\run-client.ps1 equipment-sim       # Equip Sim   (port 5175)

  Configuration file:  server\.env
  Documentation:       README.md
================================================================
"@

Write-Host $summary -ForegroundColor Green
