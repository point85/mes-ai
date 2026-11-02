"""add tracking to material_definitions

Revision ID: 20260907_0001
Revises: 20260906_0001
Create Date: 2026-09-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260907_0001"
down_revision = "20260906_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("material_definitions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tracking",
                sa.String(length=10),
                nullable=False,
                server_default="lot",
                comment="Inventory tracking: 'lot' (quantity per lot) or 'unit' (one serial-numbered unit, qty 1)",
            )
        )

    # Preserve prior behaviour: materials whose UOM was "each" were unit tracked.
    op.execute(
        "UPDATE material_definitions SET tracking = 'unit' "
        "WHERE uom_id IN (SELECT id FROM units_of_measure WHERE symbol = 'EA')"
    )


def downgrade() -> None:
    with op.batch_alter_table("material_definitions") as batch_op:
        batch_op.drop_column("tracking")
