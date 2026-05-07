#!/usr/bin/env bash
# MES AI Server — container entrypoint
#
# Executed inside the mes-server container on every start.
# Runs database migrations (idempotent) then seeds built-in reference data
# before handing off to uvicorn.

set -euo pipefail

echo "================================================"
echo " MES AI Server — starting up"
echo "================================================"

# ── Alembic migrations ────────────────────────────────────────────────────────
# alembic.ini is at WORKDIR (/app), so no -c flag needed.
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

# ── Seed built-in units of measure (idempotent) ───────────────────────────────
echo "Seeding built-in units of measure..."
python scripts/seed_uom.py
echo "Seeding complete."

# ── Start application server ──────────────────────────────────────────────────
echo "Starting uvicorn on port 8082..."
exec uvicorn mes.main:app \
    --host 0.0.0.0 \
    --port 8082 \
    --workers 1 \
    --log-level "${MES_LOG_LEVEL:-info}"
