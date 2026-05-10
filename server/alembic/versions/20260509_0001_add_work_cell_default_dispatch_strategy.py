"""add default_dispatch_strategy to work_cells

Revision ID: a1b2c3d4e5f6
Revises: 3dcc0683513d
Create Date: 2026-05-09 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3dcc0683513d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'work_cells',
        sa.Column(
            'default_dispatch_strategy',
            sa.String(length=50),
            nullable=True,
            comment="Default dispatch strategy for this work cell (e.g. 'first_available', 'shortest_queue'). Used when no strategy is specified at dispatch time.",
        ),
    )


def downgrade() -> None:
    op.drop_column('work_cells', 'default_dispatch_strategy')
