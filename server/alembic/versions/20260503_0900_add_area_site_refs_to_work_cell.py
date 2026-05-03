"""add_area_site_refs_to_work_cell

Add denormalized ``area_id`` and ``site_id`` columns to ``work_cells`` so that
every WorkCell carries direct UUID references to each ancestor level of the
ISA-95 physical hierarchy (Site → Area → ProductionLine → WorkCell) without
requiring multi-level joins.

Existing rows are back-filled via a SQL UPDATE that walks through the join chain.

Revision ID: d4e5f6a7b8c9
Revises: c9d8e7f6a5b4
Create Date: 2026-05-03 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c9d8e7f6a5b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns as nullable first so existing rows don't violate NOT NULL.
    op.add_column(
        'work_cells',
        sa.Column(
            'area_id',
            sa.Uuid(),
            nullable=True,
            comment='Denormalized reference to the parent Area (avoids join through ProductionLine).',
        ),
    )
    op.add_column(
        'work_cells',
        sa.Column(
            'site_id',
            sa.Uuid(),
            nullable=True,
            comment='Denormalized reference to the parent Site (avoids two-level join).',
        ),
    )

    # Back-fill: resolve area_id and site_id via the existing FK chain.
    op.execute("""
        UPDATE work_cells wc
        SET
            area_id = pl.area_id,
            site_id = a.site_id
        FROM production_lines pl
        JOIN areas a ON a.id = pl.area_id
        WHERE wc.line_id = pl.id
    """)

    # Now enforce NOT NULL and add FK constraints + indexes.
    op.alter_column('work_cells', 'area_id', nullable=False)
    op.alter_column('work_cells', 'site_id', nullable=False)

    op.create_foreign_key(
        'fk_work_cells_area_id',
        'work_cells', 'areas',
        ['area_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_work_cells_site_id',
        'work_cells', 'sites',
        ['site_id'], ['id'],
    )
    op.create_index('ix_work_cells_area_id', 'work_cells', ['area_id'])
    op.create_index('ix_work_cells_site_id', 'work_cells', ['site_id'])


def downgrade() -> None:
    op.drop_index('ix_work_cells_site_id', table_name='work_cells')
    op.drop_index('ix_work_cells_area_id', table_name='work_cells')
    op.drop_constraint('fk_work_cells_site_id', 'work_cells', type_='foreignkey')
    op.drop_constraint('fk_work_cells_area_id', 'work_cells', type_='foreignkey')
    op.drop_column('work_cells', 'site_id')
    op.drop_column('work_cells', 'area_id')
