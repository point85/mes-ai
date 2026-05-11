"""Re-add fluid ounce (fl oz) with uom_type 'length'.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-05-11
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Insert only if not already present
    exists = conn.execute(
        text("SELECT 1 FROM units_of_measure WHERE symbol = 'fl oz'")
    ).fetchone()
    if not exists:
        now = datetime.now(timezone.utc)
        conn.execute(
            text("""
                INSERT INTO units_of_measure
                    (id, symbol, name, uom_type, uom_class, multiplier, "offset",
                     is_builtin, left_uom_id, right_uom_id, exponent,
                     created_at, updated_at, is_active)
                VALUES
                    (:id, 'fl oz', 'fluid ounce', 'length', 'scalar', :mult, 0.0,
                     TRUE, NULL, NULL, NULL,
                     :now, :now, TRUE)
            """),
            {"id": str(uuid.uuid4()), "mult": 2.957352965e-5, "now": now},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DELETE FROM units_of_measure WHERE symbol = 'fl oz'"))
