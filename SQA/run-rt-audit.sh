#!/usr/bin/env bash
# MES AI - RT SQA Audit runner
# Usage: ./run-rt-audit.sh --scope inventory|wip|all [--headed] [--server URL] [--rt URL]

set -euo pipefail

SCOPE=""
HEADED="0"
SERVER_URL="http://localhost:8082"
RT_URL="http://localhost:5176"

show_usage() {
  echo "Usage:"
  echo "  ./run-rt-audit.sh --scope <inventory|wip|all> [--headed] [--server URL] [--rt URL]"
  echo
  echo "Scopes:"
  echo "  inventory      Run Inventory RT tests only"
  echo "  wip            Run WIP RT tests only"
  echo "  all            Run the full RT SQA suite"
  echo
  echo "Examples:"
  echo "  ./run-rt-audit.sh --scope inventory"
  echo "  ./run-rt-audit.sh --scope wip"
  echo "  ./run-rt-audit.sh --scope all --headed"
  echo "  ./run-rt-audit.sh --scope wip --server http://localhost:8082 --rt http://localhost:5176"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --scope)            SCOPE="$2";      shift 2 ;;
    -h|--help)          show_usage;       exit 0 ;;
    --headed)           HEADED="1";      shift ;;
    --server)           SERVER_URL="$2"; shift 2 ;;
    --rt)               RT_URL="$2";     shift 2 ;;
    *)                  echo "Unknown argument: $1"; echo; show_usage; exit 2 ;;
  esac
done

if [[ -z "$SCOPE" ]]; then
  show_usage
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
PREP_SCRIPT="$REPO_ROOT/server/scripts/prepare_rt_inventory.py"
TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
HEARTBEAT="$(dirname "$0")/HEARTBEAT.md"

case "$SCOPE" in
  inventory)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-RT/test_inventory_operations.py")
    ;;
  wip)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-RT/test_wip_operations.py")
    ;;
  all)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-RT")
    ;;
  *)
    echo "Invalid scope: $SCOPE"
    echo "Expected one of: inventory, wip, all"
    exit 2
    ;;
esac

echo ""
echo "MES AI - RT SQA Audit"
echo "  Scope     : $SCOPE"
echo "  Targets   :"
for target in "${TEST_TARGETS[@]}"; do
  echo "    - $target"
done
echo "  Server    : $SERVER_URL"
echo "  RT-CLIENT : $RT_URL"
echo "  Headed    : $HEADED"
echo ""

echo "[1/3] Health checks..."

# Check MES server - parse JSON and print each adapter's health.
# A timeout or connection failure is WARNING only; tests continue.
HEALTH_URL="$SERVER_URL/health"
SERVER_OK=false
set +e
HEALTH_BODY=$(curl -s --max-time 10 "$HEALTH_URL" 2>/dev/null)
HEALTH_EXIT=$?
set -e

if [[ $HEALTH_EXIT -eq 0 && -n "$HEALTH_BODY" ]]; then
  echo "  [OK]   MES server ($HEALTH_URL) -> 200"
  SERVER_OK=true
  echo "$HEALTH_BODY" | "$PYTHON" -c "
import sys, json
try:
    d = json.load(sys.stdin)
    status = d.get('status', '')
    auth = d.get('auth_mode', '')
    plugins = d.get('plugins_loaded', '')
    print('         status=' + str(status) + '  auth=' + str(auth) + '  plugins=' + str(plugins))
    for k, v in (d.get('adapters') or {}).items():
        icon = '[OK]  ' if v else '[WARN]'
        print('         adapter ' + icon + ' ' + k)
except Exception:
    pass
" 2>/dev/null || true
else
  echo "  [WARN] MES server ($HEALTH_URL) -> connection failed - continuing anyway"
fi

# Check RT-CLIENT - hard stop if unreachable (browser tests need the UI).
set +e
RT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$RT_URL" 2>/dev/null || echo "000")
set -e
if [[ "$RT_CODE" == "200" ]]; then
  echo "  [OK]   RT-CLIENT ($RT_URL) -> $RT_CODE"
else
  echo "  [FAIL] RT-CLIENT ($RT_URL) -> $RT_CODE"
  echo ""
  echo "ERROR: RT-CLIENT is not reachable. Start the client before running the audit."
  exit 1
fi

if [[ "$SERVER_OK" == "false" ]]; then
  echo "  [WARN] MES server unreachable - API-level tests may fail."
fi

echo ""
echo "[2/4] Normalizing demo inventory..."

(
  cd "$REPO_ROOT/server"
  "$PYTHON" "$PREP_SCRIPT"
)

echo ""
echo "[3/4] Running pytest ($SCOPE)..."

export SQA_SERVER_URL="$SERVER_URL"
export SQA_RT_URL="$RT_URL"
export SQA_HEADED="$HEADED"

cd "$REPO_ROOT"
set +e
"$PYTHON" -m pytest "${TEST_TARGETS[@]}" -v --tb=short
EXIT_CODE=$?
set -e

echo ""
echo "[4/4] Updating HEARTBEAT.md..."

if [[ $EXIT_CODE -eq 0 ]]; then
  ICON="PASS"
  RESULT="all tests passed"
else
  ICON="FAIL"
  RESULT="FAILURES - see SQA/reports/latest/report.html"
fi

cat >> "$HEARTBEAT" <<EOF

## $TIMESTAMP - RT-AUDIT [$ICON]
- Scope  : $SCOPE
- Server : $SERVER_URL  RT-CLIENT : $RT_URL
- pytest : $RESULT
- Report : SQA/reports/latest/report.html
EOF

echo "  HEARTBEAT.md updated."
echo ""
echo "Audit complete - [$ICON]"
exit $EXIT_CODE