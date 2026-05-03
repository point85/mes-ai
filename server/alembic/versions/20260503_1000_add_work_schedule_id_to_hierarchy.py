"""add_work_schedule_id_to_hierarchy

Add a nullable ``work_schedule_id`` FK column to the four ISA-95 physical
hierarchy tables (sites, areas, production_lines, work_cells).  This allows a
work schedule to be assigned at any level of the hierarchy from the DT-CLIENT
editors.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ["sites", "areas", "production_lines", "work_cells"]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                'work_schedule_id',
                sa.Uuid(),
                nullable=True,
                comment='Optional work schedule assigned at this hierarchy level.',
            ),
        )
        op.create_foreign_key(
            f'fk_{table}_work_schedule_id',
            table, 'work_schedules',
            ['work_schedule_id'], ['id'],
            ondelete='SET NULL',
        )
        op.create_index(
            f'ix_{table}_work_schedule_id',
            table, ['work_schedule_id'],
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_index(f'ix_{table}_work_schedule_id', table_name=table)
        op.drop_constraint(f'fk_{table}_work_schedule_id', table, type_='foreignkey')
        op.drop_column(table, 'work_schedule_id')
