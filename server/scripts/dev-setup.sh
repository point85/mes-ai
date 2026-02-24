#!/usr/bin/env bash
# MES AI — Development environment setup (WSL2 / Ubuntu 24.04)
# Run once: chmod +x scripts/dev-setup.sh && ./scripts/dev-setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== MES AI Dev Environment Setup ==="

# 1. Check Docker
if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker is not installed."
    echo "Install Docker Desktop for Windows and enable WSL2 integration,"
    echo "or install Docker Engine directly in WSL2:"
    echo "  https://docs.docker.com/engine/install/ubuntu/"
    exit 1
fi

echo "[✓] Docker found: $(docker --version)"

# 2. Check Python (try python3 first, fall back to python on Windows)
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
    if command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "ERROR: Python 3 is not installed."
        echo "  Install Python 3.12+ from https://www.python.org/downloads/"
        exit 1
    fi
fi

PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2)
echo "[✓] Python found: ${PYTHON_VERSION}"

# 3. Start PostgreSQL via Docker Compose
cd "$SERVER_DIR"
echo ""
echo "--- Starting PostgreSQL 16 ---"
docker compose up -d
echo "[✓] PostgreSQL running on localhost:5432"

# 4. Wait for PostgreSQL to be healthy
echo "--- Waiting for PostgreSQL to be ready ---"
for i in {1..30}; do
    if docker exec mes-pg pg_isready -U postgres &>/dev/null; then
        echo "[✓] PostgreSQL is ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: PostgreSQL did not become ready in 30s"
        exit 1
    fi
    sleep 1
done

# 5. Create .env from example if it doesn't exist
if [ ! -f "$SERVER_DIR/.env" ]; then
    cp "$SERVER_DIR/.env.example" "$SERVER_DIR/.env"
    echo "[✓] Created .env from .env.example"
else
    echo "[✓] .env already exists"
fi

# 6. Create virtual environment and install dependencies

# Detect OS: WSL sets /mnt/c paths, but the venv activation script location
# differs between Windows (Scripts/activate) and Unix (bin/activate).
if [ -f "$SERVER_DIR/.venv/Scripts/activate" ]; then
    ACTIVATE="$SERVER_DIR/.venv/Scripts/activate"
elif [ -f "$SERVER_DIR/.venv/bin/activate" ]; then
    ACTIVATE="$SERVER_DIR/.venv/bin/activate"
else
    ACTIVATE=""
fi

if [ ! -d "$SERVER_DIR/.venv" ] || [ -z "$ACTIVATE" ]; then
    echo ""
    echo "--- Creating virtual environment ---"
    $PYTHON_CMD -m venv "$SERVER_DIR/.venv"
    echo "[✓] Virtual environment created at .venv/"
    # Re-detect after creation
    if [ -f "$SERVER_DIR/.venv/Scripts/activate" ]; then
        ACTIVATE="$SERVER_DIR/.venv/Scripts/activate"
    else
        ACTIVATE="$SERVER_DIR/.venv/bin/activate"
    fi
fi

echo "--- Installing dependencies ---"
source "$ACTIVATE"
pip install -e ".[dev]" --quiet
echo "[✓] Dependencies installed"

# 7. Summary
ACTIVATE_CMD="source .venv/bin/activate"
if [ -f "$SERVER_DIR/.venv/Scripts/activate" ]; then
    ACTIVATE_CMD=".venv\\Scripts\\activate  (or source .venv/Scripts/activate in Git Bash)"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the virtual environment:"
echo "  $ACTIVATE_CMD"
echo ""
echo "To run the server:"
echo "  uvicorn mes.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "To run tests:"
echo "  python -m pytest tests/unit/ -v"
echo ""
echo "To stop PostgreSQL:"
echo "  docker compose down"
echo ""
