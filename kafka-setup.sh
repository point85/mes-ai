#!/usr/bin/env bash
# setup.sh — Build, configure, and install the Kafka Java Bridge plugin.
#
# Three-step setup:
#   1. Build the Java fat-jar  (mvn clean package)
#   2. Generate Python gRPC stubs  (python proto/generate_stubs.py)
#   3. Install and enable the plugin via the MES CLI
#
# Usage:
#   ./setup.sh [OPTIONS]
#
# Options:
#   --bootstrap-servers HOST:PORT,...  Kafka bootstrap.servers (default: localhost:9092)
#   --topics JSON_ARRAY                Topics to subscribe to (default: ["equipment.events","quality.results"])
#   --consumer-group GROUP             Kafka consumer group ID (default: mes-kafka-bridge)
#   --bridge-port PORT                 gRPC loopback port (default: 50051)
#   --mes-event-type TOPIC             MES event bus topic (default: data.collected)
#   --server-url URL                   MES server URL (default: http://localhost:8082)
#   --skip-build                       Skip the Maven build step
#   --skip-stubs                       Skip Python stub generation
#   -h, --help                         Show this help
#
# Examples:
#   ./setup.sh
#   ./setup.sh --bootstrap-servers broker1:9092,broker2:9092 --topics '["my.topic"]'
#   ./setup.sh --skip-build --server-url http://prod-mes:8082

set -euo pipefail

# ── Defaults ────────────────────────────────────────────────────────────────
BOOTSTRAP_SERVERS="localhost:9092"
TOPICS='["equipment.events","quality.results"]'
CONSUMER_GROUP="mes-kafka-bridge"
BRIDGE_PORT=50051
MES_EVENT_TYPE="data.collected"
SERVER_URL="http://localhost:8082"
SKIP_BUILD=0
SKIP_STUBS=0

# ── Argument parsing ─────────────────────────────────────────────────────────
usage() {
    sed -n '2,/^$/p' "$0" | grep '^#' | sed 's/^# \?//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bootstrap-servers) BOOTSTRAP_SERVERS="$2"; shift 2 ;;
        --topics)            TOPICS="$2";             shift 2 ;;
        --consumer-group)    CONSUMER_GROUP="$2";     shift 2 ;;
        --bridge-port)       BRIDGE_PORT="$2";        shift 2 ;;
        --mes-event-type)    MES_EVENT_TYPE="$2";     shift 2 ;;
        --server-url)        SERVER_URL="$2";         shift 2 ;;
        --skip-build)        SKIP_BUILD=1;            shift   ;;
        --skip-stubs)        SKIP_STUBS=1;            shift   ;;
        -h|--help)           usage ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
PLUGIN_DIR="$PROJECT_DIR/server/plugins/system/kafka_java_bridge"
BRIDGE_DIR="$PLUGIN_DIR/bridge"
JAR_PATH="$BRIDGE_DIR/target/kafka-bridge-1.0.0-shaded.jar"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

step() { echo; echo "==> $*"; }
ok()   { echo "  $*"; }

# ── Pre-flight ───────────────────────────────────────────────────────────────
if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "ERROR: Virtual environment not found at $VENV_PYTHON" >&2
    echo "       Run ./install.sh first." >&2
    exit 1
fi

# ── Step 1: Maven build ──────────────────────────────────────────────────────
if [[ $SKIP_BUILD -eq 0 ]]; then
    step "Step 1/3 — Building Java fat-jar (Maven)"
    if ! command -v mvn &>/dev/null; then
        echo "ERROR: mvn not found on PATH. Install Maven 3.8+ and retry." >&2
        exit 1
    fi
    mvn -f "$BRIDGE_DIR/pom.xml" clean package -q
    ok "Built: $JAR_PATH"
else
    echo
    echo "[skip] Maven build"
    if [[ ! -f "$JAR_PATH" ]]; then
        echo "ERROR: --skip-build set but jar not found: $JAR_PATH" >&2
        exit 1
    fi
fi

# ── Step 2: Python gRPC stub generation ──────────────────────────────────────
if [[ $SKIP_STUBS -eq 0 ]]; then
    step "Step 2/3 — Generating Python gRPC stubs"

    if ! "$VENV_PYTHON" -c "import grpc_tools" 2>/dev/null; then
        echo "  Installing grpcio-tools into venv..."
        "$VENV_PYTHON" -m pip install "grpcio-tools>=1.60.0" -q
    fi

    "$VENV_PYTHON" "$PLUGIN_DIR/proto/generate_stubs.py"
    ok "Stubs written to: $PLUGIN_DIR/proto"
else
    echo
    echo "[skip] Python stub generation"
fi

# ── Step 3: Install + enable via MES CLI ─────────────────────────────────────
step "Step 3/3 — Installing plugin via MES CLI"

ABS_JAR_PATH="$(realpath "$JAR_PATH")"

"$VENV_PYTHON" -m mes.cli --server "$SERVER_URL" plugin install kafka-java-bridge \
    --param "bridge_jar=$ABS_JAR_PATH" \
    --param "bridge_port=$BRIDGE_PORT" \
    --param "bootstrap_servers=$BOOTSTRAP_SERVERS" \
    --param "topics=$TOPICS" \
    --param "consumer_group=$CONSUMER_GROUP" \
    --param "mes_event_type=$MES_EVENT_TYPE"

echo
echo "  Enabling plugin..."
"$VENV_PYTHON" -m mes.cli --server "$SERVER_URL" plugin enable kafka-java-bridge

echo
echo "Done. kafka-java-bridge is installed and enabled."
ok "Jar:             $ABS_JAR_PATH"
ok "Bootstrap:       $BOOTSTRAP_SERVERS"
ok "Topics:          $TOPICS"
ok "Consumer group:  $CONSUMER_GROUP"
ok "gRPC port:       $BRIDGE_PORT"
ok "MES event type:  $MES_EVENT_TYPE"
