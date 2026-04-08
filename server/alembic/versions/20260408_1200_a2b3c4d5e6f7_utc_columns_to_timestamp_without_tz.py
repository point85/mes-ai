"""utc columns to timestamp without timezone

Revision ID: a2b3c4d5e6f7
Revises: 90a8e6b0846b
Create Date: 2026-04-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = '90a8e6b0846b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All tables that inherit BaseModel (have created_at_utc / updated_at_utc)
ALL_TABLES = [
    'areas', 'bills_of_material', 'bom_items', 'data_definitions',
    'data_points', 'equipment', 'equipment_materials',
    'equipment_state_logs', 'equipment_state_models',
    'erp_inbound_orders', 'erp_outbound_queue', 'idp_group_mappings',
    'lot_history', 'lots', 'material_consumptions',
    'material_definitions', 'material_lots', 'non_conformances',
    'permissions', 'plugin_config', 'process_routes',
    'product_definitions', 'production_counters', 'production_lines',
    'production_orders', 'quality_tests', 'reasons', 'roles',
    'route_material_assignments', 'route_product_assignments',
    'route_steps', 'sites', 'step_parameters', 'step_transitions',
    'test_results', 'unit_history', 'units', 'units_of_measure',
    'user_roles', 'users', 'work_cells',
]

# Model-specific _utc columns beyond created_at_utc / updated_at_utc
EXTRA_COLUMNS: dict[str, list[str]] = {
    'data_points': ['collected_at_utc'],
    'equipment_state_logs': ['started_at_utc', 'ended_at_utc'],
    'erp_inbound_orders': ['next_retry_at_utc', 'processed_at_utc'],
    'erp_outbound_queue': ['next_retry_at_utc'],
    'lot_history': ['entered_at_utc', 'exited_at_utc'],
    'material_consumptions': ['consumed_at_utc'],
    'non_conformances': ['resolved_at_utc'],
    'production_orders': [
        'planned_start_utc', 'planned_end_utc',
        'actual_start_utc', 'actual_end_utc',
    ],
    'test_results': ['tested_at_utc'],
    'unit_history': ['entered_at_utc', 'exited_at_utc'],
    'users': ['last_login_utc'],
}


def _alter_column(table: str, column: str, to_naive: bool) -> None:
    """Convert a single column between TIMESTAMPTZ and TIMESTAMP."""
    if to_naive:
        # TIMESTAMPTZ → TIMESTAMP: extract the UTC value as naive datetime
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        )
    else:
        # TIMESTAMP → TIMESTAMPTZ: treat naive value as UTC
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        )


def upgrade() -> None:
    # Convert all _utc columns from TIMESTAMPTZ → TIMESTAMP (naive UTC)
    for table in ALL_TABLES:
        _alter_column(table, 'created_at_utc', to_naive=True)
        _alter_column(table, 'updated_at_utc', to_naive=True)
        for col in EXTRA_COLUMNS.get(table, []):
            _alter_column(table, col, to_naive=True)


def downgrade() -> None:
    # Revert: TIMESTAMP → TIMESTAMPTZ
    for table in ALL_TABLES:
        _alter_column(table, 'created_at_utc', to_naive=False)
        _alter_column(table, 'updated_at_utc', to_naive=False)
        for col in EXTRA_COLUMNS.get(table, []):
            _alter_column(table, col, to_naive=False)
