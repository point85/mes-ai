#!/usr/bin/env bash
# run-client.sh — Start a MES AI client application (Vite dev server).
# Compatible with bash and zsh.
#
# Usage:
#   ./run-client.sh <Client> [options]
#
# Run  ./run-client.sh --help  for full documentation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
CLIENT=""
PORT=0
SERVER_URL=""

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
show_help() {
    cat <<'EOF'

USAGE
  ./run-client.sh <Client> [options]

ARGUMENTS
  Client               (required)  Client application to start (case-insensitive):
                                     dt-client       Design-Time client     (port 5173)
                                     rt-client       Run-Time client        (port 5176)
                                     erp-sim         ERP Simulator          (port 5174)
                                     equipment-sim   Equipment Simulator    (port 5175)

OPTIONS
  --port       NUM   Override the Vite dev server port.
  --server-url URL   MES server to proxy API calls to (default: http://localhost:8082).
                     Sets MES_SERVER_URL env var read by vite.config.ts.
  -h, --help         Show this help message.

EXAMPLES
  ./run-client.sh dt-client
  ./run-client.sh rt-client --port 3000
  ./run-client.sh rt-client --server-url http://localhost:8083
  ./run-client.sh erp-sim
  ./run-client.sh equipment-sim --port 5200

EOF
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
if [[ $# -eq 0 ]]; then
    show_help
    exit 0
fi

POSITIONAL=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --port)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --port requires a value." >&2
                exit 1
            fi
            PORT="$2"
            shift 2
            ;;
        --server-url)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --server-url requires a value." >&2
                exit 1
            fi
            SERVER_URL="$2"
            shift 2
            ;;
        -*)
            echo "Error: Unknown option '$1'." >&2
            show_help
            exit 1
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

if [[ ${#POSITIONAL[@]} -ge 1 ]]; then
    CLIENT="${POSITIONAL[0]}"
fi

# ---------------------------------------------------------------------------
# Resolve client
# ---------------------------------------------------------------------------
CLIENT_LOWER="$(echo "$CLIENT" | tr '[:upper:]' '[:lower:]')"

case "$CLIENT_LOWER" in
    dt-client)
        CLIENT_DIR="$SCRIPT_DIR/clients/design_time"
        DEFAULT_PORT=5173
        LABEL="Design-Time Client"
        ;;
    rt-client)
        CLIENT_DIR="$SCRIPT_DIR/clients/run_time"
        DEFAULT_PORT=5176
        LABEL="Run-Time Client"
        ;;
    erp-sim)
        CLIENT_DIR="$SCRIPT_DIR/clients/erp_simulator"
        DEFAULT_PORT=5174
        LABEL="ERP Simulator"
        ;;
    equipment-sim)
        CLIENT_DIR="$SCRIPT_DIR/clients/equipment_simulator"
        DEFAULT_PORT=5175
        LABEL="Equipment Simulator"
        ;;
    "")
        echo "Error: Client argument is required." >&2
        show_help
        exit 1
        ;;
    *)
        echo "Error: Unknown client '$CLIENT'." >&2
        echo "Valid options: dt-client, rt-client, erp-sim, equipment-sim" >&2
        exit 1
        ;;
esac

EFFECTIVE_PORT="${PORT:-$DEFAULT_PORT}"
if [[ "$PORT" -eq 0 ]]; then
    EFFECTIVE_PORT="$DEFAULT_PORT"
fi

if [[ ! -d "$CLIENT_DIR" ]]; then
    echo "Error: Client directory not found: $CLIENT_DIR" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "MES AI Client Startup"
echo "====================="
EFFECTIVE_SERVER_URL="${SERVER_URL:-http://localhost:8082}"
export MES_SERVER_URL="$EFFECTIVE_SERVER_URL"
echo "  Client     : $LABEL"
echo "  Dir        : $CLIENT_DIR"
echo "  URL        : http://localhost:${EFFECTIVE_PORT}"
echo "  MES Server : $EFFECTIVE_SERVER_URL"
echo ""

# ---------------------------------------------------------------------------
# Install dependencies if needed
# ---------------------------------------------------------------------------
if [[ ! -d "$CLIENT_DIR/node_modules" ]]; then
    echo "Installing npm dependencies..."
    cd "$CLIENT_DIR"
    npm install
fi

# ---------------------------------------------------------------------------
# Start Vite dev server
# ---------------------------------------------------------------------------
echo "Starting $LABEL..."
echo "Press Ctrl+C to stop."
echo ""

cd "$CLIENT_DIR"
if [[ "$PORT" -ne 0 ]]; then
    npx vite --port "$EFFECTIVE_PORT"
else
    npx vite
fi
