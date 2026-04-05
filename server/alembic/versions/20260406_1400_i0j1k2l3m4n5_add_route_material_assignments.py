"""add route_material_assignments junction table

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-04-06 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "i0j1k2l3m4n5"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "route_material_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["process_routes.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["material_definitions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_id", "material_id", name="uq_route_material"),
    )
    op.create_index("ix_route_material_assignments_route_id", "route_material_assignments", ["route_id"])
    op.create_index("ix_route_material_assignments_material_id", "route_material_assignments", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_route_material_assignments_material_id", table_name="route_material_assignments")
    op.drop_index("ix_route_material_assignments_route_id", table_name="route_material_assignments")
    op.drop_table("route_material_assignments")
