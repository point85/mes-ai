#!/usr/bin/env bash
# install-postgresql.sh — Install PostgreSQL on Linux or macOS.
# Compatible with bash 4+ and zsh.
#
# Usage:
#   ./install-postgresql.sh
#
# Run  ./install-postgresql.sh --help  for full documentation.

set -euo pipefail

# ─── Help ─────────────────────────────────────────────────────────────────────
show_help() {
    cat <<'EOF'

USAGE
  ./install-postgresql.sh

OPTIONS
  -h, --help    Show this message.

DESCRIPTION
  Installs PostgreSQL via the system package manager (apt, dnf, or brew) if it
  is not already present.  Run this script before install.sh when you do not
  have an existing PostgreSQL instance.

  Supported platforms:
    Debian / Ubuntu  — apt
    RHEL / Fedora    — dnf
    macOS            — Homebrew (brew)

  After installation you will need to:
    1. Ensure the PostgreSQL service is running.
    2. Set the postgres user password.
    3. Run install.sh to complete the MES AI setup.

NEXT STEPS (after this script completes)
  Linux — set the postgres password:
    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"

  macOS — set the postgres password:
    psql postgres -c "ALTER USER postgres PASSWORD 'your_password';"

  Then install MES AI:
    ./install.sh --db-password your_password

EOF
}

# ─── Argument parsing ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown option: $1"; show_help; exit 1 ;;
    esac
    shift
done

# ─── Output helpers ───────────────────────────────────────────────────────────
step() { echo; echo "==> $1"; }
ok()   { echo "    OK   $1"; }
warn() { echo "    WARN $1"; }
fail() { echo; echo "ERROR: $1" >&2; exit 1; }

ensure_macos_postgres_role() {
  if [[ "$OS" != "macos" ]]; then
    return 0
  fi

  if ! command -v psql &>/dev/null; then
    fail "psql was not found on PATH after installing PostgreSQL."
  fi

  if psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = 'postgres'" 2>/dev/null | grep -q 1; then
    ok "PostgreSQL role 'postgres' already exists."
  else
    warn "Homebrew PostgreSQL typically creates a superuser matching your macOS account, not 'postgres'."
    warn "Creating a 'postgres' role so MES AI can use its default PostgreSQL settings."

    psql postgres -v mes_ai_pwd="postgres" -c "CREATE ROLE postgres WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD :'mes_ai_pwd';" >/dev/null
    ok "Created PostgreSQL role 'postgres' with default password 'postgres'."
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

# ─── Check whether PostgreSQL is already installed ───────────────────────────
step "Checking for existing PostgreSQL installation"

if command -v psql &>/dev/null; then
    ok "PostgreSQL is already installed: $(psql --version)"
  ensure_macos_postgres_role
    echo ""
    echo "  Nothing to do.  Run install.sh to set up MES AI."
    exit 0
fi

# ─── Install PostgreSQL ───────────────────────────────────────────────────────
step "Installing PostgreSQL"

case "$OS" in
    macos)
        if ! command -v brew &>/dev/null; then
            fail "Homebrew is required to install PostgreSQL on macOS.
Install Homebrew first: https://brew.sh
Then rerun this script."
        fi
        brew install postgresql@16
        brew services start postgresql@16
        # Add brew-installed psql to PATH for this session
        PG_BIN="$(brew --prefix postgresql@16)/bin"
        export PATH="$PG_BIN:$PATH"
        ensure_macos_postgres_role
        ok "PostgreSQL installed and started."
        ;;
    debian)
        sudo apt-get update -q
        sudo apt-get install -y postgresql postgresql-client
        sudo systemctl enable --now postgresql
        ok "PostgreSQL installed and started."
        ;;
    rhel)
        sudo dnf install -y postgresql-server postgresql-contrib
        sudo postgresql-setup --initdb
        sudo systemctl enable --now postgresql
        ok "PostgreSQL installed and started."
        ;;
    *)
        fail "Unsupported OS.  Install PostgreSQL manually:
  https://www.postgresql.org/download/
Then run install.sh to complete the MES AI setup."
        ;;
esac

# ─── Post-install guidance ────────────────────────────────────────────────────
if [[ "$OS" == "macos" ]]; then
    PASS_CMD="psql postgres -c \"ALTER USER postgres PASSWORD 'your_password';\""
  SERVICE_NOTE="  The service was started automatically by brew services."
  MACOS_NOTE="  On macOS, this script also ensures a 'postgres' role exists. If it had to create it, the initial password is 'postgres'."
elif [[ "$OS" == "debian" ]]; then
    PASS_CMD="sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'your_password';\""
    SERVICE_NOTE="  The service was enabled and started via systemctl."
  MACOS_NOTE=""
else
    PASS_CMD="sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'your_password';\""
    SERVICE_NOTE="  The service was enabled and started via systemctl."
  MACOS_NOTE=""
fi

cat <<EOF

================================================================
  PostgreSQL installation complete!
================================================================
$SERVICE_NOTE
$MACOS_NOTE

  Next steps:

  1. Set the postgres user password:
       $PASS_CMD

  2. Run the MES AI installer:
       ./install.sh --db-password your_password

================================================================
EOF
