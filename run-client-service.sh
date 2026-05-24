#!/usr/bin/env bash
# run-client-service.sh — Manage a MES AI Vite client as a systemd service.
#
# Installs, uninstalls, starts, stops, restarts, or queries the status of
# a MES AI Vite client (dt-client, rt-client, erp-sim, or equipment-sim)
# as a systemd unit. All runtime parameters are read from a configuration
# file so that nothing sensitive appears on the command line.
#
# Usage:
#   ./run-client-service.sh <action> [--config <path>]
#
# Run  ./run-client-service.sh  with no arguments for full help.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
if [[ -t 1 ]]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_RED=$'\033[31m';  C_WHITE=$'\033[97m'; C_RESET=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_WHITE=""; C_RESET=""
fi

write_step()  { echo "${C_CYAN}  >> $*${C_RESET}"; }
write_ok()    { echo "${C_GREEN}  OK $*${C_RESET}"; }
write_warn()  { echo "${C_YELLOW} WARN $*${C_RESET}"; }
write_fatal() { echo "${C_RED}FATAL $*${C_RESET}" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Help / usage
# ---------------------------------------------------------------------------
show_help() {
    cat <<'EOF'

USAGE
  ./run-client-service.sh <action> [--config <path>]

ACTIONS
  install    Register and configure the Vite client systemd service (requires root/sudo)
  uninstall  Remove the systemd service (requires root/sudo)
  start      Start the service (requires root/sudo)
  stop       Stop the service (requires root/sudo)
  restart    Restart the service (requires root/sudo)
  status     Show current service status

OPTIONS
  --config <path>   Path to config file (default: rt-service.conf)

EXAMPLES
  sudo ./run-client-service.sh install
  sudo ./run-client-service.sh install --config ./dt-service.conf
  sudo ./run-client-service.sh start
       ./run-client-service.sh status
  sudo ./run-client-service.sh uninstall

  See rt-service.conf for all available configuration keys.

EOF
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
ACTION=""
CONFIG_FILE=""

if [[ $# -eq 0 ]]; then
    echo ""
    echo "${C_WHITE}MES AI Client Service Manager${C_RESET}"
    echo "${C_WHITE}=============================${C_RESET}"
    show_help
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        install|uninstall|start|stop|restart|status)
            ACTION="$1"; shift ;;
        --config|-c)
            CONFIG_FILE="$2"; shift 2 ;;
        -h|--help)
            show_help; exit 0 ;;
        *)
            echo "${C_RED}ERROR: Unknown argument: $1${C_RESET}" >&2
            echo "Run ./run-client-service.sh with no arguments to see usage."
            exit 1 ;;
    esac
done

if [[ -z "$ACTION" ]]; then
    show_help; exit 0
fi

if [[ -z "$CONFIG_FILE" ]]; then
    CONFIG_FILE="$SCRIPT_DIR/rt-service.conf"
fi

# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------
declare -A CFG=()
read_config() {
    local path="$1"
    if [[ ! -f "$path" ]]; then
        write_fatal "Configuration file not found: $path
Copy rt-service.conf and edit it."
    fi
    local lineno=0 line trimmed key value
    while IFS= read -r line || [[ -n "$line" ]]; do
        lineno=$((lineno + 1))
        trimmed="${line#"${line%%[![:space:]]*}"}"
        trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
        [[ -z "$trimmed" ]] && continue
        [[ "$trimmed" == \#* ]] && continue
        if [[ ! "$trimmed" =~ ^([A-Za-z][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
            write_warn "Ignoring unrecognised line $lineno in $path: $line"
            continue
        fi
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        value="${value%"${value##*[![:space:]]}"}"
        CFG[$key]="$value"
    done < "$path"
}

cfg_value() {
    local key="$1" default="${2-}"
    if [[ -n "${CFG[$key]+x}" && -n "${CFG[$key]}" ]]; then
        echo "${CFG[$key]}"
    else
        echo "$default"
    fi
}

# ---------------------------------------------------------------------------
# Client directory map
# ---------------------------------------------------------------------------
resolve_client() {
    local client_key="${1,,}"
    case "$client_key" in
        dt-client)
            CLIENT_DIR="$SCRIPT_DIR/clients/design_time"
            DEFAULT_PORT=5173
            CLIENT_LABEL="Design-Time Client"
            ;;
        rt-client)
            CLIENT_DIR="$SCRIPT_DIR/clients/run_time"
            DEFAULT_PORT=5176
            CLIENT_LABEL="Run-Time Client"
            ;;
        erp-sim)
            CLIENT_DIR="$SCRIPT_DIR/clients/erp_simulator"
            DEFAULT_PORT=5174
            CLIENT_LABEL="ERP Simulator"
            ;;
        equipment-sim)
            CLIENT_DIR="$SCRIPT_DIR/clients/equipment_simulator"
            DEFAULT_PORT=5175
            CLIENT_LABEL="Equipment Simulator"
            ;;
        *)
            write_fatal "Unknown Client '$client_key'.
Valid values: dt-client, rt-client, erp-sim, equipment-sim"
            ;;
    esac
}

# ---------------------------------------------------------------------------
# systemd helpers
# ---------------------------------------------------------------------------
require_systemd() {
    if ! command -v systemctl &>/dev/null; then
        write_fatal "systemd not found.  This script requires a systemd-based Linux distribution."
    fi
}

assert_root() {
    if [[ "$EUID" -ne 0 ]]; then
        write_fatal "This action requires root privileges.  Re-run with sudo."
    fi
}

unit_path() { echo "/etc/systemd/system/${1}.service"; }

get_service_status() {
    local name="$1"
    if [[ ! -f "$(unit_path "$name")" ]]; then
        echo "not-installed"; return
    fi
    if systemctl is-active --quiet "$name" 2>/dev/null; then
        echo "running"
    else
        echo "stopped"
    fi
}

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
echo ""
echo "${C_WHITE}MES AI Client Service Manager${C_RESET}"
echo "${C_WHITE}=============================${C_RESET}"

require_systemd

# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "status" ]]; then
    read_config "$CONFIG_FILE"
    NAME="$(cfg_value ServiceName mes-ai-rt-client)"
    CLIENT_KEY="$(cfg_value Client rt-client)"
    resolve_client "$CLIENT_KEY"
    STATUS="$(get_service_status "$NAME")"
    case "$STATUS" in
        running)        COLOUR="$C_GREEN" ;;
        not-installed)  COLOUR="$C_YELLOW" ;;
        *)              COLOUR="$C_RED" ;;
    esac
    echo "  Client   : $CLIENT_LABEL"
    echo "  Service  : $NAME"
    echo "  Status   : ${COLOUR}${STATUS}${C_RESET}"
    if [[ "$STATUS" != "not-installed" ]]; then
        echo ""
        systemctl --no-pager --lines=0 status "$NAME" || true
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
# STOP
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "stop" ]]; then
    assert_root
    read_config "$CONFIG_FILE"
    NAME="$(cfg_value ServiceName mes-ai-rt-client)"
    STATUS="$(get_service_status "$NAME")"
    if [[ "$STATUS" == "not-installed" ]]; then
        write_warn "Service '$NAME' is not installed."; exit 0
    fi
    if [[ "$STATUS" != "running" ]]; then
        write_warn "Service '$NAME' is already stopped (status: $STATUS)."; exit 0
    fi
    write_step "Stopping service '$NAME'..."
    systemctl stop "$NAME"
    write_ok "Service stopped."
    exit 0
fi

# ---------------------------------------------------------------------------
# START
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "start" ]]; then
    assert_root
    read_config "$CONFIG_FILE"
    NAME="$(cfg_value ServiceName mes-ai-rt-client)"
    STATUS="$(get_service_status "$NAME")"
    if [[ "$STATUS" == "not-installed" ]]; then
        write_fatal "Service '$NAME' is not installed.  Run: sudo ./run-client-service.sh install"
    fi
    if [[ "$STATUS" == "running" ]]; then
        write_warn "Service '$NAME' is already running."; exit 0
    fi
    write_step "Starting service '$NAME'..."
    systemctl start "$NAME"
    write_ok "Service started."
    exit 0
