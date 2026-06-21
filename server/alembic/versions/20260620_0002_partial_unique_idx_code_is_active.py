"""Convert non-partial unique indexes on code to partial (WHERE is_active = TRUE).

Revision ID: 20260620_0002
Revises: 20260620_0001
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260620_0002"
down_revision = "20260620_0001"
branch_labels = None
depends_on = None

# Tables whose code index must be partial-unique (soft-delete pattern).
_TABLES = [
    "areas",
    "data_definitions",
    "dispositions",
    "equipment",
    "equipment_classes",
    "production_lines",
    "sites",
    "storage_locations",
    "work_cells",
]


def upgrade() -> None:
    for table in _TABLES:
        index_name = f"ix_{table}_code"
        op.drop_index(index_name, table_name=table)
        op.create_index(
            index_name,
            table,
            ["code"],
            unique=True,
            postgresql_where=sa.text("is_active = TRUE"),
        )


def downgrade() -> None:
    for table in _TABLES:
        index_name = f"ix_{table}_code"
        op.drop_index(index_name, table_name=table)
        op.create_index(index_name, table, ["code"], unique=True)
