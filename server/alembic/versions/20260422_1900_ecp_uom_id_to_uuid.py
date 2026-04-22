"""equipment_class_properties.uom_id: VARCHAR(symbol) -> UUID(units_of_measure.id)

Revision ID: a7f3c1d9e4b2
Revises: 4c5fc92755a4
Create Date: 2026-04-22 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7f3c1d9e4b2"
down_revision: Union[str, None] = "4c5fc92755a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Drop existing FK (name follows Alembic default: equipment_class_properties_uom_id_fkey)
    with op.batch_alter_table("equipment_class_properties") as batch:
        batch.drop_constraint(
            "equipment_class_properties_uom_id_fkey", type_="foreignkey",
        )

    # 2) Add a temporary UUID column, populate by translating symbol -> id
    op.add_column(
        "equipment_class_properties",
        sa.Column("uom_id_new", sa.Uuid(), nullable=True),
    )
    op.execute(
        """
        UPDATE equipment_class_properties ecp
        SET uom_id_new = uom.id
        FROM units_of_measure uom
        WHERE uom.symbol = ecp.uom_id
        """
    )

    # 3) Drop old column and rename new one into place
    op.drop_column("equipment_class_properties", "uom_id")
    op.alter_column(
        "equipment_class_properties",
        "uom_id_new",
        new_column_name="uom_id",
    )

    # 4) Re-add FK to units_of_measure.id
    op.create_foreign_key(
        "equipment_class_properties_uom_id_fkey",
        "equipment_class_properties",
        "units_of_measure",
        ["uom_id"],
        ["id"],
    )


def downgrade() -> None:
    # Reverse: UUID -> VARCHAR(symbol)
    with op.batch_alter_table("equipment_class_properties") as batch:
        batch.drop_constraint(
            "equipment_class_properties_uom_id_fkey", type_="foreignkey",
        )

    op.add_column(
        "equipment_class_properties",
        sa.Column("uom_id_old", sa.String(length=20), nullable=True),
    )
    op.execute(
        """
        UPDATE equipment_class_properties ecp
        SET uom_id_old = uom.symbol
        FROM units_of_measure uom
        WHERE uom.id = ecp.uom_id
        """
    )

    op.drop_column("equipment_class_properties", "uom_id")
    op.alter_column(
        "equipment_class_properties",
        "uom_id_old",
        new_column_name="uom_id",
    )

    op.create_foreign_key(
        "equipment_class_properties_uom_id_fkey",
        "equipment_class_properties",
        "units_of_measure",
        ["uom_id"],
        ["symbol"],
    )
