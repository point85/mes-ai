"""add capacity_uom_id to storage_locations

Revision ID: 20260620_0001
Revises: 4b608427bd14
Create Date: 2026-06-20 00:01:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260620_0001"
down_revision = "4b608427bd14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "storage_locations",
        sa.Column(
            "capacity_uom_id",
            sa.Uuid(),
            sa.ForeignKey("units_of_measure.id"),
            nullable=True,
            comment="Unit of measure for the capacity value",
        ),
    )


def downgrade() -> None:
    op.drop_column("storage_locations", "capacity_uom_id")
