"""add_equipment_capability_model

ISA-95 Part 2 Equipment Capability tables:
- equipment_classes
- equipment_class_properties
- equipment_capabilities
- equipment_capability_properties
- equipment.equipment_class_id FK

Revision ID: a1b2c3d4e5f8
Revises: 8dd5eb1d4d8c
Create Date: 2026-04-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f8"
down_revision: Union[str, None] = "8dd5eb1d4d8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── equipment_classes ─────────────────────────────────────────
    op.create_table(
        "equipment_classes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=False), nullable=True),
    )

    # ── equipment_class_properties ────────────────────────────────
    op.create_table(
        "equipment_class_properties",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("equipment_class_id", sa.Uuid(), sa.ForeignKey("equipment_classes.id"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data_type", sa.String(20), nullable=False, server_default="string"),
        sa.Column("uom_id", sa.String(20), sa.ForeignKey("units_of_measure.symbol"), nullable=True),
        sa.Column("default_value", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.UniqueConstraint("equipment_class_id", "name", name="uq_ecp_class_name"),
    )

    # ── equipment_capabilities ────────────────────────────────────
    op.create_table(
        "equipment_capabilities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("equipment_id", sa.Uuid(), sa.ForeignKey("equipment.id"), nullable=False, index=True),
        sa.Column("equipment_class_id", sa.Uuid(), sa.ForeignKey("equipment_classes.id"), nullable=True, index=True),
        sa.Column("capability_type", sa.String(20), nullable=False, server_default="available"),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=False), nullable=True),
    )

    # ── equipment_capability_properties ───────────────────────────
    op.create_table(
        "equipment_capability_properties",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("capability_id", sa.Uuid(), sa.ForeignKey("equipment_capabilities.id"), nullable=False, index=True),
        sa.Column("class_property_id", sa.Uuid(), sa.ForeignKey("equipment_class_properties.id"), nullable=False, index=True),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=False), nullable=True),
        sa.UniqueConstraint("capability_id", "class_property_id", name="uq_ecap_prop"),
    )

    # ── Add equipment_class_id FK to equipment table ──────────────
    op.add_column(
        "equipment",
        sa.Column("equipment_class_id", sa.Uuid(), sa.ForeignKey("equipment_classes.id"), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("equipment", "equipment_class_id")
    op.drop_table("equipment_capability_properties")
    op.drop_table("equipment_capabilities")
    op.drop_table("equipment_class_properties")
    op.drop_table("equipment_classes")
