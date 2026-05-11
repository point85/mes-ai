"""Fix uom_type to 'length' for volume and linear-velocity units; fix mm/s class to quotient.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-11
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

# Symbols that simply need uom_type corrected to 'length'
_FIX_TYPE = ("L", "mL", "L/h", "L/min", "mL/h", "mm/s")


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Fix uom_type → 'length' for volume / flow units ───────────
    conn.execute(
        text(
            "UPDATE units_of_measure SET uom_type = 'length'"
            " WHERE symbol = ANY(:syms)"
        ),
        {"syms": list(_FIX_TYPE)},
    )

    # ── 2. Fix mm/s: scalar → quotient, link left=mm, right=s ────────
    mm_row = conn.execute(
        text("SELECT id FROM units_of_measure WHERE symbol = 'mm' AND uom_class = 'scalar'")
    ).fetchone()
    s_row = conn.execute(
        text("SELECT id FROM units_of_measure WHERE symbol = 's' AND uom_class = 'scalar'")
    ).fetchone()

    if mm_row and s_row:
        conn.execute(
            text(
                "UPDATE units_of_measure"
                " SET uom_class = 'quotient', left_uom_id = :mm, right_uom_id = :s"
                " WHERE symbol = 'mm/s' AND uom_class = 'scalar'"
            ),
            {"mm": str(mm_row[0]), "s": str(s_row[0])},
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Restore mm/s to scalar (best-effort)
    conn.execute(
        text(
            "UPDATE units_of_measure"
            " SET uom_class = 'scalar', uom_type = 'other',"
            "     left_uom_id = NULL, right_uom_id = NULL"
            " WHERE symbol = 'mm/s'"
        )
    )

    conn.execute(
        text(
            "UPDATE units_of_measure SET uom_type = 'other'"
            " WHERE symbol = ANY(:syms)"
        ),
        {"syms": list(_FIX_TYPE)},
    )
