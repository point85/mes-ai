#!/usr/bin/env bash
# run-server.sh — Start the MES AI server with a specified database backend.
# Compatible with bash and zsh.
#
# Usage:
#   ./run-server.sh <Database> [DbName] [options]
#
# Run  ./run-server.sh --help  for full documentation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
VENV_ACTIVATE="$SCRIPT_DIR/.venv/bin/activate"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DATABASE=""
DB_NAME="mes_ai"
DB_SERVER=""
USERNAME=""
PASSWORD=""
UVICORN_PORT=8082
STAMP=false

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
show_help() {
    cat <<'EOF'

USAGE
  ./run-server.sh <Database> [DbName] [options]

ARGUMENTS
  Database             (required)  Database engine (case-insensitive):
                                     PostgreSQL | MSSQL | Oracle
  DbName               (optional)  MES database name.  Default: mes_ai

OPTIONS
  -s, --server HOST[:PORT]  DB host and optional port.
                            Default: localhost with the engine's standard port.
  -u, --username USER       DB username.  Defaults to "postgres" for PostgreSQL.
                            Required for MSSQL and Oracle.
  -p, --password PASS       DB password.  Defaults to "postgres" for PostgreSQL.
      --port PORT            uvicorn port.  Default: 8082
      --stamp               Purge stale Alembic revision and re-stamp to head
                            before running migrations (use after consolidation).
  -h, --help                Show this help message.

SUPPORTED DATABASES
  Engine        Default Port  Async Driver  Example Connection String
  ----------    ------------  ------------  -----------------------------------------------
  PostgreSQL        5432      asyncpg       postgresql+asyncpg://user:pass@host:5432/mes_ai
  MSSQL             1433      pyodbc        mssql+pyodbc://user:pass@host:1433/mes_ai?driver=ODBC+Driver+18+for+SQL+Server
  Oracle            1521      oracledb      oracle+oracledb://user:pass@host:1521/mes_ai

EXAMPLES
  ./run-server.sh PostgreSQL
  ./run-server.sh PostgreSQL mes_ai -u postgres -p secret
  ./run-server.sh MSSQL mes_ai -u sa -p MyPass123 --port 8090
  ./run-server.sh Oracle mes_ai -s oracle-host:1521 -u mes -p oracle

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
        -s|--server)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --server requires a value (HOST or HOST:PORT)." >&2
                exit 1
            fi
            DB_SERVER="$2"
            shift 2
            ;;
        -u|--username)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --username requires a value." >&2
                exit 1
            fi
            USERNAME="$2"
            shift 2
            ;;
        -p|--password)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --password requires a value." >&2
                exit 1
            fi
            PASSWORD="$2"
            shift 2
            ;;
        --port)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --port requires a value." >&2
                exit 1
            fi
            UVICORN_PORT="$2"
            shift 2
            ;;
        --stamp)
            STAMP=true
            shift
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

# Assign positional args: first = Database, second = DbName
if [[ ${#POSITIONAL[@]} -ge 1 ]]; then
    DATABASE="${POSITIONAL[0]}"
fi
if [[ ${#POSITIONAL[@]} -ge 2 ]]; then
    DB_NAME="${POSITIONAL[1]}"
fi

# ---------------------------------------------------------------------------
# Validate database type
# ---------------------------------------------------------------------------
if [[ -z "$DATABASE" ]]; then
    echo "Error: Database argument is required." >&2
    show_help
    exit 1
fi

DB_TYPE_LOWER=$(echo "$DATABASE" | tr '[:upper:]' '[:lower:]')

case "$DB_TYPE_LOWER" in
    postgresql)  DEFAULT_PORT=5432  ;;
    mssql)       DEFAULT_PORT=1433  ;;
    oracle)      DEFAULT_PORT=1521  ;;
    *)
        echo "Error: Unknown database '$DATABASE'." >&2
        echo "Valid options: PostgreSQL, MSSQL, Oracle" >&2
        exit 1
        ;;
esac

# ---------------------------------------------------------------------------
# Resolve host and port from --server
# ---------------------------------------------------------------------------
DB_HOST="localhost"
DB_PORT="$DEFAULT_PORT"

if [[ -n "$DB_SERVER" ]]; then
    # Check for host:port pattern (supports IPv4; for IPv6 use brackets)
    if echo "$DB_SERVER" | grep -qE '^.+:[0-9]+$'; then
        DB_HOST=$(echo "$DB_SERVER" | sed 's/:[0-9]*$//')
        DB_PORT=$(echo "$DB_SERVER" | grep -oE '[0-9]+$')
    else
        DB_HOST="$DB_SERVER"
    fi
fi

# ---------------------------------------------------------------------------
# Credential defaults / validation
# ---------------------------------------------------------------------------
if [[ -z "$USERNAME" ]]; then
    case "$DB_TYPE_LOWER" in
        postgresql)
            USERNAME="postgres"
            PASSWORD="${PASSWORD:-postgres}"
            echo "INFO: No credentials supplied — using PostgreSQL defaults (postgres/postgres)."
            ;;
        *)
            echo "Error: --username is required for $DATABASE." >&2
            exit 1
            ;;
    esac
