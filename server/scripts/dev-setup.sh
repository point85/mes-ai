#!/usr/bin/env bash
# MES AI — Development environment bootstrap & launcher
# Assumes PostgreSQL 16 is running natively on the host OS (not Docker).
#
# Usage:
#   chmod +x scripts/dev-setup.sh
#   ./scripts/dev-setup.sh            # setup + start server & DT-CLIENT
#   ./scripts/dev-setup.sh --setup    # setup only (install deps, run migrations)
#   ./scripts/dev-setup.sh --start    # start only (skip setup, launch services)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"
CLIENT_DIR="$(dirname "$SERVER_DIR")/clients/design_time"

MODE="${1:-all}"  # all | --setup | --start

# ── Helpers ──────────────────────────────────────────────────────

detect_python() {
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "ERROR: Python 3 is not installed."
        echo "  Install Python 3.12+ from https://www.python.org/downloads/"
        exit 1
    fi
    PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2)
    echo "[✓] Python found: ${PYTHON_VERSION}"
}

detect_node() {
    if ! command -v node &>/dev/null; then
        echo "ERROR: Node.js is not installed."
        echo "  Install Node.js 18+ from https://nodejs.org/"
        exit 1
    fi
    echo "[✓] Node.js found: $(node --version)"
}

detect_venv_activate() {
    # Windows venv uses Scripts/; Unix uses bin/
    if [ -f "$SERVER_DIR/.venv/Scripts/activate" ]; then
        ACTIVATE="$SERVER_DIR/.venv/Scripts/activate"
    elif [ -f "$SERVER_DIR/.venv/bin/activate" ]; then
        ACTIVATE="$SERVER_DIR/.venv/bin/activate"
    else
        ACTIVATE=""
    fi
}

check_postgres() {
    echo "--- Checking PostgreSQL connectivity ---"
    # Try psql if available, otherwise attempt a Python probe
    if command -v psql &>/dev/null; then
        if psql "postgresql://postgres:postgres@localhost:5432/mes_ai" -c "SELECT 1" &>/dev/null; then
            echo "[✓] PostgreSQL is reachable on localhost:5432"
            return 0
        fi
    fi
    # Fallback: lightweight Python check
    if $PYTHON_CMD -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
try:
    s.connect(('localhost', 5432)); s.close(); sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo "[✓] PostgreSQL port 5432 is open on localhost"
        return 0
    fi

    echo "ERROR: Cannot reach PostgreSQL on localhost:5432."
    echo "  Make sure PostgreSQL is running natively on this machine."
    echo "  Database: mes_ai  User: postgres  Password: postgres"
    exit 1
}

# ── Setup ────────────────────────────────────────────────────────

do_setup() {
    echo "=== MES AI Dev Environment Setup ==="

    detect_python
    detect_node

    cd "$SERVER_DIR"

    # PostgreSQL connectivity
    check_postgres

    # .env
    if [ ! -f "$SERVER_DIR/.env" ]; then
        if [ -f "$SERVER_DIR/.env.example" ]; then
            cp "$SERVER_DIR/.env.example" "$SERVER_DIR/.env"
            # Default to auth disabled for dev
            sed -i 's/^MES_AUTH_MODE=.*/MES_AUTH_MODE=none/' "$SERVER_DIR/.env" 2>/dev/null || true
            echo "[✓] Created .env from .env.example (auth=none)"
        else
            echo "[!] No .env.example found — using built-in defaults"
        fi
    else
        echo "[✓] .env already exists"
    fi

    # Python venv + deps
    detect_venv_activate
    if [ ! -d "$SERVER_DIR/.venv" ] || [ -z "$ACTIVATE" ]; then
        echo ""
        echo "--- Creating Python virtual environment ---"
        $PYTHON_CMD -m venv "$SERVER_DIR/.venv"
        echo "[✓] Virtual environment created at server/.venv/"
        detect_venv_activate
    fi

    echo "--- Installing Python dependencies ---"
    source "$ACTIVATE"
    pip install -e ".[dev]" --quiet
    echo "[✓] Python dependencies installed"

    # Alembic migrations
    echo "--- Running database migrations ---"
    cd "$SERVER_DIR"
    alembic upgrade head 2>/dev/null && echo "[✓] Alembic migrations applied" \
        || echo "[!] Alembic migration skipped (may already be current)"

    # Node deps for DT-CLIENT
    if [ -d "$CLIENT_DIR" ]; then
        echo ""
        echo "--- Installing DT-CLIENT dependencies ---"
        cd "$CLIENT_DIR"
        npm install --silent 2>/dev/null || npm install
        echo "[✓] DT-CLIENT dependencies installed"
    fi

    echo ""
    echo "=== Setup Complete ==="
}

# ── Start ────────────────────────────────────────────────────────

do_start() {
    echo ""
    echo "=== Starting MES AI Services ==="

    detect_python
    detect_venv_activate

    if [ -z "$ACTIVATE" ]; then
        echo "ERROR: Python venv not found. Run with --setup first."
        exit 1
    fi

    source "$ACTIVATE"

    # Ensure PostgreSQL is reachable before launching
    check_postgres

    # Start FastAPI server in background
    echo ""
    echo "--- Starting MES server (port 8000) ---"
    cd "$SERVER_DIR"
    export MES_AUTH_MODE="${MES_AUTH_MODE:-none}"
    uvicorn mes.main:app --reload --host 0.0.0.0 --port 8000 &
    SERVER_PID=$!
    echo "[✓] MES server started (PID $SERVER_PID)"

    # Wait briefly for server to be ready
    sleep 2

    # Start DT-CLIENT dev server in background
    if [ -d "$CLIENT_DIR" ]; then
        echo "--- Starting DT-CLIENT (port 5173) ---"
        cd "$CLIENT_DIR"
        npm run dev &
        CLIENT_PID=$!
        echo "[✓] DT-CLIENT started (PID $CLIENT_PID)"
    fi

    echo ""
    echo "=== MES AI is running ==="
    echo ""
    echo "  Server API:   http://localhost:8000/api/v1/docs"
    echo "  DT-CLIENT:    http://localhost:5173"
    echo "  Health check: http://localhost:8000/health"
    echo ""
    echo "Press Ctrl+C to stop all services."
    echo ""

    # Trap Ctrl+C to cleanly shut down background processes
    trap 'echo ""; echo "Shutting down..."; kill $SERVER_PID 2>/dev/null; kill $CLIENT_PID 2>/dev/null; exit 0' INT TERM

    # Wait for either process to exit
    wait
}

# ── Main ─────────────────────────────────────────────────────────

case "$MODE" in
    --setup)
        do_setup
        ;;
    --start)
        do_start
        ;;
    all|*)
        do_setup
        do_start
        ;;
esac
