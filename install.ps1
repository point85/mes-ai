#Requires -Version 5.1
<#
.SYNOPSIS
    MES AI - Windows bootstrapper

.DESCRIPTION
    Installs and starts MES AI using Docker Compose.
    On first run, copies .env.example to .env and generates a random secret key.
    On subsequent runs, pulls/builds updated images and restarts services.

.PARAMETER Build
    Build images from source instead of pulling from the registry.
    Use this when MES_IMAGE_TAG=local (the default) or when working from source.

.PARAMETER Pull
    Pull pre-built images from the registry (requires MES_IMAGE_TAG set to a
    published version tag in .env).

.PARAMETER Down
    Stop and remove containers (data volume is preserved).

.PARAMETER Reset
    Stop containers AND delete the PostgreSQL data volume (destructive - all data lost).

.EXAMPLE
    .\install.ps1             # build from source + start
    .\install.ps1 -Build      # same as above (explicit)
    .\install.ps1 -Pull       # pull images from registry + start
    .\install.ps1 -Down       # stop services
    .\install.ps1 -Reset      # stop + wipe database
#>
param(
    [switch]$Build,
    [switch]$Pull,
    [switch]$Down,
    [switch]$Reset
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# -- Helpers -------------------------------------------------------------------
function Write-Step  { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  [FAIL] $msg" -ForegroundColor Red }

function Get-RandomSecret {
    $chars = ([char[]]([char]'A'..[char]'Z') + [char[]]([char]'a'..[char]'z') + [char[]]([char]'0'..[char]'9'))
    return -join (1..48 | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
}

# -- Banner --------------------------------------------------------------------
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "         MES AI  -  Installer           " -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""

# -- Stop / Reset shortcuts ----------------------------------------------------
if ($Reset) {
    Write-Warn "Stopping containers and deleting database volume - all data will be lost..."
    docker compose down -v
    Write-Ok "Done. Run .\install.ps1 to start fresh."
    exit 0
}
if ($Down) {
    Write-Step "Stopping containers..."
    docker compose down
    Write-Ok "Services stopped. Data volume preserved."
    exit 0
}

# -- 1. Check Docker -----------------------------------------------------------
Write-Step "Checking Docker..."
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Fail "Docker not found."
    Write-Host "    Install Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Gray
    exit 1
}
$daemonVersion = docker version --format "{{.Server.Version}}" 2>$null
if (-not $daemonVersion) {
    Write-Fail "Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
}
Write-Ok "Docker $daemonVersion"

# -- 2. .env setup -------------------------------------------------------------
Write-Step "Checking .env..."
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    $secret = Get-RandomSecret
    (Get-Content ".env") -replace "change-me-to-a-random-32-byte-string", $secret | Set-Content ".env"
    Write-Ok "Created .env with a generated secret key. Review and customise before production use."
} else {
    Write-Ok ".env already exists."
}

# -- 3. Read image tag ---------------------------------------------------------
$imageTag = (Get-Content ".env" | Where-Object { $_ -match "^MES_IMAGE_TAG=" }) -replace "MES_IMAGE_TAG=", ""
if (-not $imageTag) { $imageTag = "local" }

# -- 4. Pull or build images ---------------------------------------------------
if ($Pull -or ($imageTag -ne "local" -and -not $Build)) {
    Write-Step "Pulling images (tag: $imageTag)..."
    docker compose pull
    Write-Ok "Images pulled."
} else {
    Write-Step "Building images from source..."
    docker compose build
    Write-Ok "Images built."
}

# -- 5. Start services ---------------------------------------------------------
Write-Step "Starting services..."
docker compose up -d
Write-Ok "Containers started."

# -- 6. Wait for server health -------------------------------------------------
Write-Step "Waiting for MES server to be ready (up to 90 s)..."
$maxWait  = 90
$waited   = 0
$health   = ""
while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 3
    $waited += 3
    $health = (docker inspect --format="{{.State.Health.Status}}" mes-server 2>$null) -as [string]
    if ($health -eq "healthy") { break }
    if ($waited % 15 -eq 0) { Write-Host "    ...still starting ($waited / $maxWait s)" -ForegroundColor Gray }
}
if ($health -eq "healthy") {
    Write-Ok "Server is healthy."
} else {
    Write-Warn "Server did not become healthy within ${maxWait}s."
    Write-Host "    Check logs: docker compose logs mes-server" -ForegroundColor Gray
}

# -- 7. Print access URLs ------------------------------------------------------
$portDt    = (Get-Content ".env" | Where-Object { $_ -match "^PORT_DT=" })    -replace "PORT_DT=", ""
$portRt    = (Get-Content ".env" | Where-Object { $_ -match "^PORT_RT=" })    -replace "PORT_RT=", ""
$portErp   = (Get-Content ".env" | Where-Object { $_ -match "^PORT_ERP_SIM=" }) -replace "PORT_ERP_SIM=", ""
$portEquip = (Get-Content ".env" | Where-Object { $_ -match "^PORT_EQUIP_SIM=" }) -replace "PORT_EQUIP_SIM=", ""
$portSrv   = (Get-Content ".env" | Where-Object { $_ -match "^PORT_SERVER=" }) -replace "PORT_SERVER=", ""
if (-not $portDt)    { $portDt    = "5173" }
if (-not $portRt)    { $portRt    = "5176" }
if (-not $portErp)   { $portErp   = "5174" }
if (-not $portEquip) { $portEquip = "5175" }
if (-not $portSrv)   { $portSrv   = "8082" }

Write-Host ""
Write-Host "  MES AI is running:" -ForegroundColor Green
Write-Host "    Design-Time Client  : http://localhost:$portDt" -ForegroundColor White
Write-Host "    Run-Time Client     : http://localhost:$portRt" -ForegroundColor White
Write-Host "    ERP Simulator       : http://localhost:$portErp" -ForegroundColor White
Write-Host "    Equipment Simulator : http://localhost:$portEquip" -ForegroundColor White
Write-Host "    API / Swagger Docs  : http://localhost:$portSrv/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Useful commands:" -ForegroundColor Gray
Write-Host "    docker compose logs -f          stream all logs" -ForegroundColor Gray
Write-Host "    docker compose logs mes-server  server logs only" -ForegroundColor Gray
Write-Host "    .\install.ps1 -Down             stop services" -ForegroundColor Gray
Write-Host "    .\install.ps1 -Reset            stop + wipe database" -ForegroundColor Gray
Write-Host ""

