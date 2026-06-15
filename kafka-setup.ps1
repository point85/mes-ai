<#
.SYNOPSIS
    Build, configure, and install the Kafka Java Bridge plugin.

.DESCRIPTION
    Three-step setup for the kafka-java-bridge plugin:
      1. Build the Java fat-jar  (mvn clean package)
      2. Generate Python gRPC stubs  (python proto/generate_stubs.py)
      3. Install and enable the plugin via the MES CLI

    Run this script from any directory; it resolves all paths relative to its
    own location so it works whether invoked from the project root or from
    within the plugin directory.

.PARAMETER BootstrapServers
    Kafka bootstrap.servers value.  Default: localhost:9092

.PARAMETER Topics
    JSON array of Kafka topic names to subscribe to.
    Default: '["equipment.events","quality.results"]'
    Use '[]' for publish-only mode.

.PARAMETER ConsumerGroup
    Kafka consumer group ID.  Default: mes-kafka-bridge

.PARAMETER BridgePort
    Loopback port the Java gRPC sidecar listens on.  Default: 50051

.PARAMETER MesEventType
    MES event bus topic published for each incoming Kafka record.
    Default: data.collected

.PARAMETER ServerUrl
    MES server URL for the CLI install/enable REST calls.
    Default: http://localhost:8082

.PARAMETER SkipBuild
    Skip the Maven build step (re-use an existing jar).

.PARAMETER SkipStubs
    Skip the Python gRPC stub generation step.

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 -BootstrapServers broker1:9092,broker2:9092 -Topics '["my.topic"]'
    .\setup.ps1 -SkipBuild -ServerUrl http://prod-mes:8082
#>

[CmdletBinding()]
param(
    [string]$BootstrapServers = "localhost:9092",
    [string]$Topics           = '["equipment.events","quality.results"]',
    [string]$ConsumerGroup    = "mes-kafka-bridge",
    [int]   $BridgePort       = 50051,
    [string]$MesEventType     = "data.collected",
    [string]$ServerUrl        = "http://localhost:8082",
    [switch]$SkipBuild,
    [switch]$SkipStubs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ──────────────────────────────────────────────────────────────────
$ProjectDir = $PSScriptRoot
$PluginDir  = Join-Path $ProjectDir "server\plugins\system\kafka_java_bridge"
$BridgeDir  = Join-Path $PluginDir "bridge"
$JarPath    = Join-Path $BridgeDir "target\kafka-bridge-1.0.0-shaded.jar"
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"

function Write-Step([string]$msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Assert-Command([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Error "$name not found on PATH. Please install it and retry."
        exit 1
    }
}

# ── Pre-flight checks ───────────────────────────────────────────────────────
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at $VenvPython`nRun .\install.ps1 first."
    exit 1
}

# ── Step 1: Maven build ─────────────────────────────────────────────────────
if (-not $SkipBuild) {
    Write-Step "Step 1/3 — Building Java fat-jar (Maven)"
    Assert-Command "mvn"
    $PomFile = Join-Path $BridgeDir "pom.xml"
    mvn -f $PomFile clean package -q
    if ($LASTEXITCODE -ne 0) { Write-Error "Maven build failed."; exit 1 }
    Write-Host "  Built: $JarPath" -ForegroundColor Green
} else {
    Write-Host "`n[skip] Maven build" -ForegroundColor Yellow
    if (-not (Test-Path $JarPath)) {
        Write-Error "SkipBuild was set but jar not found: $JarPath"
        exit 1
    }
}

# ── Step 2: Python gRPC stub generation ─────────────────────────────────────
if (-not $SkipStubs) {
    Write-Step "Step 2/3 — Generating Python gRPC stubs"
    $GenScript = Join-Path $PluginDir "proto\generate_stubs.py"

    # Ensure grpcio-tools is present in the venv
    & $VenvPython -c "import grpc_tools" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Installing grpcio-tools into venv..." -ForegroundColor Yellow
        & $VenvPython -m pip install "grpcio-tools>=1.60.0" -q
        if ($LASTEXITCODE -ne 0) { Write-Error "pip install grpcio-tools failed."; exit 1 }
    }

    & $VenvPython $GenScript
    if ($LASTEXITCODE -ne 0) { Write-Error "Stub generation failed."; exit 1 }
    Write-Host "  Stubs written to: $(Join-Path $PluginDir 'proto')" -ForegroundColor Green
} else {
    Write-Host "`n[skip] Python stub generation" -ForegroundColor Yellow
}

# ── Step 3: Install + enable via MES CLI ────────────────────────────────────
Write-Step "Step 3/3 — Installing plugin via MES CLI"

$AbsJarPath = (Resolve-Path $JarPath).Path

& $VenvPython -m mes.cli --server $ServerUrl plugin install kafka-java-bridge `
    --param "bridge_jar=$AbsJarPath" `
    --param "bridge_port=$BridgePort" `
    --param "bootstrap_servers=$BootstrapServers" `
    --param "topics=$Topics" `
    --param "consumer_group=$ConsumerGroup" `
    --param "mes_event_type=$MesEventType"

if ($LASTEXITCODE -ne 0) { Write-Error "Plugin install failed."; exit 1 }

Write-Host "`n  Enabling plugin..." -ForegroundColor Cyan
& $VenvPython -m mes.cli --server $ServerUrl plugin enable kafka-java-bridge
if ($LASTEXITCODE -ne 0) { Write-Error "Plugin enable failed."; exit 1 }

Write-Host "`nDone. kafka-java-bridge is installed and enabled." -ForegroundColor Green
Write-Host "  Jar:              $AbsJarPath"
Write-Host "  Bootstrap:        $BootstrapServers"
Write-Host "  Topics:           $Topics"
Write-Host "  Consumer group:   $ConsumerGroup"
Write-Host "  gRPC port:        $BridgePort"
Write-Host "  MES event type:   $MesEventType"
