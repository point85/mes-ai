#!/usr/bin/env bash
# MES AI - DT SQA Audit runner
# Usage: ./run-dt-audit.sh --scope uom|users-and-groups|reasons|physical-model|data-definitions|storage-locations|materials|routes|equipment|products|work-schedule|plugins|all [--headed] [--server URL] [--dt URL]

set -euo pipefail

SCOPE=""
HEADED="0"
SERVER_URL="http://localhost:8082"
DT_URL="http://localhost:5173"

show_usage() {
  echo "Usage:"
  echo "  ./run-dt-audit.sh --scope <uom|users-and-groups|reasons|physical-model|data-definitions|storage-locations|materials|routes|equipment|products|work-schedule|plugins|all> [--headed] [--server URL] [--dt URL]"
  echo
  echo "Scopes:"
  echo "  uom            Run Units of Measure DT tests only"
  echo "  users-and-groups Run Users and Roles DT tests only"
  echo "  reasons        Run Reason Codes DT tests only"
  echo "  physical-model Run Sites/Areas/Lines/Work Cells DT tests only"
  echo "  data-definitions Run Data Definitions DT tests only"
  echo "  storage-locations Run Storage Locations DT tests only"
  echo "  materials      Run Materials DT tests only"
  echo "  routes         Run Standalone Route Editor DT tests only"
  echo "  equipment      Run Equipment DT tests only"
  echo "  products       Run Products and BOM DT tests only"
  echo "  work-schedule  Run Work Schedule DT tests only"
  echo "  plugins        Run all plugin UI tests"
  echo "  all            Run the full DT SQA suite"
  echo
  echo "Examples:"
  echo "  ./run-dt-audit.sh --scope uom"
  echo "  ./run-dt-audit.sh --scope users-and-groups"
  echo "  ./run-dt-audit.sh --scope reasons"
  echo "  ./run-dt-audit.sh --scope physical-model"
  echo "  ./run-dt-audit.sh --scope data-definitions"
  echo "  ./run-dt-audit.sh --scope storage-locations"
  echo "  ./run-dt-audit.sh --scope materials"
  echo "  ./run-dt-audit.sh --scope routes"
  echo "  ./run-dt-audit.sh --scope equipment"
  echo "  ./run-dt-audit.sh --scope products"
  echo "  ./run-dt-audit.sh --scope work-schedule --headed"
  echo "  ./run-dt-audit.sh --scope plugins"
  echo "  ./run-dt-audit.sh --scope plugins --headed"
  echo "  ./run-dt-audit.sh --scope all --server http://localhost:8082 --dt http://localhost:5173"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --scope)            SCOPE="$2";         shift 2 ;;
    -h|--help)          show_usage;          exit 0 ;;
    --headed)           HEADED="1";         shift ;;
    --server)           SERVER_URL="$2";    shift 2 ;;
    --dt)               DT_URL="$2";        shift 2 ;;
    *)                  echo "Unknown argument: $1"; echo; show_usage; exit 2 ;;
  esac
done

if [[ -z "$SCOPE" ]]; then
  show_usage
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
HEARTBEAT="$(dirname "$0")/HEARTBEAT.md"

case "$SCOPE" in
  uom)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_uom_crud.py")
    ;;
  users-and-groups)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_auth_admin_crud.py")
    ;;
  reasons)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_reason_crud.py")
    ;;
  physical-model)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_physical_model_crud.py")
    ;;
  data-definitions)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_data_definition_crud.py")
    ;;
  storage-locations)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_storage_location_crud.py")
    ;;
  materials)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_material_crud.py")
    ;;
  routes)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_route_editor_crud.py")
    ;;
  equipment)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_equipment_crud.py")
    ;;
  products)
    TEST_TARGETS=(
      "$(dirname "$0")/modules/SQA-DT/test_product_crud.py"
      "$(dirname "$0")/modules/SQA-DT/test_product_route_crud.py"
      "$(dirname "$0")/modules/SQA-DT/test_product_bom_crud.py"
    )
    ;;
  work-schedule)
    TEST_TARGETS=(
      "$(dirname "$0")/modules/SQA-DT/test_work_schedule_crud.py"
      "$(dirname "$0")/modules/SQA-DT/test_work_schedule_shift_crud.py"
      "$(dirname "$0")/modules/SQA-DT/test_work_schedule_rotation_crud.py"
      "$(dirname "$0")/modules/SQA-DT/test_work_schedule_team_crud.py"
      "$(dirname "$0")/modules/SQA-DT/test_work_schedule_non_working_period_crud.py"
      "$(dirname "$0")/modules/SQA-DT/test_work_schedule_queries.py"
    )
    ;;
  plugins)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT/test_kafka_plugin_ui.py")
    ;;
  all)
    TEST_TARGETS=("$(dirname "$0")/modules/SQA-DT")
    ;;
  *)
    echo "Invalid scope: $SCOPE"
    echo "Expected one of: uom, users-and-groups, reasons, physical-model, data-definitions, storage-locations, materials, routes, equipment, products, work-schedule, plugins, all"
    exit 2
    ;;
esac

echo ""
echo "MES AI - DT SQA Audit"
echo "  Scope     : $SCOPE"
echo "  Targets   :"
for target in "${TEST_TARGETS[@]}"; do
  echo "    - $target"
done
echo "  Server    : $SERVER_URL"
echo "  DT-CLIENT : $DT_URL"
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
check_url "$DT_URL" "DT-CLIENT"

echo ""
echo "[2/3] Running pytest ($SCOPE)..."

export SQA_SERVER_URL="$SERVER_URL"
export SQA_DT_URL="$DT_URL"
export SQA_HEADED="$HEADED"

cd "$REPO_ROOT"
set +e
"$PYTHON" -m pytest "${TEST_TARGETS[@]}" -v --tb=short
EXIT_CODE=$?
set -e

echo ""
echo "[3/3] Updating HEARTBEAT.md..."

if [[ $EXIT_CODE -eq 0 ]]; then
  ICON="PASS"
  RESULT="all tests passed"
else
  ICON="FAIL"
  RESULT="FAILURES - see SQA/reports/latest/report.html"
fi

cat >> "$HEARTBEAT" <<EOF

## $TIMESTAMP - DT-AUDIT [$ICON]
- Scope  : $SCOPE
- Server : $SERVER_URL  DT-CLIENT : $DT_URL
- pytest : $RESULT
- Report : SQA/reports/latest/report.html
EOF

echo "  HEARTBEAT.md updated."
echo ""
echo "Audit complete - [$ICON]"
exit $EXIT_CODE