"""add_dispositions_table

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-04-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l3m4n5o6p7q8'
down_revision: Union[str, None] = 'k2l3m4n5o6p7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dispositions',
        sa.Column('route_id', sa.UUID(), nullable=False, comment='Route this disposition belongs to'),
        sa.Column('route_step_id', sa.UUID(), nullable=False, comment='Destination step this disposition routes to'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Unique display name within the route'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='Optional description of this disposition'),
        sa.Column('category', sa.String(length=20), nullable=False, comment='Disposition category: route, hold, scrap'),
        sa.Column('is_system', sa.Boolean(), nullable=False, comment='True for auto-created system dispositions'),
        sa.Column('id', sa.UUID(), nullable=False, comment='Unique identifier for the entity'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='Timestamp when the entity was created'),
        sa.Column('created_at_utc', sa.DateTime(), nullable=True, comment='Timestamp when the entity was created (UTC)'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='Timestamp when the entity was last updated'),
        sa.Column('updated_at_utc', sa.DateTime(), nullable=True, comment='Timestamp when the entity was last updated (UTC)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Soft delete flag. False means the entity is logically deleted.'),
        sa.ForeignKeyConstraint(['route_id'], ['process_routes.id']),
        sa.ForeignKeyConstraint(['route_step_id'], ['route_steps.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('route_id', 'name', name='uq_disposition_route_name'),
    )
    op.create_index(op.f('ix_dispositions_id'), 'dispositions', ['id'], unique=False)
    op.create_index(op.f('ix_dispositions_route_id'), 'dispositions', ['route_id'], unique=False)
    op.create_index(op.f('ix_dispositions_route_step_id'), 'dispositions', ['route_step_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_dispositions_route_step_id'), table_name='dispositions')
    op.drop_index(op.f('ix_dispositions_route_id'), table_name='dispositions')
    op.drop_index(op.f('ix_dispositions_id'), table_name='dispositions')
    op.drop_table('dispositions')
