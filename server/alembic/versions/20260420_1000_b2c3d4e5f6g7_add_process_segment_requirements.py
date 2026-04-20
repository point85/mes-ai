"""add_process_segment_requirements

ISA-95 Process Segment tables:
- step_equipment_requirements
- step_material_requirements
- route_steps.equipment_class_id FK

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f8
Create Date: 2026-04-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── equipment_class_id on route_steps ────────────────────────────
    op.add_column(
        "route_steps",
        sa.Column(
            "equipment_class_id",
            sa.Uuid(),
            sa.ForeignKey("equipment_classes.id"),
            nullable=True,
            comment="ISA-95 process segment: what class of equipment is required at this step",
        ),
    )
    op.create_index(
        "ix_route_steps_equipment_class_id",
        "route_steps",
        ["equipment_class_id"],
    )

    # ── step_equipment_requirements ──────────────────────────────────
    op.create_table(
        "step_equipment_requirements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("step_id", sa.Uuid(), sa.ForeignKey("route_steps.id"), nullable=False, index=True),
        sa.Column("equipment_id", sa.Uuid(), sa.ForeignKey("equipment.id"), nullable=False, index=True),
        sa.Column(
            "use_type", sa.String(20), nullable=False, server_default="preferred",
            comment="Use type: required, preferred, alternate",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("step_id", "equipment_id", name="uq_step_equip_req"),
    )

    # ── step_material_requirements ───────────────────────────────────
    op.create_table(
        "step_material_requirements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("step_id", sa.Uuid(), sa.ForeignKey("route_steps.id"), nullable=False, index=True),
        sa.Column("material_id", sa.Uuid(), sa.ForeignKey("material_definitions.id"), nullable=False, index=True),
        sa.Column("quantity", sa.Float(), nullable=False, comment="Quantity per unit/lot of finished product"),
        sa.Column(
            "uom", sa.String(20), sa.ForeignKey("units_of_measure.symbol"),
            nullable=False, server_default="EA",
            comment="Unit of measure for the quantity",
        ),
        sa.Column(
            "material_use", sa.String(20), nullable=False, server_default="consumed",
            comment="Material use: consumed, produced",
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0", comment="Sort order within the step"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("step_id", "material_id", name="uq_step_mat_req"),
    )


def downgrade() -> None:
    op.drop_table("step_material_requirements")
    op.drop_table("step_equipment_requirements")
    op.drop_index("ix_route_steps_equipment_class_id", table_name="route_steps")
    op.drop_column("route_steps", "equipment_class_id")
