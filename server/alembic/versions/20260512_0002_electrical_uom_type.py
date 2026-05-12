"""Add 'electrical' uom_type; reclassify ampere and milliampere from 'other'.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None

_ELECTRICAL_SYMBOLS = ("A", "mA")


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "UPDATE units_of_measure"
            " SET uom_type = 'electrical', updated_at = NOW()"
            " WHERE symbol = ANY(:symbols)"
        ).bindparams(symbols=list(_ELECTRICAL_SYMBOLS))
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "UPDATE units_of_measure"
            " SET uom_type = 'other', updated_at = NOW()"
            " WHERE symbol = ANY(:symbols)"
        ).bindparams(symbols=list(_ELECTRICAL_SYMBOLS))
    )
