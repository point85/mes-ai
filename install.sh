#!/usr/bin/env bash
# MES AI — macOS / Linux bootstrapper
#
# Usage:
#   ./install.sh             build from source + start (default)
#   ./install.sh --build     same as above (explicit)
#   ./install.sh --pull      pull pre-built images from registry + start
#   ./install.sh --down      stop services (data preserved)
#   ./install.sh --reset     stop + wipe database (DESTRUCTIVE)
#
# Requirements: Docker with Compose V2 (docker compose)

set -euo pipefail
cd "$(dirname "$0")"

# ── Parse flags ───────────────────────────────────────────────────────────────
DO_BUILD=0
DO_PULL=0
DO_DOWN=0
DO_RESET=0

for arg in "$@"; do
    case "$arg" in
        --build) DO_BUILD=1 ;;
        --pull)  DO_PULL=1  ;;
        --down)  DO_DOWN=1  ;;
        --reset) DO_RESET=1 ;;
    esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
C_CYAN='\033[0;36m'; C_GREEN='\033[0;32m'; C_YELLOW='\033[0;33m'
C_RED='\033[0;31m';  C_GRAY='\033[0;37m';  C_RESET='\033[0m'
step()  { echo -e "  ${C_CYAN}$*${C_RESET}"; }
ok()    { echo -e "  ${C_GREEN}[OK]${C_RESET} $*"; }
warn()  { echo -e "  ${C_YELLOW}[WARN]${C_RESET} $*"; }
fail()  { echo -e "  ${C_RED}[FAIL]${C_RESET} $*"; exit 1; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${C_CYAN}╔══════════════════════════════════════╗${C_RESET}"
echo -e "  ${C_CYAN}║        MES AI  —  Installer          ║${C_RESET}"
echo -e "  ${C_CYAN}╚══════════════════════════════════════╝${C_RESET}"
echo ""

# ── Stop / Reset shortcuts ────────────────────────────────────────────────────
if [[ $DO_RESET -eq 1 ]]; then
    warn "Stopping containers and deleting database volume (all data will be lost)..."
    docker compose down -v
    ok "Done. Run ./install.sh to start fresh."
    exit 0
fi
if [[ $DO_DOWN -eq 1 ]]; then
    step "Stopping containers..."
    docker compose down
    ok "Services stopped. Data volume preserved."
    exit 0
fi

# ── 1. Check Docker ───────────────────────────────────────────────────────────
step "Checking Docker..."
if ! command -v docker &>/dev/null; then
    fail "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop"
fi
if ! docker info &>/dev/null; then
    fail "Docker daemon is not running. Start Docker Desktop and try again."
fi
DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
ok "Docker $DOCKER_VER"

# ── 2. .env setup ─────────────────────────────────────────────────────────────
step "Checking .env..."
if [[ ! -f .env ]]; then
    cp .env.example .env
    # Generate a 48-char alphanumeric secret key
    if command -v python3 &>/dev/null; then
        SECRET=$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48)))")
    else
        SECRET=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 48 || true)
    fi
    if [[ -n "$SECRET" ]]; then
        sed -i.bak "s/change-me-to-a-random-32-byte-string/$SECRET/" .env
        rm -f .env.bak
        ok "Created .env with a generated secret key. Review and customise before production use."
    else
        ok "Created .env from .env.example. Set MES_SECRET_KEY before production use."
    fi
else
    ok ".env already exists."
fi

# ── 3. Read image tag ─────────────────────────────────────────────────────────
IMAGE_TAG=$(grep '^MES_IMAGE_TAG=' .env | cut -d= -f2 || echo "local")
IMAGE_TAG="${IMAGE_TAG:-local}"

# ── 4. Pull or build images ───────────────────────────────────────────────────
if [[ $DO_PULL -eq 1 ]] || ( [[ "$IMAGE_TAG" != "local" ]] && [[ $DO_BUILD -eq 0 ]] ); then
    step "Pulling images (tag: $IMAGE_TAG)..."
    docker compose pull
    ok "Images pulled."
else
    step "Building images from source..."
    docker compose build
    ok "Images built."
fi

# ── 5. Start services ─────────────────────────────────────────────────────────
step "Starting services..."
docker compose up -d
ok "Containers started."

# ── 6. Wait for server health ─────────────────────────────────────────────────
step "Waiting for MES server to be ready (up to 90 s)..."
MAX_WAIT=90
WAITED=0
HEALTH=""
while [[ $WAITED -lt $MAX_WAIT ]]; do
    sleep 3
    WAITED=$((WAITED + 3))
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' mes-server 2>/dev/null || echo "starting")
    [[ "$HEALTH" == "healthy" ]] && break
    [[ $((WAITED % 15)) -eq 0 ]] && echo -e "    ${C_GRAY}...still starting ($WAITED / ${MAX_WAIT}s)${C_RESET}"
done
if [[ "$HEALTH" == "healthy" ]]; then
    ok "Server is healthy."
else
    warn "Server did not become healthy within ${MAX_WAIT}s."
    echo -e "    ${C_GRAY}Check logs: docker compose logs mes-server${C_RESET}"
fi

# ── 7. Print access URLs ──────────────────────────────────────────────────────
PORT_DT=$(grep    '^PORT_DT='      .env | cut -d= -f2); PORT_DT="${PORT_DT:-5173}"
PORT_RT=$(grep    '^PORT_RT='      .env | cut -d= -f2); PORT_RT="${PORT_RT:-5176}"
PORT_ERP=$(grep   '^PORT_ERP_SIM=' .env | cut -d= -f2); PORT_ERP="${PORT_ERP:-5174}"
PORT_EQUIP=$(grep '^PORT_EQUIP_SIM=' .env | cut -d= -f2); PORT_EQUIP="${PORT_EQUIP:-5175}"
PORT_SRV=$(grep   '^PORT_SERVER='  .env | cut -d= -f2); PORT_SRV="${PORT_SRV:-8082}"

echo ""
echo -e "  ${C_GREEN}MES AI is running:${C_RESET}"
echo -e "    Design-Time Client  : ${C_CYAN}http://localhost:$PORT_DT${C_RESET}"
echo -e "    Run-Time Client     : ${C_CYAN}http://localhost:$PORT_RT${C_RESET}"
echo -e "    ERP Simulator       : ${C_CYAN}http://localhost:$PORT_ERP${C_RESET}"
echo -e "    Equipment Simulator : ${C_CYAN}http://localhost:$PORT_EQUIP${C_RESET}"
echo -e "    API / Swagger Docs  : ${C_CYAN}http://localhost:$PORT_SRV/docs${C_RESET}"
echo ""
echo -e "  ${C_GRAY}Useful commands:${C_RESET}"
echo -e "  ${C_GRAY}  docker compose logs -f           stream all logs${C_RESET}"
echo -e "  ${C_GRAY}  docker compose logs mes-server   server logs only${C_RESET}"
echo -e "  ${C_GRAY}  ./install.sh --down              stop services${C_RESET}"
echo -e "  ${C_GRAY}  ./install.sh --reset             stop + wipe database${C_RESET}"
echo ""
