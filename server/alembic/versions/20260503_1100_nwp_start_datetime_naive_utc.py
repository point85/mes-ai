"""nwp_start_datetime_naive_utc

Change non_working_periods.start_datetime from TIMESTAMPTZ to plain TIMESTAMP
to match the project-wide convention of storing naive UTC datetimes (same as
the *_utc companion columns on every BaseModel).

Revision ID: f0a1b2c3d4e5
Revises: e5f6a7b8c9d0
Create Date: 2026-05-03 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'non_working_periods',
        'start_datetime',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using='start_datetime AT TIME ZONE \'UTC\'',
    )


def downgrade() -> None:
    op.alter_column(
        'non_working_periods',
        'start_datetime',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using='start_datetime AT TIME ZONE \'UTC\'',
    )
