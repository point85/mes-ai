"""drop quality tables

Revision ID: ee55ff66aa77
Revises: bb22cc33dd44
Create Date: 2026-05-06 10:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ee55ff66aa77"
down_revision: str = "bb22cc33dd44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop defect_code_id FK columns from tables that reference defect_codes
    op.drop_column("units", "defect_code_id")
    op.drop_column("lots", "defect_code_id")
    op.drop_column("segment_response_units", "defect_code_id")
    op.drop_column("segment_response_lots", "defect_code_id")

    # Drop quality tables in FK-dependency order: child tables first
    op.drop_table("non_conformances")
    op.drop_table("test_results")
    op.drop_table("quality_tests")
    op.drop_table("defect_codes")


def downgrade() -> None:
    # Recreate tables in reverse order
    op.create_table(
        "defect_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "quality_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("test_type", sa.String(length=32), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["step_id"], ["process_segments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "test_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("measured_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["production_lots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_id"], ["quality_tests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["production_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "non_conformances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nc_number", sa.String(length=64), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("defect_code_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("disposition_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["defect_code_id"], ["defect_codes.id"]),
        sa.ForeignKeyConstraint(["lot_id"], ["production_lots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_result_id"], ["test_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["production_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nc_number"),
    )
    # Restore defect_code_id FK columns
    op.add_column("units", sa.Column("defect_code_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("lots", sa.Column("defect_code_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("segment_response_units", sa.Column("defect_code_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("segment_response_lots", sa.Column("defect_code_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_units_defect_code_id", "units", "defect_codes", ["defect_code_id"], ["id"])
    op.create_foreign_key("fk_lots_defect_code_id", "lots", "defect_codes", ["defect_code_id"], ["id"])
    op.create_foreign_key("fk_sru_defect_code_id", "segment_response_units", "defect_codes", ["defect_code_id"], ["id"])
    op.create_foreign_key("fk_srl_defect_code_id", "segment_response_lots", "defect_codes", ["defect_code_id"], ["id"])
