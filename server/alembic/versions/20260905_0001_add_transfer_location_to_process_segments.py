"""add transfer_location_id to process_segments

Revision ID: 20260905_0001
Revises: 20260904_0001
Create Date: 2026-09-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260905_0001"
down_revision = "20260904_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("process_segments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "transfer_location_id",
                sa.Uuid(),
                nullable=True,
                comment="Storage location a WIP lot/unit completed from this step is transferred to",
            )
        )
        batch_op.create_foreign_key(
            "fk_process_segments_transfer_location",
            "storage_locations",
            ["transfer_location_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("process_segments") as batch_op:
        batch_op.drop_constraint("fk_process_segments_transfer_location", type_="foreignkey")
        batch_op.drop_column("transfer_location_id")
