"""add_data_snapshot_to_segment_response_lots

Add data_snapshot JSON column to segment_response_lots to match
segment_response_units, enabling step parameter actual values to be
persisted for lot-based WIP.

Revision ID: bb22cc33dd44
Revises: aa11bb22cc33
Create Date: 2026-05-05 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bb22cc33dd44'
down_revision: Union[str, None] = 'aa11bb22cc33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "segment_response_lots",
        sa.Column(
            "data_snapshot",
            sa.JSON(),
            nullable=True,
            comment="Freeform JSON snapshot of data collected at this step (step parameter actuals, etc.)",
        ),
    )


def downgrade() -> None:
    op.drop_column("segment_response_lots", "data_snapshot")
