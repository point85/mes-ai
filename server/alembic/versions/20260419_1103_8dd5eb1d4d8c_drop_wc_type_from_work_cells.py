"""drop_wc_type_from_work_cells

Revision ID: 8dd5eb1d4d8c
Revises: n4o5p6q7r8s9
Create Date: 2026-04-19 11:03:13.102869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8dd5eb1d4d8c'
down_revision: Union[str, None] = 'n4o5p6q7r8s9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('work_cells', 'wc_type')


def downgrade() -> None:
    op.add_column('work_cells', sa.Column('wc_type', sa.VARCHAR(length=20), nullable=False, server_default='manual', comment="Work cell type: 'manual' or 'automated'"))
