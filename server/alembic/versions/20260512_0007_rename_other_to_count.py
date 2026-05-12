"""Rename uom_type 'other' to 'count' for all affected rows.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-05-12 00:07:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: str = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE units_of_measure
           SET uom_type = 'count'
         WHERE uom_type = 'other'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE units_of_measure
           SET uom_type = 'other'
         WHERE uom_type = 'count'
        """
    )
