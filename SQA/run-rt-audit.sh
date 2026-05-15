#!/usr/bin/env bash
# MES AI - RT SQA Audit runner
# Usage: ./run-rt-audit.sh --scope inventory|wip|all [--headed] [--server URL] [--rt URL]

set -euo pipefail

SCOPE=""
HEADED="0"
SERVER_URL="http://localhost:8081"
RT_URL="http://localhost:5178"

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
  echo "  ./run-rt-audit.sh --scope wip --server http://localhost:8081 --rt http://localhost:5178"
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

check_url() {
  local url="$1" label="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" || echo "000")
  if [[ "$code" == "200" ]]; then
    echo "  [OK]   $label ($url) -> $code"
  else
    echo "  [FAIL] $label ($url) -> $code"
    return 1
  fi
}

check_url "$SERVER_URL/health" "MES server"
check_url "$RT_URL" "RT-CLIENT"

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