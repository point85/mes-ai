"""disposition_to_step_column

Replace the dispositions table with input_disposition and
disposition_category columns on route_steps.

Revision ID: m3n4o5p6q7r8
Revises: l3m4n5o6p7q8
Create Date: 2026-04-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'm3n4o5p6q7r8'
down_revision: Union[str, None] = 'l3m4n5o6p7q8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to route_steps
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

    # Drop the dispositions table
    op.drop_table('dispositions')


def downgrade() -> None:
    # Recreate the dispositions table
    op.create_table(
        'dispositions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('route_id', sa.Uuid(), nullable=False),
        sa.Column('route_step_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('category', sa.String(20), server_default='route', nullable=False),
        sa.Column('is_system', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['route_id'], ['process_routes.id']),
        sa.ForeignKeyConstraint(['route_step_id'], ['route_steps.id']),
    )

    # Drop the new columns
    op.drop_column('route_steps', 'disposition_category')
    op.drop_column('route_steps', 'input_disposition')
