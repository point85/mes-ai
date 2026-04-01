"""Add max_queue_depth to equipment, material_id to units/lots.

Revision ID: a1b2c3d4e5f7
Revises: f6a7b8c9d0e1
Create Date: 2026-04-01 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Equipment: max_queue_depth (null = unlimited)
    op.add_column(
        "equipment",
        sa.Column(
            "max_queue_depth", sa.Integer(), nullable=True,
            comment="Max WIP items (units + lots) allowed in input queue. Null = unlimited.",
        ),
    )

    # Unit: material_id FK for dispatch capability matching
    op.add_column(
        "units",
        sa.Column(
            "material_id", UUID(as_uuid=True), nullable=True,
            comment="Output material produced by this unit. Used for dispatch capability matching.",
        ),
    )
    op.create_index("ix_units_material_id", "units", ["material_id"])
    op.create_foreign_key(
        "fk_units_material_id", "units",
        "material_definitions", ["material_id"], ["id"],
    )

    # Lot: material_id FK for dispatch capability matching
    op.add_column(
        "lots",
        sa.Column(
            "material_id", UUID(as_uuid=True), nullable=True,
            comment="Output material produced by this lot. Used for dispatch capability matching.",
        ),
    )
    op.create_index("ix_lots_material_id", "lots", ["material_id"])
    op.create_foreign_key(
        "fk_lots_material_id", "lots",
        "material_definitions", ["material_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_lots_material_id", "lots", type_="foreignkey")
    op.drop_index("ix_lots_material_id", "lots")
    op.drop_column("lots", "material_id")

    op.drop_constraint("fk_units_material_id", "units", type_="foreignkey")
    op.drop_index("ix_units_material_id", "units")
    op.drop_column("units", "material_id")

    op.drop_column("equipment", "max_queue_depth")
