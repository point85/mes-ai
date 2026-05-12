"""Reclassify degrees Brix (°Bx) to mass type and volt (V) to electrical type.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "b4c5d6e7f8a9"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "UPDATE units_of_measure"
            " SET uom_type = 'mass', updated_at = NOW()"
            " WHERE symbol = '°Bx'"
        )
    )
    conn.execute(
        text(
            "UPDATE units_of_measure"
            " SET uom_type = 'electrical', updated_at = NOW()"
            " WHERE symbol = 'V'"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "UPDATE units_of_measure"
            " SET uom_type = 'other', updated_at = NOW()"
            " WHERE symbol IN ('°Bx', 'V')"
        )
    )
