"""Add volume / fluid-volume UoMs: liter, milliliter, fluid ounce, L/h, L/min, mL/h

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-11
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from alembic import op
from sqlalchemy import text

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

# New scalar units: (symbol, name, uom_type, multiplier, offset)
_NEW_SCALARS = [
    ("L",     "liter",        "length", 0.001,            0.0),
    ("mL",    "milliliter",   "length", 1.0e-6,           0.0),
    ("fl oz", "fluid ounce",  "length", 2.957352965e-5,   0.0),
]

# New quotient units: (symbol, name, left_symbol, right_symbol)
_NEW_QUOTIENTS = [
    ("L/h",   "liters per hour",       "L",  "h"),
    ("L/min", "liters per minute",     "L",  "min"),
    ("mL/h",  "milliliters per hour",  "mL", "h"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Insert scalar units (skip if already present) ─────────────
    scalar_ids: dict[str, str] = {}  # symbol → id (str UUID)

    for symbol, name, uom_type, multiplier, offset in _NEW_SCALARS:
        row = conn.execute(
            text("SELECT id FROM units_of_measure WHERE symbol = :s"),
            {"s": symbol},
        ).fetchone()
        if row:
            scalar_ids[symbol] = str(row[0])
            continue

        uid = str(uuid.uuid4())
        scalar_ids[symbol] = uid
        conn.execute(
            text("""
            INSERT INTO units_of_measure
                (id, symbol, name, uom_type, uom_class, multiplier, "offset", is_builtin,
                 left_uom_id, right_uom_id, exponent,
                 created_at, updated_at, is_active)
            VALUES
                (:id, :symbol, :name, :uom_type, 'scalar', :multiplier, :offset, TRUE,
                 NULL, NULL, NULL,
                 :now, :now, TRUE)
            """),
            {
                "id": uid,
                "symbol": symbol,
                "name": name,
                "uom_type": uom_type,
                "multiplier": multiplier,
                "offset": offset,
                "now": datetime.now(timezone.utc),
            },
        )

    # ── 2. Resolve existing scalar IDs for time units (h, min) ───────
    for sym in ("h", "min"):
        row = conn.execute(
            text("SELECT id FROM units_of_measure WHERE symbol = :s AND uom_class = 'scalar'"),
            {"s": sym},
        ).fetchone()
        if row:
            scalar_ids[sym] = str(row[0])

    # ── 3. Insert quotient units (skip if already present) ───────────
    for symbol, name, left_sym, right_sym in _NEW_QUOTIENTS:
        exists = conn.execute(
            text("SELECT 1 FROM units_of_measure WHERE symbol = :s"),
            {"s": symbol},
        ).fetchone()
        if exists:
            continue

        left_id = scalar_ids.get(left_sym)
        right_id = scalar_ids.get(right_sym)
        if not left_id or not right_id:
            continue  # skip if base units are missing

        # uom_type inherits from left unit
        left_row = conn.execute(
            text("SELECT uom_type FROM units_of_measure WHERE id = :id"),
            {"id": left_id},
        ).fetchone()
        uom_type = left_row[0] if left_row else "length"

        uid = str(uuid.uuid4())
        conn.execute(
            text("""
            INSERT INTO units_of_measure
                (id, symbol, name, uom_type, uom_class, multiplier, "offset", is_builtin,
                 left_uom_id, right_uom_id, exponent,
                 created_at, updated_at, is_active)
            VALUES
                (:id, :symbol, :name, :uom_type, 'quotient', 1.0, 0.0, TRUE,
                 :left_uom_id, :right_uom_id, NULL,
                 :now, :now, TRUE)
            """),
            {
                "id": uid,
                "symbol": symbol,
                "name": name,
                "uom_type": uom_type,
                "left_uom_id": left_id,
                "right_uom_id": right_id,
                "now": datetime.now(timezone.utc),
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    all_symbols = (
        [s for s, *_ in _NEW_QUOTIENTS]
        + [s for s, *_ in _NEW_SCALARS]
    )
    for symbol in all_symbols:
        conn.execute(
            text("DELETE FROM units_of_measure WHERE symbol = :s AND is_builtin = TRUE"),
            {"s": symbol},
        )
