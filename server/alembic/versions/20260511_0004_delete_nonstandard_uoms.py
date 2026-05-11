"""Delete non-standard UoMs: °Bx, pH, CFU/mL, N, mA, kPa, Pa, Nm, V.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-11
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

# Symbols to remove — all confirmed non-builtin custom records
_DELETE_SYMBOLS = ("°Bx", "pH", "CFU/mL", "N", "mA", "kPa", "Pa", "Nm", "V")


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Null out nullable FK references to these UoMs ─────────────
    conn.execute(
        text(
            "UPDATE equipment_class_properties SET uom_id = NULL"
            " WHERE uom_id IN"
            " (SELECT id FROM units_of_measure WHERE symbol = ANY(:syms))"
        ),
        {"syms": list(_DELETE_SYMBOLS)},
    )
    conn.execute(
        text(
            "UPDATE data_definitions SET uom_id = NULL"
            " WHERE uom_id IN"
            " (SELECT id FROM units_of_measure WHERE symbol = ANY(:syms))"
        ),
        {"syms": list(_DELETE_SYMBOLS)},
    )
    conn.execute(
        text(
            "UPDATE segment_parameters SET uom_id = NULL"
            " WHERE uom_id IN"
            " (SELECT id FROM units_of_measure WHERE symbol = ANY(:syms))"
        ),
        {"syms": list(_DELETE_SYMBOLS)},
    )

    # ── 2. Delete the units ───────────────────────────────────────────
    conn.execute(
        text("DELETE FROM units_of_measure WHERE symbol = ANY(:syms)"),
        {"syms": list(_DELETE_SYMBOLS)},
    )


def downgrade() -> None:
    # These were custom/demo records — no restore on downgrade.
    pass
