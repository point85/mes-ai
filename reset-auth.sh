#!/usr/bin/env bash
# reset-auth.sh — Reset MES authentication mode to "none" in server/.env.
#
# Emergency recovery script for when MES_AUTH_MODE has been set to
# "local" or "oidc" and access to dt-client is lost.
#
# Sets MES_AUTH_MODE=none in server/.env so the server accepts all
# requests without credentials after a restart.
#
# After regaining access, reconfigure authentication in the dt-client
# Settings page (Admin -> Settings).
#
# Usage:
#   ./reset-auth.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/server/.env"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC}  $*"; }
info() { echo -e "  ${CYAN}[  ]${NC}  $*"; }
warn() { echo -e "  ${YELLOW}[!!]${NC}  $*"; }
err()  { echo -e "  ${RED}[XX]${NC}  $*"; }

echo ""
echo -e "${CYAN}MES Authentication Reset${NC}"
echo -e "${CYAN}========================${NC}"
echo ""

# --- Verify .env exists -----------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
    err "server/.env not found at: $ENV_FILE"
    warn "Run install.sh first to create the environment file."
    exit 1
fi

info "Found: $ENV_FILE"

# --- Read current value -----------------------------------------------------
current_mode=""
if grep -qE '^\s*MES_AUTH_MODE\s*=' "$ENV_FILE"; then
    current_mode="$(grep -E '^\s*MES_AUTH_MODE\s*=' "$ENV_FILE" | tail -1 | sed 's/.*=\s*//' | tr -d '[:space:]')"
fi

if [ "$current_mode" = "none" ]; then
    ok "MES_AUTH_MODE is already set to 'none'. No changes needed."
    echo ""
    exit 0
fi

if [ -n "$current_mode" ]; then
    info "Current MES_AUTH_MODE: $current_mode"
else
    info "MES_AUTH_MODE not found in .env — it will be appended."
fi

# --- Rewrite .env with MES_AUTH_MODE=none -----------------------------------
TMP_FILE="$(mktemp)"

if grep -qE '^\s*MES_AUTH_MODE\s*=' "$ENV_FILE"; then
    # Replace existing line
    sed 's/^\s*MES_AUTH_MODE\s*=.*/MES_AUTH_MODE=none/' "$ENV_FILE" > "$TMP_FILE"
else
    # Append new line
    cp "$ENV_FILE" "$TMP_FILE"
    echo "MES_AUTH_MODE=none" >> "$TMP_FILE"
fi

mv "$TMP_FILE" "$ENV_FILE"

ok "MES_AUTH_MODE set to 'none' in server/.env"

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Restart the MES server (./run-server.sh)."
echo "  2. Open dt-client — login is no longer required."
echo "  3. Go to Admin -> Settings to reconfigure authentication."
echo ""
