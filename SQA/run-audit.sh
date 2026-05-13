#!/usr/bin/env bash
# MES AI — SQA Audit runner (no external agent required)
# Usage: ./run-audit.sh [MODULE] [--headed] [--server URL] [--dt URL]
#
set -euo pipefail

MODULE="SQA-DT"
HEADED="0"
SERVER_URL="http://localhost:8081"
DT_URL="http://localhost:5177"

while [[ $# -gt 0 ]]; do
  case $1 in
    --headed)           HEADED="1";          shift ;;
    --server)           SERVER_URL="$2";     shift 2 ;;
    --dt)               DT_URL="$2";         shift 2 ;;
    *)                  MODULE="$1";         shift ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
HEARTBEAT="$(dirname "$0")/HEARTBEAT.md"

echo ""
echo "MES AI — SQA Audit"
echo "  Module    : $MODULE"
echo "  Server    : $SERVER_URL"
echo "  DT-CLIENT : $DT_URL"
echo "  Headed    : $HEADED"
echo ""

# ── 1. Health checks ─────────────────────────────────────────────────────────
echo "[1/3] Health checks..."

check_url() {
  local url="$1" label="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" || echo "000")
  if [[ "$code" == "200" ]]; then
    echo "  ✓ $label ($url) → $code"
  else
    echo "  ✗ $label ($url) → $code"
    return 1
  fi
}

check_url "$SERVER_URL/health" "MES server"
check_url "$DT_URL"            "DT-CLIENT"

# ── 2. Run pytest + Playwright ───────────────────────────────────────────────
echo ""
echo "[2/3] Running pytest ($MODULE)..."

export SQA_SERVER_URL="$SERVER_URL"
export SQA_DT_URL="$DT_URL"
export SQA_HEADED="$HEADED"

TEST_PATH="$(dirname "$0")/modules/$MODULE"
cd "$REPO_ROOT"
set +e
"$PYTHON" -m pytest "$TEST_PATH" -v --tb=short
EXIT_CODE=$?
set -e

# ── 3. Update HEARTBEAT.md ───────────────────────────────────────────────────
echo ""
echo "[3/3] Updating HEARTBEAT.md..."

if [[ $EXIT_CODE -eq 0 ]]; then
  ICON="✅ GREEN"
  RESULT="all tests passed"
else
  ICON="❌ RED"
  RESULT="FAILURES — see SQA/reports/latest/report.html"
fi

cat >> "$HEARTBEAT" <<EOF

## $TIMESTAMP — $MODULE $ICON
- Server : $SERVER_URL  DT-CLIENT : $DT_URL
- pytest  : $RESULT
- Report  : SQA/reports/latest/report.html
EOF

echo "  HEARTBEAT.md updated."
echo ""
echo "Audit complete — $ICON"
exit $EXIT_CODE