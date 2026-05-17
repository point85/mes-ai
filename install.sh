#!/usr/bin/env bash
# install.sh — Install and configure the MES AI application.
# Compatible with bash 4+ and zsh on Linux and macOS.
#
# Usage:
#   ./install.sh [options]
#
# Run  ./install.sh --help  for full documentation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# ─── Defaults ────────────────────────────────────────────────────────────────
DB_PROVIDER=""
DB_NAME="mes_ai"
DATABASE_URL=""
DB_SERVER="localhost"
DB_USER="postgres"
DB_PASSWORD="postgres"
SKIP_CLIENTS=false
SKIP_MIGRATIONS=false

# ─── Help ─────────────────────────────────────────────────────────────────────
show_help() {
    cat <<'EOF'

USAGE
  ./install.sh [options]

OPTIONS
    --db-provider  PROVIDER     Required: PostgreSQL | MSSQL | Oracle
    --db-name      NAME         Database name.              Default: mes_ai
    --database-url URL          Full SQLAlchemy URL.        Skips DB auto-create.
    --db-server    HOST[:PORT]  Database host/port.         Default: localhost
    --db-user      USER         Database username.          Default: postgres for PostgreSQL
    --db-password  PASS         Database password.          Default: postgres for PostgreSQL
  --skip-clients              Skip npm install for browser clients.
  --skip-migrations           Skip Alembic schema migrations.
  -h, --help                  Show this message.

STEPS PERFORMED
   1. Verify Python 3.12+ (install via apt/brew/dnf if missing)
   2. Verify Node.js 20+  (install via apt/brew/dnf if missing, unless --skip-clients)
   3. Create Python virtual environment     (.venv/)
   4. Install Python server dependencies    (pip install -e ".[dev]")
   5. Create server/.env configuration      (skipped if already present)
     6. Prepare database                      (auto-create for PostgreSQL only)
   7. Run Alembic schema migrations         (skipped with --skip-migrations)
   8. Install npm dependencies              (clients/*, skipped with --skip-clients)

  To install PostgreSQL first:  ./install-postgresql.sh

EXAMPLES
    ./install.sh --db-provider PostgreSQL
    ./install.sh --db-provider PostgreSQL --db-name my_mes --db-password secret
    ./install.sh --db-provider MSSQL --db-server sql-host:1433 --db-user sa --db-password secret
    ./install.sh --db-provider Oracle --database-url oracle+oracledb://mes:secret@oracle-host:1521/mes_ai

EOF
}

# ─── Argument parsing ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-provider)       DB_PROVIDER="$2"; shift ;;
        --db-name)           DB_NAME="$2";     shift ;;
        --database-url)      DATABASE_URL="$2"; shift ;;
        --db-server)         DB_SERVER="$2";   shift ;;
        --db-user)           DB_USER="$2";     shift ;;
        --db-password)       DB_PASSWORD="$2"; shift ;;
        --skip-clients)      SKIP_CLIENTS=true ;;
        --skip-migrations)   SKIP_MIGRATIONS=true ;;
        -h|--help)           show_help; exit 0 ;;
        *) echo "Unknown option: $1"; show_help; exit 1 ;;
    esac
    shift
done

if [[ -z "$DB_PROVIDER" ]]; then
    echo "Error: --db-provider is required. Choose PostgreSQL, MSSQL, or Oracle." >&2
    show_help
    exit 1
fi

# ─── Output helpers ───────────────────────────────────────────────────────────
step() { echo; echo "==> $1"; }
ok()   { echo "    OK   $1"; }
warn() { echo "    WARN $1"; }
skip() { echo "    --   $1"; }
fail() { echo; echo "ERROR: $1" >&2; exit 1; }

ensure_macos_postgres_role() {
    if [[ "$OS" != "macos" || "$DB_TYPE_LOWER" != "postgresql" || -n "$DATABASE_URL" || "$DB_USER" != "postgres" ]]; then
        return 0
    fi

    if ! command -v psql &>/dev/null; then
        fail "psql is required to verify the PostgreSQL role on macOS. Ensure PostgreSQL is installed and on PATH."
    fi

    if psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = 'postgres'" 2>/dev/null | grep -q 1; then
        ok "PostgreSQL role 'postgres' already exists."
    else
        warn "Homebrew PostgreSQL typically creates a superuser matching your macOS account, not 'postgres'."
        warn "Creating a 'postgres' role so the MES AI installer can use the default PostgreSQL settings."

        psql postgres -v mes_ai_pwd="$DB_PASSWORD" -c "CREATE ROLE postgres WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD :'mes_ai_pwd';" >/dev/null
        ok "Created PostgreSQL role 'postgres'."
    fi
}

check_mssql_odbc_driver() {
    local driver_name=""

    if command -v odbcinst &>/dev/null; then
        if odbcinst -q -d | grep -q "ODBC Driver 18 for SQL Server"; then
            driver_name="ODBC Driver 18 for SQL Server"
        elif odbcinst -q -d | grep -q "ODBC Driver 17 for SQL Server"; then
            driver_name="ODBC Driver 17 for SQL Server"
        fi
    fi

    if [[ -z "$driver_name" ]] && [[ -f /etc/odbcinst.ini ]]; then
        if grep -q "ODBC Driver 18 for SQL Server" /etc/odbcinst.ini; then
            driver_name="ODBC Driver 18 for SQL Server"
        elif grep -q "ODBC Driver 17 for SQL Server" /etc/odbcinst.ini; then
            driver_name="ODBC Driver 17 for SQL Server"
        fi
    fi

    if [[ -z "$driver_name" ]]; then
        fail "ODBC Driver for SQL Server not found.
Install 'ODBC Driver 18 for SQL Server' before running migrations:
  https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server"
    fi

    if [[ "$driver_name" == "ODBC Driver 18 for SQL Server" ]]; then
        ok "ODBC Driver 18 for SQL Server detected."
    else
        warn "ODBC Driver 17 for SQL Server detected. Driver 18 is preferred."
    fi
}

check_oracle_client_availability() {
    local oracle_check
    oracle_check=$("$VENV_PYTHON" - <<'PYEOF'
import json, os, sys

try:
    import oracledb
except Exception as exc:
    print(json.dumps({"status": "import_error", "error": str(exc)}))
    sys.exit(0)

client_hints = []
for env_name in ("PATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
    for part in os.environ.get(env_name, "").split(os.pathsep):
        if part and any(token in part.lower() for token in ("oracle", "instantclient")):
            client_hints.append(part)

client_hints = sorted(set(client_hints))

print(json.dumps({
    "status": "ok",
    "version": getattr(oracledb, "__version__", "unknown"),
    "thin_mode": bool(oracledb.is_thin_mode()),
    "client_hints": client_hints,
}))
PYEOF
)

    if [[ -z "$oracle_check" ]]; then
        fail "Oracle driver check returned no output. Verify the .venv was created correctly."
    fi

    local status
    status=$(printf '%s' "$oracle_check" | "$VENV_PYTHON" -c "import json,sys; print(json.load(sys.stdin)['status'])")

    if [[ "$status" != "ok" ]]; then
        local error_text
        error_text=$(printf '%s' "$oracle_check" | "$VENV_PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('error','unknown error'))")
        fail "Python 'oracledb' driver is not available in the virtual environment.
Reinstall Python dependencies or inspect the install output.
Details: ${error_text}"
    fi

    local version thin_mode hint_count
    version=$(printf '%s' "$oracle_check" | "$VENV_PYTHON" -c "import json,sys; print(json.load(sys.stdin)['version'])")
    thin_mode=$(printf '%s' "$oracle_check" | "$VENV_PYTHON" -c "import json,sys; print('true' if json.load(sys.stdin)['thin_mode'] else 'false')")
    hint_count=$(printf '%s' "$oracle_check" | "$VENV_PYTHON" -c "import json,sys; print(len(json.load(sys.stdin)['client_hints']))")

    ok "Oracle Python driver detected: version ${version}."
    if [[ "$hint_count" -gt 0 ]]; then
        ok "Oracle client libraries appear to be available."
    elif [[ "$thin_mode" == "true" ]]; then
        warn "Oracle client libraries were not detected on PATH/LD_LIBRARY_PATH. oracledb thin mode will be used."
    else
        fail "Oracle client libraries were not detected and thin mode is unavailable.
Install Oracle Instant Client or configure the Oracle client library path before running migrations."
    fi
}

# ─── OS detection ─────────────────────────────────────────────────────────────
detect_os() {
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]] || [[ -f /etc/fedora-release ]]; then
        echo "rhel"
    else
        echo "unknown"
    fi
}

OS="$(detect_os)"

# ─── Resolve DB host / port ───────────────────────────────────────────────────
DB_TYPE_LOWER=$(echo "$DB_PROVIDER" | tr '[:upper:]' '[:lower:]')

case "$DB_TYPE_LOWER" in
    postgresql) DEFAULT_DB_PORT=5432 ;;
    mssql)      DEFAULT_DB_PORT=1433 ;;
    oracle)     DEFAULT_DB_PORT=1521 ;;
    *)
        echo "Error: Unknown db provider '$DB_PROVIDER'. Valid options: PostgreSQL, MSSQL, Oracle." >&2
        exit 1
        ;;
esac

DB_HOST="localhost"
DB_PORT=$DEFAULT_DB_PORT

if [[ "$DB_SERVER" =~ ^(.+):([0-9]+)$ ]]; then
    DB_HOST="${BASH_REMATCH[1]}"
    DB_PORT="${BASH_REMATCH[2]}"
elif [[ -n "$DB_SERVER" ]]; then
    DB_HOST="$DB_SERVER"
fi

if [[ -n "$DATABASE_URL" ]]; then
    DB_URL="$DATABASE_URL"
else
    case "$DB_TYPE_LOWER" in
        postgresql)
            DB_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
            ;;
        mssql)
            DB_URL="mssql+pyodbc://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server"
            ;;
        oracle)
            DB_URL="oracle+oracledb://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
            ;;
    esac
fi

# ─── Step 1: Python 3.12+ ─────────────────────────────────────────────────────
step "Step 1/8 — Checking Python 3.12+"

PYTHON_CMD=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver_str=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        major=$(echo "$ver_str" | cut -d. -f1)
        minor=$(echo "$ver_str" | cut -d. -f2)
        if [[ "$major" -eq 3 && "$minor" -ge 12 ]]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    warn "Python 3.12+ not found. Attempting installation..."
    case "$OS" in
        macos)
            if command -v brew &>/dev/null; then
                brew install python@3.12
                PYTHON_CMD="python3.12"
            else
                fail "Homebrew not found. Install Python 3.12+ from https://www.python.org/downloads/
  or install Homebrew first: https://brew.sh"
            fi
            ;;
        debian)
            sudo apt-get update -q
            sudo apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip
            PYTHON_CMD="python3.12"
            ;;
        rhel)
            sudo dnf install -y python3.12
            PYTHON_CMD="python3.12"
            ;;
        *)
            fail "Cannot auto-install Python on this OS.
Install Python 3.12+ from https://www.python.org/downloads/ then rerun."
            ;;
    esac
fi

ok "Found: $($PYTHON_CMD --version 2>&1)"

# ─── Step 2: Node.js 20+ ──────────────────────────────────────────────────────
if [[ "$SKIP_CLIENTS" == "false" ]]; then
    step "Step 2/8 — Checking Node.js 20+"

    NODE_OK=false
    if command -v node &>/dev/null; then
        node_major=$(node --version 2>&1 | grep -oE '[0-9]+' | head -1)
        [[ "$node_major" -ge 20 ]] && NODE_OK=true
    fi

    if [[ "$NODE_OK" == "false" ]]; then
        warn "Node.js 20+ not found. Attempting installation..."
        case "$OS" in
            macos)
                if command -v brew &>/dev/null; then
                    brew install node
                else
                    fail "Homebrew not found. Install Node.js 20+ from https://nodejs.org, or rerun with --skip-clients."
                fi
                ;;
            debian)
                # NodeSource LTS (Node 20+)
                curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
                sudo apt-get install -y nodejs
                ;;
            rhel)
                curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
                sudo dnf install -y nodejs
                ;;
            *)
                fail "Cannot auto-install Node.js on this OS.
Install Node.js 20+ from https://nodejs.org, or rerun with --skip-clients."
                ;;
        esac
        ok "Node.js installed: $(node --version)"
    else
        ok "Found: $(node --version)"
    fi
else
    skip "Step 2 skipped (--skip-clients)"
fi

# ─── Step 3: Python virtual environment ─────────────────────────────────────────────
step "Step 3/8 — Python virtual environment (.venv)"

if [[ -d "$VENV_DIR" ]]; then
    ok "Virtual environment already exists at .venv/"
else
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    ok "Created .venv/"
fi
# ─── Step 4: Python dependencies ────────────────────────────────────────────────
step "Step 4/8 — Installing Python server dependencies"

pushd "$SERVER_DIR" > /dev/null
"$VENV_PIP" install --upgrade pip --quiet
"$VENV_PIP" install -e ".[dev]" --quiet
popd > /dev/null

ok "Python packages installed (mes-ai + dev extras)."

if [[ "$DB_TYPE_LOWER" == "postgresql" ]]; then
    step "Step 4/8 - Checking PostgreSQL role prerequisites"
    ensure_macos_postgres_role
fi

# ─── Step 5: server/.env ──────────────────────────────────────────────────────
step "Step 5/8 — Creating server/.env configuration"

ENV_FILE="$SERVER_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
    ok "server/.env already exists — skipping. Edit it to change settings."
else
    # Generate a cryptographically random 32-byte secret key
    if command -v openssl &>/dev/null; then
        SECRET_KEY="$(openssl rand -base64 32)"
    else
        SECRET_KEY="$("$VENV_PYTHON" -c \
            "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())")"
    fi

    cat > "$ENV_FILE" <<EOF
# MES AI server configuration - generated by install.sh
# Edit this file to adjust settings before starting the server.

# -- Database ---------------------------------------------------------------
MES_DATABASE_URL=${DB_URL}

# -- Authentication ---------------------------------------------------------
# none  = no authentication (development / evaluation)
# local = built-in username/password authentication
# oidc  = external OpenID Connect identity provider
MES_AUTH_MODE=none

# WARNING: replace with a strong random value before any production use.
MES_SECRET_KEY=${SECRET_KEY}

# -- Logging ----------------------------------------------------------------
# DEBUG | INFO | WARNING | ERROR | CRITICAL
MES_LOG_LEVEL=INFO

# -- Event bus --------------------------------------------------------------
# memory = in-process (single server)
# redis  = distributed (requires Redis, set MES_REDIS_URL)
MES_EVENT_BUS_TYPE=memory
EOF

    ok "Created server/.env"
fi

# ─── Step 6: Create database ────────────────────────────────────────────────────
if [[ -n "$DATABASE_URL" ]]; then
    skip "Step 6 skipped (--database-url supplied; ensure the database already exists)"
elif [[ "$DB_TYPE_LOWER" != "postgresql" ]]; then
    skip "Step 6 skipped (--db-provider ${DB_PROVIDER} requires manual database creation)"
    warn "Automatic database creation is only implemented for PostgreSQL."
    warn "Ensure database '${DB_NAME}' already exists on ${DB_PROVIDER} before migrations run."
else
    step "Step 6/8 — Creating PostgreSQL database '${DB_NAME}'"

    # Pass credentials via environment variables so the Python script
    # (written as a single-quoted heredoc) never sees shell expansions.
    CREATE_DB_OUTPUT=$(
        _MES_INST_HOST="$DB_HOST"   \
        _MES_INST_PORT="$DB_PORT"   \
        _MES_INST_USER="$DB_USER"   \
        _MES_INST_PASS="$DB_PASSWORD" \
        _MES_INST_DBNAME="$DB_NAME"  \
        "$VENV_PYTHON" - <<'PYEOF'
import asyncio, sys, os
import asyncpg

async def main():
    host    = os.environ["_MES_INST_HOST"]
    port    = int(os.environ["_MES_INST_PORT"])
    user    = os.environ["_MES_INST_USER"]
    password = os.environ["_MES_INST_PASS"]
    db_name  = os.environ["_MES_INST_DBNAME"]

    try:
        conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password,
            database="postgres"
        )
    except Exception as e:
        print(f"CONNECT_ERROR:{e}", file=sys.stderr)
        sys.exit(1)

    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if exists:
            print("EXISTS")
        else:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print("CREATED")
    finally:
        await conn.close()

asyncio.run(main())
PYEOF
) || true

    if echo "$CREATE_DB_OUTPUT" | grep -q "CONNECT_ERROR"; then
        warn "Could not connect to PostgreSQL at ${DB_HOST}:${DB_PORT}."
        warn "Details: $(echo "$CREATE_DB_OUTPUT" | sed 's/CONNECT_ERROR://')"
        warn ""
        warn "Ensure PostgreSQL is running and credentials are correct, then create"
        warn "the database manually:  CREATE DATABASE \"${DB_NAME}\";"
        warn ""
        warn "Rerun the installer once PostgreSQL is accessible, or start the server"
        warn "with:  ./run-server.sh PostgreSQL ${DB_NAME} -u ${DB_USER}"
    elif echo "$CREATE_DB_OUTPUT" | grep -q "EXISTS"; then
        ok "Database '${DB_NAME}' already exists."
    elif echo "$CREATE_DB_OUTPUT" | grep -q "CREATED"; then
        ok "Database '${DB_NAME}' created."
    else
        warn "Unexpected output: $CREATE_DB_OUTPUT"
    fi
fi

# ─── Step 8: Alembic migrations ───────────────────────────────────────────────
if [[ "$SKIP_MIGRATIONS" == "true" ]]; then
    skip "Step 7 skipped (--skip-migrations)"
else
    step "Step 7/8 — Checking database driver prerequisites"

    case "$DB_TYPE_LOWER" in
        mssql)
            check_mssql_odbc_driver
            ;;
        oracle)
            check_oracle_client_availability
            ;;
        *)
            ok "No additional database driver prerequisites required for ${DB_PROVIDER}."
            ;;
    esac

    step "Step 7/8 — Running Alembic schema migrations"

    pushd "$SERVER_DIR" > /dev/null
    MES_DATABASE_URL="$DB_URL" \
        "$VENV_PYTHON" -m alembic upgrade head
    popd > /dev/null

    ok "Schema migrations applied."
fi

# ─── Step 9: npm dependencies ────────────────────────────────────────────────
if [[ "$SKIP_CLIENTS" == "false" ]]; then
    step "Step 8/8 — Installing npm dependencies for browser clients"

    declare -a CLIENT_NAMES=("Design-Time client" "Run-Time client" "ERP Simulator" "Equipment Simulator")
    declare -a CLIENT_DIRS=("clients/design_time" "clients/run_time" "clients/erp_simulator" "clients/equipment_simulator")

    for i in "${!CLIENT_NAMES[@]}"; do
        name="${CLIENT_NAMES[$i]}"
        dir="$SCRIPT_DIR/${CLIENT_DIRS[$i]}"
        if [[ -f "$dir/package.json" ]]; then
            echo "    Installing $name..."
            pushd "$dir" > /dev/null
            npm install --silent
            popd > /dev/null
            ok "$name ready."
        else
            warn "$name: package.json not found at $dir — skipped."
        fi
    done
else
    skip "Step 8 skipped (--skip-clients)"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
cat <<EOF

================================================================
  MES AI installation complete!
================================================================

  Start the MES server:
        ./run-server.sh ${DB_PROVIDER} ${DB_NAME} -u ${DB_USER}

  Start a client (open in a separate terminal):
    ./run-client.sh dt-client           # Design-Time (port 5173)
    ./run-client.sh rt-client           # Run-Time    (port 5176)
    ./run-client.sh erp-sim             # ERP Sim     (port 5174)
    ./run-client.sh equipment-sim       # Equip Sim   (port 5175)

  Configuration file:  server/.env
  Documentation:       README.md
================================================================
EOF

