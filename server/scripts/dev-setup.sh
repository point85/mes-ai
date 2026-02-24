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

# 2. Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "  sudo apt update && sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
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
if [ ! -d "$SERVER_DIR/.venv" ]; then
    echo ""
    echo "--- Creating virtual environment ---"
    python3 -m venv "$SERVER_DIR/.venv"
    echo "[✓] Virtual environment created at .venv/"
fi

echo "--- Installing dependencies ---"
source "$SERVER_DIR/.venv/bin/activate"
pip install -e ".[dev]" --quiet
echo "[✓] Dependencies installed"

# 7. Summary
echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
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
