"""Add current material setup columns to equipment.

Adds current_material_id, current_job_number, and material_setup_at
to the equipment table for tracking runtime material setup state.

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-04-16 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "k2l3m4n5o6p7"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "equipment",
        sa.Column(
            "current_material_id",
            sa.Uuid(),
            sa.ForeignKey("equipment_materials.id"),
            nullable=True,
            comment="Currently running equipment-material setup. Null = no material set up.",
        ),
    )
    op.add_column(
        "equipment",
        sa.Column(
            "current_job_number",
            sa.String(64),
            nullable=True,
            comment="Job / batch identifier for the current material run.",
        ),
    )
    op.add_column(
        "equipment",
        sa.Column(
            "material_setup_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Local timestamp when the current material was set up.",
        ),
    )
    op.add_column(
        "equipment",
        sa.Column(
            "material_setup_at_utc",
            sa.DateTime(timezone=False),
            nullable=True,
            comment="UTC timestamp when the current material was set up.",
        ),
    )


def downgrade() -> None:
    op.drop_column("equipment", "material_setup_at_utc")
    op.drop_column("equipment", "material_setup_at")
    op.drop_column("equipment", "current_job_number")
    op.drop_column("equipment", "current_material_id")
