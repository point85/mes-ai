<#
.SYNOPSIS
    Install PostgreSQL on Windows via winget.

.DESCRIPTION
    Checks whether PostgreSQL is already installed, then uses winget to download
    and install it if not.  After installation, prints the commands needed to
    start the service and set the postgres user password before running
    install.ps1.

    Run this script BEFORE install.ps1 if you do not already have a PostgreSQL
    instance available (local or remote).

.PARAMETER Help
    Show this help message and exit.

.EXAMPLE
    .\install-postgresql.ps1

.EXAMPLE
    .\install-postgresql.ps1 -Help
#>

[CmdletBinding()]
param(
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    $UnknownArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Help -------------------------------------------------------------------
function Show-Help {
  Write-Host @'

USAGE
  .\install-postgresql.ps1

OPTIONS
  -Help    Show this message.

DESCRIPTION
  Installs PostgreSQL via winget if it is not already present on this machine.
  Run this script before install.ps1 when you do not have an existing
  PostgreSQL instance.

  After installation you will need to:
    1. Start the PostgreSQL service (if it did not start automatically).
    2. Set the postgres user password.
    3. Run install.ps1 to complete the MES AI setup.

NEXT STEPS (after this script completes)
  Start the service:
    Start-Service postgresql-x64-<version>     # adjust version number

  Set the postgres password (connect as the Windows postgres user):
    psql -U postgres -c "ALTER USER postgres PASSWORD 'your_password';"

  Then install MES AI:
    .\install.ps1 -DbPassword your_password

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

# --- Output helpers ---------------------------------------------------------
function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "    OK   $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "    WARN $msg" -ForegroundColor Yellow }
function Fail([string]$msg)       { Write-Host "`nERROR: $msg" -ForegroundColor Red; exit 1 }

# --- Check whether PostgreSQL is already installed --------------------------
Write-Step "Checking for existing PostgreSQL installation"

$pgFound = $false
try { & psql --version 2>&1 | Out-Null; $pgFound = $true } catch { }

if ($pgFound) {
    Write-Ok "PostgreSQL is already installed: $((& psql --version 2>&1))"
    Write-Host ""
    Write-Host "  Nothing to do.  Run install.ps1 to set up MES AI." -ForegroundColor Green
    exit 0
}

# --- Verify winget is available --------------------------------------------
Write-Step "Checking winget"

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Fail (@"
winget is not available on this system.

Install PostgreSQL manually from:
  https://www.postgresql.org/download/windows/

Then run install.ps1 to complete the MES AI setup.
"@)
}

Write-Ok "winget found: $((winget --version 2>&1))"

# --- Install PostgreSQL -----------------------------------------------------
Write-Step "Installing PostgreSQL via winget (this may take several minutes)"

winget install --id PostgreSQL.PostgreSQL --source winget `
    --accept-source-agreements --accept-package-agreements

# Refresh PATH so psql is visible in this session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Ok "PostgreSQL installed."

# --- Post-install guidance --------------------------------------------------
$summary = @"

================================================================
  PostgreSQL installation complete!
================================================================

  Next steps:

  1. Start the PostgreSQL service if it is not already running.
     Find the exact service name with:
       Get-Service | Where-Object { `$_.Name -like 'postgresql*' }
     Then start it:
       Start-Service postgresql-x64-<version>

  2. Set the postgres user password (required before running install.ps1):
       psql -U postgres -c "ALTER USER postgres PASSWORD 'your_password';"

     If psql is not on PATH yet, open a new terminal first so the updated
     PATH takes effect.

  3. Run the MES AI installer:
       .\install.ps1 -DbPassword your_password

================================================================
"@

Write-Host $summary -ForegroundColor Green
