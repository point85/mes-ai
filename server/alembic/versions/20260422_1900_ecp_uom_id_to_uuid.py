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


def _dialect() -> str:
    return op.get_bind().dialect.name


def _drop_fk_by_column(table: str, column: str, pg_name: str) -> None:
    """Drop a FK constraint — uses dynamic lookup on MySQL where auto-names differ."""
    if _dialect() == "mysql":
        result = op.get_bind().execute(sa.text(
            "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
            "AND COLUMN_NAME = :c AND REFERENCED_TABLE_NAME IS NOT NULL"
        ), {"t": table, "c": column})
        row = result.fetchone()
        if row:
            op.drop_constraint(row[0], table, type_="foreignkey")
    else:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(pg_name, type_="foreignkey")


def upgrade() -> None:
    dialect = _dialect()

    # 1) Drop existing FK
    _drop_fk_by_column(
        "equipment_class_properties", "uom_id",
        "equipment_class_properties_uom_id_fkey",
    )

    # 2) Add a temporary UUID column, populate by translating symbol -> id
    op.add_column(
        "equipment_class_properties",
        sa.Column("uom_id_new", sa.Uuid(), nullable=True),
    )
    if dialect == "mysql":
        op.execute(
            "UPDATE equipment_class_properties ecp "
            "JOIN units_of_measure uom ON uom.symbol = ecp.uom_id "
            "SET ecp.uom_id_new = uom.id"
        )
    else:
        op.execute(
            "UPDATE equipment_class_properties ecp "
            "SET uom_id_new = uom.id "
            "FROM units_of_measure uom "
            "WHERE uom.symbol = ecp.uom_id"
        )

    # 3) Drop old column and rename new one into place
    op.drop_column("equipment_class_properties", "uom_id")
    op.alter_column(
        "equipment_class_properties",
        "uom_id_new",
        new_column_name="uom_id",
        existing_type=sa.Uuid(),
        existing_nullable=True,
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
    dialect = _dialect()
    _drop_fk_by_column(
        "equipment_class_properties", "uom_id",
        "equipment_class_properties_uom_id_fkey",
    )

    op.add_column(
        "equipment_class_properties",
        sa.Column("uom_id_old", sa.String(length=20), nullable=True),
    )
    if dialect == "mysql":
        op.execute(
            "UPDATE equipment_class_properties ecp "
            "JOIN units_of_measure uom ON uom.id = ecp.uom_id "
            "SET ecp.uom_id_old = uom.symbol"
        )
    else:
        op.execute(
            "UPDATE equipment_class_properties ecp "
            "SET uom_id_old = uom.symbol "
            "FROM units_of_measure uom "
            "WHERE uom.id = ecp.uom_id"
        )


    op.drop_column("equipment_class_properties", "uom_id")
    op.alter_column(
        "equipment_class_properties",
        "uom_id_old",
        new_column_name="uom_id",
        existing_type=sa.String(length=20),
        existing_nullable=True,
    )

    op.create_foreign_key(
        "equipment_class_properties_uom_id_fkey",
        "equipment_class_properties",
        "units_of_measure",
        ["uom_id"],
        ["symbol"],
    )
