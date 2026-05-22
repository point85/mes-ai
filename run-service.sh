#!/usr/bin/env bash
# run-service.sh — Manage the MES AI server as a systemd service.
#
# Installs, uninstalls, starts, stops, restarts, or queries the status of
# the MES AI uvicorn server as a systemd unit. All runtime parameters are
# read from a configuration file so that no credentials appear on the
# command line or in process lists.
#
# Usage:
#   ./run-service.sh <action> [--config <path>] [--run-migrations]
#
# Run  ./run-service.sh  with no arguments for full help.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
VENV_ALEMBIC="$SCRIPT_DIR/.venv/bin/alembic"

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
  ./run-service.sh <action> [--config <path>] [--run-migrations]

ACTIONS
  install    Register and configure the MES AI systemd service (requires root/sudo)
  uninstall  Remove the systemd service (requires root/sudo)
  start      Start the service (requires root/sudo)
  stop       Stop the service (requires root/sudo)
  restart    Restart the service (requires root/sudo)
  status     Show current service status

OPTIONS
  --config <path>     Path to config file (default: mes-service.conf)
  --run-migrations    Run 'alembic upgrade head' before starting/installing

EXAMPLES
  sudo ./run-service.sh install --run-migrations
  sudo ./run-service.sh install --config /etc/mes/prod.conf --run-migrations
  sudo ./run-service.sh start
  ./run-service.sh status
  sudo ./run-service.sh uninstall

  See mes-service.conf.example for all available configuration keys.

EOF
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
ACTION=""
CONFIG_FILE=""
RUN_MIGRATIONS=false

if [[ $# -eq 0 ]]; then
    echo ""
    echo "${C_WHITE}MES AI Service Manager${C_RESET}"
    echo "${C_WHITE}======================${C_RESET}"
    show_help
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        install|uninstall|start|stop|restart|status)
            ACTION="$1"
            shift
            ;;
        --config|-c)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --run-migrations|-m)
            RUN_MIGRATIONS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "${C_RED}ERROR: Unknown argument: $1${C_RESET}" >&2
            echo "Run ./run-service.sh with no arguments to see usage."
            exit 1
            ;;
    esac
done

if [[ -z "$ACTION" ]]; then
    show_help
    exit 0
fi

if [[ -z "$CONFIG_FILE" ]]; then
    CONFIG_FILE="$SCRIPT_DIR/mes-service.conf"
fi

# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------
declare -A CFG=()
read_config() {
    local path="$1"
    if [[ ! -f "$path" ]]; then
        write_fatal "Configuration file not found: $path
Copy mes-service.conf.example to mes-service.conf and edit it."
    fi
    local lineno=0 line trimmed key value
    while IFS= read -r line || [[ -n "$line" ]]; do
        lineno=$((lineno + 1))
        trimmed="${line#"${line%%[![:space:]]*}"}"   # ltrim
        trimmed="${trimmed%"${trimmed##*[![:space:]]}"}" # rtrim
        [[ -z "$trimmed" ]] && continue
        [[ "$trimmed" == \#* ]] && continue
        if [[ ! "$trimmed" =~ ^([A-Za-z][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
            write_warn "Ignoring unrecognised line $lineno in $path: $line"
            continue
        fi
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        # rtrim value
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
# Connection-string builder
# ---------------------------------------------------------------------------
build_connection_string() {
    local db_type host port user pass dbname conn
    db_type="$(cfg_value Database PostgreSQL)"
    dbname="$(cfg_value DbName mes_ai)"
    host="$(cfg_value DbServer localhost)"
    user="$(cfg_value Username)"
    pass="$(cfg_value Password)"

    case "${db_type,,}" in
        postgresql|postgres)
            db_type="postgresql"
            [[ "$host" == *:* ]] || host="${host}:5432"
            [[ -z "$user" ]] && user="postgres"
            [[ -z "$pass" ]] && pass="postgres"
            conn="postgresql+asyncpg://${user}:${pass}@${host}/${dbname}"
            ;;
        mssql|sqlserver)
            db_type="mssql"
            [[ "$host" == *:* ]] || host="${host}:1433"
            [[ -z "$user" ]] && write_fatal "Username is required for MSSQL"
            [[ -z "$pass" ]] && write_fatal "Password is required for MSSQL"
            conn="mssql+pyodbc://${user}:${pass}@${host}/${dbname}?driver=ODBC+Driver+18+for+SQL+Server"
            ;;
        oracle)
            db_type="oracle"
            [[ "$host" == *:* ]] || host="${host}:1521"
            [[ -z "$user" ]] && write_fatal "Username is required for Oracle"
            [[ -z "$pass" ]] && write_fatal "Password is required for Oracle"
            conn="oracle+oracledb://${user}:${pass}@${host}/${dbname}"
            ;;
        *)
            write_fatal "Unsupported Database value: $db_type (use PostgreSQL, MSSQL, or Oracle)"
            ;;
    esac
    echo "$db_type|$conn"
}

# ---------------------------------------------------------------------------
# Alembic migrations
# ---------------------------------------------------------------------------
invoke_migrations() {
    local conn_url="$1"
    if [[ ! -x "$VENV_ALEMBIC" ]]; then
        write_fatal "Alembic not found at: $VENV_ALEMBIC
Run ./install.sh first to create the virtual environment."
    fi
    write_step "Running Alembic migrations (alembic upgrade head)..."
    (
        cd "$SERVER_DIR"
        MES_DATABASE_URL="$conn_url" "$VENV_ALEMBIC" upgrade head
    ) || write_fatal "Alembic migration failed.
Fix the schema issue, then re-run without --run-migrations."
    write_ok "Migrations applied."
}

# ---------------------------------------------------------------------------
# systemd helpers
# ---------------------------------------------------------------------------
assert_root() {
    if [[ $EUID -ne 0 ]]; then
        write_fatal "This action requires root privileges. Re-run with sudo."
    fi
}

require_systemd() {
    if ! command -v systemctl >/dev/null 2>&1; then
        write_fatal "systemctl not found. This script requires a systemd-based Linux distribution."
    fi
}

unit_path() {
    echo "/etc/systemd/system/$1.service"
}

get_service_status() {
    local name="$1"
    if [[ ! -f "$(unit_path "$name")" ]]; then
        echo "not-installed"
        return
    fi
    local state
    state="$(systemctl is-active "$name" 2>/dev/null || true)"
    case "$state" in
        active)     echo "running" ;;
        inactive)   echo "stopped" ;;
        failed)     echo "failed" ;;
        activating) echo "starting" ;;
        deactivating) echo "stopping" ;;
        *)          echo "${state:-unknown}" ;;
    esac
}

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
echo ""
echo "${C_WHITE}MES AI Service Manager${C_RESET}"
echo "${C_WHITE}======================${C_RESET}"

require_systemd

# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------
if [[ "$ACTION" == "status" ]]; then
    read_config "$CONFIG_FILE"
    NAME="$(cfg_value ServiceName mes-ai)"
    STATUS="$(get_service_status "$NAME")"
    case "$STATUS" in
        running)        COLOUR="$C_GREEN" ;;
        not-installed)  COLOUR="$C_YELLOW" ;;
        *)              COLOUR="$C_RED" ;;
    esac
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
    NAME="$(cfg_value ServiceName mes-ai)"
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
    NAME="$(cfg_value ServiceName mes-ai)"
    STATUS="$(get_service_status "$NAME")"
    if [[ "$STATUS" == "not-installed" ]]; then
        write_fatal "Service '$NAME' is not installed.  Run: sudo ./run-service.sh install"
    fi
    if [[ "$STATUS" == "running" ]]; then
        write_warn "Service '$NAME' is already running."; exit 0
    fi
    if $RUN_MIGRATIONS; then
        DB_INFO="$(build_connection_string)"; CONN_URL="${DB_INFO#*|}"
        invoke_migrations "$CONN_URL"
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
    NAME="$(cfg_value ServiceName mes-ai)"
    if [[ "$(get_service_status "$NAME")" == "not-installed" ]]; then
        write_fatal "Service '$NAME' is not installed.  Run: sudo ./run-service.sh install"
    fi
    if $RUN_MIGRATIONS; then
        DB_INFO="$(build_connection_string)"; CONN_URL="${DB_INFO#*|}"
        invoke_migrations "$CONN_URL"
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
    NAME="$(cfg_value ServiceName mes-ai)"
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

