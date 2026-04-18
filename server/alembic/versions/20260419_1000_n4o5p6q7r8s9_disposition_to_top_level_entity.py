"""disposition_to_top_level_entity

Replace input_disposition / disposition_category string columns on
route_steps with a proper top-level dispositions table and a
disposition_id FK.

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-04-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n4o5p6q7r8s9'
down_revision: Union[str, None] = 'm3n4o5p6q7r8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the new top-level dispositions table
    op.create_table(
        'dispositions',
        sa.Column('code', sa.String(50), nullable=False, comment="Short unique code (e.g. 'PASS', 'QC-FAIL')"),
        sa.Column('name', sa.String(255), nullable=False, comment='Human-readable disposition name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional description of when this disposition applies'),
        sa.Column('category', sa.String(20), nullable=False, comment="Disposition category: 'route', 'hold', or 'scrap'"),
        sa.Column('id', sa.UUID(), nullable=False, comment='Unique identifier for the entity'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Timestamp when the entity was created'),
        sa.Column('created_at_utc', sa.DateTime(), nullable=True, comment='Timestamp when the entity was created (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='Timestamp when the entity was last updated'),
        sa.Column('updated_at_utc', sa.DateTime(), nullable=True, comment='Timestamp when the entity was last updated (UTC)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Soft delete flag. False means the entity is logically deleted.'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_disposition_code'),
    )
    op.create_index(op.f('ix_dispositions_id'), 'dispositions', ['id'], unique=False)
    op.create_index(op.f('ix_dispositions_code'), 'dispositions', ['code'], unique=True)

    # 2. Add disposition_id FK to route_steps
    op.add_column(
        'route_steps',
        sa.Column(
            'disposition_id',
            sa.UUID(),
            nullable=True,
            comment='FK to the disposition that routes WIP to this step',
        ),
    )
    op.create_foreign_key(
        'fk_route_steps_disposition_id',
        'route_steps', 'dispositions',
        ['disposition_id'], ['id'],
    )
    op.create_index(op.f('ix_route_steps_disposition_id'), 'route_steps', ['disposition_id'], unique=False)

    # 3. Drop old string columns from route_steps
    op.drop_column('route_steps', 'disposition_category')
    op.drop_column('route_steps', 'input_disposition')


def downgrade() -> None:
    # Re-add old string columns
    op.add_column(
        'route_steps',
        sa.Column(
            'input_disposition',
            sa.String(100),
            nullable=True,
            comment='Disposition name that routes WIP to this step',
        ),
    )
    op.add_column(
        'route_steps',
        sa.Column(
            'disposition_category',
            sa.String(20),
            server_default='route',
            nullable=False,
            comment='Disposition category: route, hold, scrap',
        ),
    )

    # Drop disposition_id FK and column
    op.drop_index(op.f('ix_route_steps_disposition_id'), table_name='route_steps')
    op.drop_constraint('fk_route_steps_disposition_id', 'route_steps', type_='foreignkey')
    op.drop_column('route_steps', 'disposition_id')

    # Drop dispositions table
    op.drop_index(op.f('ix_dispositions_code'), table_name='dispositions')
    op.drop_index(op.f('ix_dispositions_id'), table_name='dispositions')
    op.drop_table('dispositions')
