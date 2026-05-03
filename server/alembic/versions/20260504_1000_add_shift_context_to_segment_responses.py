"""add_shift_context_to_segment_responses

Add work_schedule_name, shift_name, team_name columns to
segment_response_units and segment_response_lots for genealogy /
traceability — records the active work schedule, shift and team at the
moment each unit or lot entered a process step.

Revision ID: 9a8b7c6d5e4f
Revises: f0a1b2c3d4e5
Create Date: 2026-05-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, None] = 'f0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ["segment_response_units", "segment_response_lots"]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                'work_schedule_name',
                sa.String(200),
                nullable=True,
                comment='Work schedule name active when this event was recorded',
            ),
        )
        op.add_column(
            table,
            sa.Column(
                'shift_name',
                sa.String(200),
                nullable=True,
                comment='Shift name active when this event was recorded',
            ),
        )
        op.add_column(
            table,
            sa.Column(
                'team_name',
                sa.String(200),
                nullable=True,
                comment='Team name active when this event was recorded',
            ),
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_column(table, 'team_name')
        op.drop_column(table, 'shift_name')
        op.drop_column(table, 'work_schedule_name')
