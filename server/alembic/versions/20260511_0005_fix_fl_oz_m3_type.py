"""Fix uom_type to 'length' for fluid ounce and cubic meter.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-11
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().execute(
        text(
            "UPDATE units_of_measure SET uom_type = 'length'"
            " WHERE symbol = ANY(:syms)"
        ),
        {"syms": ["fl oz", "m³"]},
    )


def downgrade() -> None:
    op.get_bind().execute(
        text(
            "UPDATE units_of_measure SET uom_type = 'other'"
            " WHERE symbol = ANY(:syms)"
        ),
        {"syms": ["fl oz", "m³"]},
    )
