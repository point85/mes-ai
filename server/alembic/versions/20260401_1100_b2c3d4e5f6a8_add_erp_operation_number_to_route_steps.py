"""Add erp_operation_number to route_steps table.

Stores the ERP operation/step number for outbound reporting back to ERP
(e.g. SAP OperationNumber '0010', Oracle OperationSequenceNumber '10').

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-01 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a8"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "route_steps",
        sa.Column(
            "erp_operation_number",
            sa.String(50),
            nullable=True,
            comment="ERP operation/step number for outbound reporting (e.g. '0010', '0020')",
        ),
    )


def downgrade() -> None:
    op.drop_column("route_steps", "erp_operation_number")
