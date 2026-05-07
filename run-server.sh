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

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
show_help() {
    cat <<'EOF'

USAGE
  ./run-server.sh <Database> [DbName] [options]

ARGUMENTS
  Database             (required)  Database engine (case-insensitive):
                                     PostgreSQL | MySQL | SQLite | MSSQL
                                     Oracle | CockroachDB | DB2
  DbName               (optional)  MES database name.  Default: mes_ai

OPTIONS
  -s, --server HOST[:PORT]  DB host and optional port.
                            Default: localhost with the engine's standard port.
  -u, --username USER       DB username.  Defaults to "postgres" for PostgreSQL,
                            "root" for CockroachDB.
                            Required for MySQL, MSSQL, Oracle, DB2.
  -p, --password PASS       DB password.  Defaults to "postgres" for PostgreSQL.
      --port PORT            uvicorn port.  Default: 8082
  -h, --help                Show this help message.

SUPPORTED DATABASES
  Engine        Default Port  Async Driver  Example Connection String
  ----------    ------------  ------------  -----------------------------------------------
  PostgreSQL        5432      asyncpg       postgresql+asyncpg://user:pass@host:5432/mes_ai
  MySQL             3306      aiomysql      mysql+aiomysql://user:pass@host:3306/mes_ai
  SQLite             N/A      aiosqlite     sqlite+aiosqlite:///./mes_ai.db
  MSSQL             1433      pyodbc        mssql+pyodbc://user:pass@host:1433/mes_ai?driver=ODBC+Driver+18+for+SQL+Server
  Oracle            1521      oracledb      oracle+oracledb://user:pass@host:1521/mes_ai
  CockroachDB      26257      asyncpg       cockroachdb+asyncpg://user:pass@host:26257/mes_ai
  DB2              50000      ibm_db        db2+ibm_db://user:pass@host:50000/mes_ai

EXAMPLES
  ./run-server.sh PostgreSQL
  ./run-server.sh PostgreSQL mes_ai -u postgres -p secret
  ./run-server.sh MySQL mes_ai -s db.example.com:3306 -u root -p pass
  ./run-server.sh SQLite
  ./run-server.sh SQLite -n test_mes --port 8092
  ./run-server.sh MSSQL mes_ai -u sa -p MyPass123 --port 8090
  ./run-server.sh Oracle mes_ai -s oracle-host:1521 -u mes -p oracle
  ./run-server.sh CockroachDB mes_ai -u root
  ./run-server.sh DB2 mes_ai -s db2-host:50000 -u db2inst1 -p pass

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
    mysql)       DEFAULT_PORT=3306  ;;
    sqlite)      DEFAULT_PORT=0     ;;
    mssql)       DEFAULT_PORT=1433  ;;
    oracle)      DEFAULT_PORT=1521  ;;
    cockroachdb) DEFAULT_PORT=26257 ;;
    db2)         DEFAULT_PORT=50000 ;;
    *)
        echo "Error: Unknown database '$DATABASE'." >&2
        echo "Valid options: PostgreSQL, MySQL, SQLite, MSSQL, Oracle, CockroachDB, DB2" >&2
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
if [[ "$DB_TYPE_LOWER" != "sqlite" ]]; then
    if [[ -z "$USERNAME" ]]; then
        case "$DB_TYPE_LOWER" in
            postgresql)
                USERNAME="postgres"
                PASSWORD="${PASSWORD:-postgres}"
                echo "INFO: No credentials supplied — using PostgreSQL defaults (postgres/postgres)."
                ;;
            cockroachdb)
                USERNAME="root"
                echo "INFO: No username supplied — using CockroachDB default (root)."
                ;;
            *)
                echo "Error: --username is required for $DATABASE." >&2
                exit 1
                ;;
        esac
    fi
fi

# ---------------------------------------------------------------------------
# Build connection string
# ---------------------------------------------------------------------------
case "$DB_TYPE_LOWER" in
    postgresql)
        CONN_STR="postgresql+asyncpg://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        ;;
    mysql)
        CONN_STR="mysql+aiomysql://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        ;;
    sqlite)
        CONN_STR="sqlite+aiosqlite:///./${DB_NAME}.db"
        ;;
    mssql)
        CONN_STR="mssql+pyodbc://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server"
        ;;
    oracle)
        CONN_STR="oracle+oracledb://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        ;;
    cockroachdb)
        CONN_STR="cockroachdb+asyncpg://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        ;;
    db2)
        CONN_STR="db2+ibm_db://${USERNAME}:${PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
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
if [[ "$DB_TYPE_LOWER" != "sqlite" ]]; then
    echo "  DB Server : ${DB_HOST}:${DB_PORT}"
    echo "  Username  : $USERNAME"
fi
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
export DATABASE_URL="$CONN_STR"
export MES_AUTH_MODE="${MES_AUTH_MODE:-none}"

# ---------------------------------------------------------------------------
# Activate virtual environment
# ---------------------------------------------------------------------------
echo "Activating virtual environment..."
# shellcheck disable=SC1090
source "$VENV_ACTIVATE"

# ---------------------------------------------------------------------------
# Alembic migrations
# ---------------------------------------------------------------------------
echo "Running Alembic migrations..."
cd "$SERVER_DIR"
alembic upgrade head

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