fi

# ---------------------------------------------------------------------------
# RESTART
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "restart" ]]; then
    assert_root
    read_config "$CONFIG_FILE"
    NAME="$(cfg_value ServiceName mes-ai-rt-client)"
    if [[ "$(get_service_status "$NAME")" == "not-installed" ]]; then
        write_fatal "Service '$NAME' is not installed.  Run: sudo ./run-client-service.sh install"
    fi
    write_step "Restarting service '$NAME'..."
    systemctl restart "$NAME"
    write_ok "Service restarted."
    exit 0
fi

# ---------------------------------------------------------------------------
# UNINSTALL
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "uninstall" ]]; then
    assert_root
    read_config "$CONFIG_FILE"
    NAME="$(cfg_value ServiceName mes-ai-rt-client)"
    STATUS="$(get_service_status "$NAME")"
    if [[ "$STATUS" == "not-installed" ]]; then
        write_warn "Service '$NAME' is not installed."; exit 0
    fi
    if [[ "$STATUS" == "running" ]]; then
        write_step "Stopping running service before removal..."
        systemctl stop "$NAME" || true
    fi
    write_step "Disabling service '$NAME'..."
    systemctl disable "$NAME" 2>/dev/null || true
    write_step "Removing unit file..."
    rm -f "$(unit_path "$NAME")"
    systemctl daemon-reload
    systemctl reset-failed "$NAME" 2>/dev/null || true
    write_ok "Service '$NAME' removed."
    exit 0
fi

# ---------------------------------------------------------------------------
# INSTALL
# ---------------------------------------------------------------------------
assert_root
read_config "$CONFIG_FILE"

# Resolve client
CLIENT_KEY="$(cfg_value Client rt-client)"
resolve_client "$CLIENT_KEY"

if [[ ! -d "$CLIENT_DIR" ]]; then
    write_fatal "Client directory not found: $CLIENT_DIR"
fi

# Ensure node_modules is present
NODE_MODULES="$CLIENT_DIR/node_modules"
if [[ ! -d "$NODE_MODULES" ]]; then
    write_step "node_modules not found — running npm install in $CLIENT_DIR ..."
    (cd "$CLIENT_DIR" && npm install)
    write_ok "npm install complete."
fi

# Locate vite binary and node
VITE_BIN="$CLIENT_DIR/node_modules/vite/bin/vite.js"
if [[ ! -f "$VITE_BIN" ]]; then
    write_fatal "Vite binary not found at: $VITE_BIN
Run npm install in $CLIENT_DIR."
fi

NODE_EXE="$(command -v node 2>/dev/null || true)"
if [[ -z "$NODE_EXE" ]]; then
    write_fatal "Node.js not found on PATH.  Install Node.js 20+ and re-run."
fi

# Wrapper script that strips ANSI escape codes / non-ASCII from Vite output
WRAPPER="$SCRIPT_DIR/vite-service-wrapper.cjs"
if [[ ! -f "$WRAPPER" ]]; then
    write_fatal "vite-service-wrapper.cjs not found at: $WRAPPER"
fi

# Read config values
SVC_NAME="$(cfg_value ServiceName        mes-ai-rt-client)"
SVC_DISPLAY="$(cfg_value ServiceDisplayName "MES AI $CLIENT_LABEL")"
SVC_DESC="$(cfg_value ServiceDescription "MES AI $CLIENT_LABEL Vite server")"
PORT="$(cfg_value Port "$DEFAULT_PORT")"
BIND_HOST="$(cfg_value BindHost   "0.0.0.0")"
SERVER_URL="$(cfg_value ServerUrl  "http://localhost:8082")"
START_TYPE="$(cfg_value StartType  "auto")"
LOG_DIR="$(cfg_value LogDir       "")"
SVC_USER="$(cfg_value ServiceUser  "$(logname 2>/dev/null || echo "${SUDO_USER:-root}")")"
SVC_GROUP="$(cfg_value ServiceGroup "$SVC_USER")"

