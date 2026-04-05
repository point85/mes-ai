"""add route_product_assignments junction table and make product_id nullable

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-04-06 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "h9i0j1k2l3m4"
down_revision = "g8h9i0j1k2l3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make product_id nullable on process_routes (routes can exist without a product)
    op.alter_column(
        "process_routes",
        "product_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Create route_product_assignments junction table
    op.create_table(
        "route_product_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["process_routes.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product_definitions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_id", "product_id", name="uq_route_product"),
    )
    op.create_index("ix_route_product_assignments_route_id", "route_product_assignments", ["route_id"])
    op.create_index("ix_route_product_assignments_product_id", "route_product_assignments", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_route_product_assignments_product_id", table_name="route_product_assignments")
    op.drop_index("ix_route_product_assignments_route_id", table_name="route_product_assignments")
    op.drop_table("route_product_assignments")

    op.alter_column(
        "process_routes",
        "product_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
