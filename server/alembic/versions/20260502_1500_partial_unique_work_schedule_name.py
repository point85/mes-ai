"""partial_unique_work_schedule_name

Replace the full unique index on work_schedules.name with a partial unique
index that only enforces uniqueness among *active* records.  This lets a
soft-deleted schedule be replaced by a new record with the same name.

Revision ID: a1b2c3d4e5f6
Revises: f72c48a370e4
Create Date: 2026-05-02 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c9d8e7f6a5b4'
down_revision: Union[str, None] = 'f72c48a370e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old full unique index
    op.drop_index('ix_work_schedules_name', table_name='work_schedules')
    # Create a partial unique index — only active rows must have distinct names
    op.execute(
        "CREATE UNIQUE INDEX ix_work_schedules_name "
        "ON work_schedules (name) WHERE (is_active = TRUE)"
    )


def downgrade() -> None:
    op.drop_index('ix_work_schedules_name', table_name='work_schedules')
    op.create_index('ix_work_schedules_name', 'work_schedules', ['name'], unique=True)