[[ -z "$SVC_USER"  ]] && SVC_USER="root"
[[ -z "$SVC_GROUP" ]] && SVC_GROUP="$SVC_USER"

if [[ -z "$LOG_DIR" ]]; then
    LOG_DIR="$CLIENT_DIR/logs"
fi
mkdir -p "$LOG_DIR"
chown -R "$SVC_USER:$SVC_GROUP" "$LOG_DIR" 2>/dev/null || true

# Summary
echo ""
echo "  Client     : $CLIENT_LABEL  ($CLIENT_KEY)"
echo "  Service    : $SVC_NAME"
echo "  Display    : $SVC_DISPLAY"
echo "  URL        : http://${BIND_HOST}:${PORT}"
echo "  MES Server : $SERVER_URL"
echo "  Start Type : $START_TYPE"
echo "  Run as     : $SVC_USER:$SVC_GROUP"
echo "  Log Dir    : $LOG_DIR"
echo "  Node       : $NODE_EXE"
echo "  Vite       : $VITE_BIN"
echo ""

# Tear down existing service if present
EXISTING="$(get_service_status "$SVC_NAME")"
if [[ "$EXISTING" != "not-installed" ]]; then
    write_step "Existing service '$SVC_NAME' found (status: $EXISTING) — removing before reinstall..."
    [[ "$EXISTING" == "running" ]] && systemctl stop "$SVC_NAME" || true
    systemctl disable "$SVC_NAME" 2>/dev/null || true
    rm -f "$(unit_path "$SVC_NAME")"
    systemctl daemon-reload
    write_ok "Old service removed."
fi

# Write systemd unit file
UNIT_FILE="$(unit_path "$SVC_NAME")"
write_step "Writing systemd unit: $UNIT_FILE"

cat > "$UNIT_FILE" <<EOF
[Unit]
Description=$SVC_DISPLAY - $SVC_DESC
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SVC_USER
Group=$SVC_GROUP
WorkingDirectory=$CLIENT_DIR

Environment="MES_SERVER_URL=$SERVER_URL"
Environment="NO_COLOR=1"
Environment="FORCE_COLOR=0"
Environment="TERM=dumb"

ExecStart=$NODE_EXE $WRAPPER $VITE_BIN --host $BIND_HOST --port $PORT

StandardOutput=append:$LOG_DIR/${SVC_NAME}-stdout.log
StandardError=append:$LOG_DIR/${SVC_NAME}-stderr.log

Restart=on-failure
RestartSec=5
TimeoutStopSec=30

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$UNIT_FILE"
systemctl daemon-reload

# Start type → enable/disable behaviour
case "${START_TYPE,,}" in
    auto|delayed-auto)
        systemctl enable "$SVC_NAME" >/dev/null
        write_ok "Service enabled to start on boot."
        ;;
    manual)
        systemctl disable "$SVC_NAME" >/dev/null 2>&1 || true
        write_ok "Service installed (manual start; not enabled on boot)."
        ;;
    disabled)
        systemctl disable "$SVC_NAME" >/dev/null 2>&1 || true
        systemctl mask "$SVC_NAME" >/dev/null 2>&1 || true
        write_warn "Service installed in disabled/masked state."
        ;;
    *)
        systemctl enable "$SVC_NAME" >/dev/null
        write_ok "Service enabled to start on boot (default)."
        ;;
esac

write_ok "Service '$SVC_NAME' installed."
echo ""
echo "  Client URL : http://localhost:${PORT}"
echo "  Logs       : $LOG_DIR"
echo "  Journal    : journalctl -u $SVC_NAME -f"
echo ""
echo "  Start now  : sudo ./run-client-service.sh start  --config \"$CONFIG_FILE\""
echo "  Stop       : sudo ./run-client-service.sh stop   --config \"$CONFIG_FILE\""
echo "  Status     :      ./run-client-service.sh status --config \"$CONFIG_FILE\""
echo "  Uninstall  : sudo ./run-client-service.sh uninstall --config \"$CONFIG_FILE\""
echo ""
