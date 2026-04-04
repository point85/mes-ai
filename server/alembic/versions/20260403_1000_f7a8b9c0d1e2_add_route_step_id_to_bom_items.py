"""Add route_step_id FK to bom_items table.

Allows a BOM line item to be associated with a specific route step,
indicating which operation consumes this material.

Revision ID: f7a8b9c0d1e2
Revises: e386092bb59c
Create Date: 2026-04-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "e386092bb59c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bom_items",
        sa.Column(
            "route_step_id",
            sa.Uuid(),
            sa.ForeignKey("route_steps.id"),
            nullable=True,
            comment="Optional FK to route step where this material is consumed",
        ),
    )
    op.create_index(
        "ix_bom_items_route_step_id", "bom_items", ["route_step_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_bom_items_route_step_id", table_name="bom_items")
    op.drop_column("bom_items", "route_step_id")