fi

# ---------------------------------------------------------------------------
# MSSQL: verify ODBC driver is installed
# ---------------------------------------------------------------------------
if [[ "$DB_TYPE_LOWER" == "mssql" ]]; then
    ODBC_DRIVER_NAME=""
    # Check odbcinst.ini (unixODBC)
    if command -v odbcinst &>/dev/null; then
        if odbcinst -q -d | grep -q "ODBC Driver 18 for SQL Server"; then
            ODBC_DRIVER_NAME="ODBC+Driver+18+for+SQL+Server"
        elif odbcinst -q -d | grep -q "ODBC Driver 17 for SQL Server"; then
            echo "INFO: ODBC Driver 17 for SQL Server detected (18 preferred)."
            ODBC_DRIVER_NAME="ODBC+Driver+17+for+SQL+Server"
        fi
    fi
    # Fallback: check /etc/odbcinst.ini directly
    if [[ -z "$ODBC_DRIVER_NAME" ]] && [[ -f /etc/odbcinst.ini ]]; then
        if grep -q "ODBC Driver 18 for SQL Server" /etc/odbcinst.ini; then
            ODBC_DRIVER_NAME="ODBC+Driver+18+for+SQL+Server"
        elif grep -q "ODBC Driver 17 for SQL Server" /etc/odbcinst.ini; then
            echo "INFO: ODBC Driver 17 for SQL Server detected (18 preferred)."
            ODBC_DRIVER_NAME="ODBC+Driver+17+for+SQL+Server"
        fi
    fi
    if [[ -z "$ODBC_DRIVER_NAME" ]]; then
        echo "Error: ODBC Driver for SQL Server not found." >&2
        echo "Install 'ODBC Driver 18 for SQL Server':" >&2
        echo "  https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server" >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Build connection string
# ---------------------------------------------------------------------------
case "$DB_TYPE_LOWER" in
    postgresql)
        CONN_STR="postgresql+asyncpg://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        ;;
    mssql)
        CONN_STR="mssql+pyodbc://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?driver=${ODBC_DRIVER_NAME}"
        ;;
    oracle)
        CONN_STR="oracle+oracledb://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        ;;
esac

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "MES AI Server Startup"
echo "====================="
echo "  Database  : $DATABASE"
echo "  DB Name   : $DB_NAME"
echo "  DB Server : ${DB_HOST}:${DB_PORT}"
echo "  Username  : $USERNAME"
echo "  URL       : $CONN_STR"
echo "  API Port  : $UVICORN_PORT"
echo ""

# ---------------------------------------------------------------------------
# Validate paths
# ---------------------------------------------------------------------------
if [[ ! -f "$VENV_ACTIVATE" ]]; then
    echo "Error: Virtual environment not found at: $VENV_ACTIVATE" >&2
    echo "Create it with:" >&2
    echo "  python3 -m venv .venv" >&2
    echo "  pip install -e server/[dev]" >&2
    exit 1
fi

if [[ ! -d "$SERVER_DIR" ]]; then
    echo "Error: Server directory not found: $SERVER_DIR" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Set environment variables
# ---------------------------------------------------------------------------
export MES_DATABASE_URL="$CONN_STR"
export MES_AUTH_MODE="${MES_AUTH_MODE:-none}"
export MES_LOG_FILE="mes_server_${UVICORN_PORT}.log"