# Validate required tools
if [[ ! -x "$VENV_PYTHON" ]]; then
    write_fatal "Python virtual environment not found at: $VENV_PYTHON
Run ./install.sh first."
fi
if [[ ! -d "$SERVER_DIR" ]]; then
    write_fatal "Server directory not found: $SERVER_DIR"
fi

SVC_NAME="$(cfg_value ServiceName        mes-ai)"
SVC_DISPLAY="$(cfg_value ServiceDisplayName "MES AI Server")"
SVC_DESC="$(cfg_value ServiceDescription "MES AI Manufacturing Execution System Server")"
PORT="$(cfg_value UvicornPort 8082)"
WORKERS="$(cfg_value Workers   4)"
AUTH_MODE="$(cfg_value AuthMode none)"
START_TYPE="$(cfg_value StartType auto)"
LOG_DIR="$(cfg_value LogDir "")"
SVC_USER="$(cfg_value ServiceUser "$(logname 2>/dev/null || echo "$SUDO_USER")")"
SVC_GROUP="$(cfg_value ServiceGroup "$SVC_USER")"

[[ -z "$SVC_USER" ]] && SVC_USER="root"
[[ -z "$SVC_GROUP" ]] && SVC_GROUP="$SVC_USER"

# Connection string
DB_INFO="$(build_connection_string)"
DB_TYPE="${DB_INFO%%|*}"
CONN_URL="${DB_INFO#*|}"

# Log directory
if [[ -z "$LOG_DIR" ]]; then
    LOG_DIR="$SERVER_DIR/logs"
fi
mkdir -p "$LOG_DIR"
chown -R "$SVC_USER:$SVC_GROUP" "$LOG_DIR" 2>/dev/null || true

# Migrations
if $RUN_MIGRATIONS; then
    invoke_migrations "$CONN_URL"
fi

# Summary
MASKED_URL="$(echo "$CONN_URL" | sed -E 's#(://[^:]+:)[^@]+(@)#\1****\2#')"
echo ""
echo "  Service   : $SVC_NAME"
echo "  Display   : $SVC_DISPLAY"
echo "  Database  : $DB_TYPE  ($MASKED_URL)"
echo "  Port      : $PORT"
echo "  Workers   : $WORKERS"
echo "  Auth Mode : $AUTH_MODE"
echo "  Start Type: $START_TYPE"
echo "  Run as    : $SVC_USER:$SVC_GROUP"
echo "  Log Dir   : $LOG_DIR"
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
WorkingDirectory=$SERVER_DIR

Environment="MES_DATABASE_URL=$CONN_URL"
Environment="MES_AUTH_MODE=$AUTH_MODE"
Environment="MES_LOG_FILE=mes_server_${PORT}.log"

ExecStart=$VENV_PYTHON -m uvicorn mes.main:app --host 0.0.0.0 --port $PORT --workers $WORKERS

StandardOutput=append:$LOG_DIR/${SVC_NAME}-stdout.log
StandardError=append:$LOG_DIR/${SVC_NAME}-stderr.log

Restart=on-failure
RestartSec=5
TimeoutStopSec=30

# Hardening (relax if your environment needs it)
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
echo "  Health check : http://localhost:${PORT}/health"
echo "  API docs     : http://localhost:${PORT}/api/v1/docs"
echo "  Logs         : $LOG_DIR"
echo "  Journal      : journalctl -u $SVC_NAME -f"
echo ""
echo "  Start now    : sudo ./run-service.sh start  --config \"$CONFIG_FILE\""
echo "  Stop         : sudo ./run-service.sh stop   --config \"$CONFIG_FILE\""
echo "  Status       :      ./run-service.sh status --config \"$CONFIG_FILE\""
echo "  Uninstall    : sudo ./run-service.sh uninstall --config \"$CONFIG_FILE\""
echo ""
