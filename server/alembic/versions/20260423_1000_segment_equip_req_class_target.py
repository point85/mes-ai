"""segment_equipment_requirements: add equipment_class_id target

Adds an optional ``equipment_class_id`` FK to
``segment_equipment_requirements`` so a ProcessSegment can require an
equipment *class* (ISA-95 EquipmentSegmentSpecification → EquipmentClass)
in addition to requiring a specific ``Equipment``.

Exactly one of ``equipment_class_id`` / ``equipment_id`` must be set per
row — enforced by a CHECK constraint.  ``equipment_id`` becomes nullable.

Revision ID: b2c9e0117f31
Revises: a7f3c1d9e4b2
Create Date: 2026-04-23 10:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c9e0117f31"
down_revision: Union[str, None] = "a7f3c1d9e4b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add the class-target column (nullable).
    op.add_column(
        "segment_equipment_requirements",
        sa.Column("equipment_class_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "segment_equipment_requirements_equipment_class_id_fkey",
        "segment_equipment_requirements", "equipment_classes",
        ["equipment_class_id"], ["id"],
    )
    op.create_index(
        "ix_segment_equipment_requirements_equipment_class_id",
        "segment_equipment_requirements", ["equipment_class_id"],
    )

    # 2) Relax equipment_id to nullable (class-target rows have NULL here).
    op.alter_column(
        "segment_equipment_requirements",
        "equipment_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # 3) Enforce exactly-one-of target via CHECK constraint.
    op.create_check_constraint(
        "ck_segment_equip_req_one_target",
        "segment_equipment_requirements",
        "(equipment_id IS NULL) <> (equipment_class_id IS NULL)",
    )

    # 4) Add a second unique constraint covering the class-target case.
    op.create_unique_constraint(
        "uq_segment_equip_class_req",
        "segment_equipment_requirements",
        ["step_id", "equipment_class_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_segment_equip_class_req",
        "segment_equipment_requirements",
        type_="unique",
    )
    op.drop_constraint(
        "ck_segment_equip_req_one_target",
        "segment_equipment_requirements",
        type_="check",
    )
    # Purge any rows that rely on the class target before making equipment_id
    # NOT NULL again — they would otherwise violate the restored constraint.
    op.execute(
        "DELETE FROM segment_equipment_requirements "
        "WHERE equipment_id IS NULL"
    )
    op.alter_column(
        "segment_equipment_requirements",
        "equipment_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_index(
        "ix_segment_equipment_requirements_equipment_class_id",
        table_name="segment_equipment_requirements",
    )
    op.drop_constraint(
        "segment_equipment_requirements_equipment_class_id_fkey",
        "segment_equipment_requirements",
        type_="foreignkey",
    )
    op.drop_column("segment_equipment_requirements", "equipment_class_id")