# ---------------------------------------------------------------------------
# Activate virtual environment
# ---------------------------------------------------------------------------
echo "Activating virtual environment..."
# shellcheck disable=SC1090
source "$VENV_ACTIVATE"

# ---------------------------------------------------------------------------
# Check database exists (PostgreSQL / MSSQL; Oracle uses service names)
# ---------------------------------------------------------------------------
echo "Checking database '$DB_NAME' exists on ${DB_HOST}:${DB_PORT}..."
if [[ "$DB_TYPE_LOWER" == "postgresql" ]]; then
    if command -v psql &>/dev/null; then
        db_exists=$(PGPASSWORD="$PASSWORD" psql -U "$USERNAME" -h "$DB_HOST" -p "$DB_PORT" \
            -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" postgres 2>&1)
        if [[ "$db_exists" != "1" ]]; then
            echo "Error: Database '$DB_NAME' does not exist on ${DB_HOST}:${DB_PORT}." >&2
            echo "Create it first:" >&2
            echo "  psql -U $USERNAME -h $DB_HOST -p $DB_PORT -c \"CREATE DATABASE \\\"$DB_NAME\\\";\"" >&2
            exit 1
        fi
    else
        echo "  WARNING: psql not found - skipping database existence check." >&2
    fi
elif [[ "$DB_TYPE_LOWER" == "mssql" ]]; then
    if command -v sqlcmd &>/dev/null; then
        result=$(sqlcmd -S "${DB_HOST},${DB_PORT}" -U "$USERNAME" -P "$PASSWORD" \
            -Q "SET NOCOUNT ON; IF DB_ID('$DB_NAME') IS NULL PRINT 'MISSING'" -h -1 2>&1)
        if echo "$result" | grep -q "MISSING"; then
            echo "Error: Database '$DB_NAME' does not exist on ${DB_HOST}:${DB_PORT}." >&2
            echo "Create it first:" >&2
            echo "  sqlcmd -S ${DB_HOST},${DB_PORT} -U $USERNAME -Q \"CREATE DATABASE [$DB_NAME]\"" >&2
            exit 1
        fi
    else
        echo "  WARNING: sqlcmd not found - skipping database existence check." >&2
    fi
fi

# ---------------------------------------------------------------------------
# Alembic migrations
# ---------------------------------------------------------------------------
echo "Running Alembic migrations..."
cd "$SERVER_DIR"

# Auto-detect a database that has existing application tables but is missing the
# alembic_version tracking table (e.g. after a migration consolidation).  Stamp to
# head so "upgrade head" does not try to re-run already-applied DDL.
# For a truly empty database do NOT stamp — let "upgrade head" run all migrations
# from scratch and create every table.
if [[ "$STAMP" != true && "$DB_TYPE_LOWER" == "postgresql" ]] && command -v psql &>/dev/null; then
    av_exists=$(PGPASSWORD="$PASSWORD" psql -U "$USERNAME" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" \
        -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version'" 2>/dev/null || true)
    table_count=$(PGPASSWORD="$PASSWORD" psql -U "$USERNAME" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" \
        -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo "0")
    has_alembic="$(echo "$av_exists" | tr -d '[:space:]')"
    has_tables="$(echo "$table_count" | tr -d '[:space:]')"
    if [[ "$has_alembic" != "1" && "$has_tables" -gt 0 ]]; then
        echo "  Existing schema without alembic_version detected — stamping to current head before upgrade."
        STAMP=true
    fi
fi

if [[ "$STAMP" == true ]]; then
    echo "  Stamping database to current head (purging stale revision)..."
    alembic stamp head --purge
fi
if ! alembic upgrade head; then
    echo "Error: Alembic migration failed." >&2
    echo "If the database has a stale revision from a prior migration consolidation," >&2
    echo "re-run with --stamp to reset it." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Uvicorn
# ---------------------------------------------------------------------------
echo ""
echo "Starting MES server..."
echo "  Health  : http://localhost:${UVICORN_PORT}/health"
echo "  API     : http://localhost:${UVICORN_PORT}/api/v1/docs"
echo ""
echo "Press Ctrl+C to stop."
echo ""

uvicorn mes.main:app --reload --host 0.0.0.0 --port "$UVICORN_PORT"
