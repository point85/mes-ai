"""Reclassify pH from 'other' to 'amount_of_substance' uom_type.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-05-12 00:06:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: str = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE units_of_measure
           SET uom_type = 'amount_of_substance'
         WHERE symbol = 'pH'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE units_of_measure
           SET uom_type = 'other'
         WHERE symbol = 'pH'
        """
    )
