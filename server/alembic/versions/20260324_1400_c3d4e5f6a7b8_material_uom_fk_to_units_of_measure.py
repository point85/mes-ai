"""uom FK to units_of_measure.symbol on all tables

Adds foreign-key constraints from every `uom` column to
`units_of_measure.symbol` so that every UOM reference is validated:
  - material_definitions.uom
  - product_definitions.uom
  - bom_items.uom
  - step_parameters.uom     (nullable)
  - data_definitions.uom    (nullable)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-24 14:00:00.000000

"""
from typing import Sequence, Union

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_SPECS = [
    ("fk_material_definitions_uom",  "material_definitions"),
    ("fk_product_definitions_uom",   "product_definitions"),
    ("fk_bom_items_uom",             "bom_items"),
    ("fk_step_parameters_uom",       "step_parameters"),
    ("fk_data_definitions_uom",      "data_definitions"),
]


def upgrade() -> None:
    # Ensure EA and PC exist in units_of_measure before adding FK constraints.
    # These were added to the seed data but may be missing in databases seeded
    # before this migration.
    conn = op.get_bind()
    uom_table = sa.table(
        "units_of_measure",
        sa.column("id", sa.dialects.postgresql.UUID),
        sa.column("symbol", sa.String),
        sa.column("name", sa.String),
        sa.column("uom_type", sa.String),
        sa.column("multiplier", sa.Float),
        sa.column("offset", sa.Float),
        sa.column("is_builtin", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    for symbol, name in [("EA", "each"), ("PC", "piece")]:
        exists = conn.execute(
            sa.select(uom_table.c.symbol).where(uom_table.c.symbol == symbol)
        ).first()
        if not exists:
            conn.execute(uom_table.insert().values(
                id=str(uuid.uuid4()),
                symbol=symbol,
                name=name,
                uom_type="count",
                multiplier=1.0,
                offset=0.0,
                is_builtin=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            ))

    for name, table in _FK_SPECS:
        op.create_foreign_key(
            name,
            table,
            "units_of_measure",
            ["uom"],
            ["symbol"],
        )


def downgrade() -> None:
    for name, table in _FK_SPECS:
        op.drop_constraint(name, table, type_="foreignkey")
