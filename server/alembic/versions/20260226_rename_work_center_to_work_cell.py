"""rename work_center to work_cell

Revision ID: a3b4c5d6e7f8
Revises: 1822ca139098
Create Date: 2026-02-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = '1822ca139098'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename table work_centers → work_cells
    op.rename_table("work_centers", "work_cells")

    # Rename FK column in equipment table
    op.alter_column("equipment", "work_center_id", new_column_name="work_cell_id")

    # Rename FK column in route_steps table
    op.alter_column("route_steps", "work_center_id", new_column_name="work_cell_id")


def downgrade() -> None:
    # Reverse: rename back
    op.alter_column("route_steps", "work_cell_id", new_column_name="work_center_id")
    op.alter_column("equipment", "work_cell_id", new_column_name="work_center_id")
    op.rename_table("work_cells", "work_centers")
