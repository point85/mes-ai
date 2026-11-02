"""add tracking_override to material_lots

Revision ID: 20260906_0001
Revises: 20260905_0001
Create Date: 2026-09-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260906_0001"
down_revision = "20260905_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("material_lots") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tracking_override",
                sa.String(length=10),
                nullable=True,
                comment="Tracking method fixed when the lot was created from WIP (unit or lot); null uses the material default",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("material_lots") as batch_op:
        batch_op.drop_column("tracking_override")
