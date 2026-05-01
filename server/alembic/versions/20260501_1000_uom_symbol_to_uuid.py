"""Change all UoM FK columns from symbol string to UUID

All tables that previously held a string FK pointing at
``units_of_measure.symbol`` are migrated to a UUID FK pointing at
``units_of_measure.id``.

Affected tables / columns:
  product_definitions:           uom          → uom_id
  bom_items:                     uom          → uom_id
  segment_parameters:            uom          → uom_id  (nullable)
  segment_material_requirements: uom          → uom_id
  material_definitions:          uom          → uom_id
  data_definitions:              uom          → uom_id  (nullable)
  equipment_materials:           design_speed_uom → design_speed_uom_id
                                 reject_uom   → reject_uom_id

Revision ID: a1b2c3d4e5f6
Revises: 5aefea3fbea4
Create Date: 2026-05-01 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "5aefea3fbea4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _migrate_uom_column(
    table: str,
    old_col: str,
    new_col: str,
    *,
    nullable: bool = False,
    fk_name: str | None = None,
) -> None:
    """Add new UUID column, populate from units_of_measure join, drop old column."""
    if fk_name is None:
        fk_name = f"fk_{table}_{new_col}_uom"

    # 1. Add new nullable UUID column
    op.add_column(table, sa.Column(new_col, sa.Uuid(), nullable=True))

    # 2. Populate from join
    op.execute(
        f"""
        UPDATE {table} t
        SET {new_col} = u.id
        FROM units_of_measure u
        WHERE u.symbol = t.{old_col}
        """
    )

    # 3. Set NOT NULL if required
    if not nullable:
        op.alter_column(table, new_col, nullable=False)

    # 4. Create FK constraint
    op.create_foreign_key(fk_name, table, "units_of_measure", [new_col], ["id"])

    # 5. Drop old string column
    op.drop_column(table, old_col)


def upgrade() -> None:
    _migrate_uom_column("product_definitions",          "uom", "uom_id")
    _migrate_uom_column("bom_items",                    "uom", "uom_id")
    _migrate_uom_column("segment_parameters",           "uom", "uom_id",   nullable=True)
    _migrate_uom_column("segment_material_requirements","uom", "uom_id")
    _migrate_uom_column("material_definitions",         "uom", "uom_id")
    _migrate_uom_column("data_definitions",             "uom", "uom_id",   nullable=True)
    _migrate_uom_column(
        "equipment_materials", "design_speed_uom", "design_speed_uom_id",
        fk_name="fk_equipment_materials_design_speed_uom_id_uom",
    )
    _migrate_uom_column(
        "equipment_materials", "reject_uom", "reject_uom_id",
        fk_name="fk_equipment_materials_reject_uom_id_uom",
    )


def downgrade() -> None:
    """Reverse: re-add symbol columns and drop UUID columns."""

    def _reverse(table: str, old_col: str, new_col: str, *, nullable: bool = False, fk_name: str | None = None) -> None:
        if fk_name is None:
            fk_name = f"fk_{table}_{new_col}_uom"
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.add_column(table, sa.Column(old_col, sa.String(20), nullable=True))
        op.execute(
            f"""
            UPDATE {table} t
            SET {old_col} = u.symbol
            FROM units_of_measure u
            WHERE u.id = t.{new_col}
            """
        )
        if not nullable:
            op.alter_column(table, old_col, nullable=False)
        op.drop_column(table, new_col)

    _reverse("equipment_materials", "reject_uom",       "reject_uom_id",
             fk_name="fk_equipment_materials_reject_uom_id_uom")
    _reverse("equipment_materials", "design_speed_uom", "design_speed_uom_id",
             fk_name="fk_equipment_materials_design_speed_uom_id_uom")
    _reverse("data_definitions",              "uom", "uom_id", nullable=True)
    _reverse("material_definitions",          "uom", "uom_id")
    _reverse("segment_material_requirements", "uom", "uom_id")
    _reverse("segment_parameters",            "uom", "uom_id", nullable=True)
    _reverse("bom_items",                     "uom", "uom_id")
    _reverse("product_definitions",           "uom", "uom_id")
