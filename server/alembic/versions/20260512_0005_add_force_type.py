"""Reclassify N, Nm, Pa, kPa to new 'force' uom_type.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-05-12 00:05:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a9b0"
down_revision: str = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE units_of_measure
           SET uom_type = 'force'
         WHERE symbol IN ('N', 'Nm', 'Pa', 'kPa')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE units_of_measure
           SET uom_type = 'other'
         WHERE symbol IN ('N', 'Nm', 'Pa', 'kPa')
        """
    )
