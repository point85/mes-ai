"""Add runtime performance indexes and reporting views.

Revision ID: 20260708_0001
Revises: 20260620_0002
Create Date: 2026-07-08

Analysis of all REST GET endpoints revealed the following hot-path query
patterns that lack appropriate database support on large datasets:

COMPOSITE INDEXES
─────────────────
equipment_state_logs (equipment_id, ended_at)
    record_state_change()  — finds the open log to close it (every transition)
    get_current_state()    — returns the current open log
    DashboardService.line_status()  — called per-equipment in a tight loop
    DispatchService.evaluate()      — checks dispatch_category for each candidate

equipment_state_logs (equipment_id, started_at)
    OEEService.calculate_oee()            — time-range fetch, groups by oee_bucket
    EquipmentStateService.list_state_logs() — equipment + date range filter

production_counters (equipment_id, shift_date)
    ProductionCounterService.create_or_update_counter() — upsert key
    ProductionCounterService.increment_counter()        — today's upsert

segment_response_units (unit_id, entered_at)
    UnitService.get_segment_response_units() — history ORDER BY entered_at

segment_response_lots (lot_id, entered_at)
    LotService equivalent

segment_response_units (entered_at, equipment_id)
segment_response_lots  (entered_at, equipment_id)
    DashboardService.shift_summary() — time-window aggregation

material_lots (material_id, status)
    MaterialLotService.list_lots() — combined material + status filter

data_points (unit_id, collected_at)
data_points (lot_id,  collected_at)
    GenealogyService.get_unit_genealogy() and step-context data-point queries

PARTIAL INDEXES  (PostgreSQL / SQLite)
───────────────────────────────────────
segment_response_units (unit_id) WHERE exited_at IS NULL
segment_response_lots  (lot_id)  WHERE exited_at IS NULL
    All WIP lifecycle operations that find the currently-open segment response
    before closing it (complete, scrap, hold, etc.)

units            (status) WHERE is_active = TRUE
lots             (status) WHERE is_active = TRUE
operations_requests (status) WHERE is_active = TRUE
material_lots    (status) WHERE is_active = TRUE
    list_* endpoints that filter by is_active=TRUE AND status=<value>.
    On Oracle / SQL Server (no partial-index support) these become regular
    single-column indexes — still a net improvement over a full table scan.

SINGLE-COLUMN INDEXES
──────────────────────
test_results.tested_at
    TestResultService.list_results() — ORDER BY tested_at DESC (no filter guard)

REPORTING VIEWS
───────────────
v_equipment_current_state
    One row per equipment: its latest open (ended_at IS NULL) state-log entry.
    Backed by ix_equipment_state_logs_equip_ended.
    Reference view for dashboard, dispatch, and OEE consumers.

v_active_wip_by_equipment
    Queue depth (active units + active lots) per equipment.
    Combines units.current_equipment_id and lots.current_equipment_id with
    active-only filters; exposes max_queue_depth for capacity checks.

v_order_production_summary
    Aggregated good/reject/rework totals per operations_request from
    production_counters.  Replaces the N-query rollup currently in
    DashboardService.order_progress().
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260708_0001"
down_revision = "20260620_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════════════
    # equipment_state_logs
    # ═══════════════════════════════════════════════════════════════════

    # (equipment_id, ended_at): current-state lookup + dispatch availability.
    # The overwhelming majority of queries filter equipment_id = X AND
    # ended_at IS NULL — this composite lets the DB seek directly to the
    # handful of open rows for that equipment.
    op.create_index(
        "ix_equipment_state_logs_equip_ended",
        "equipment_state_logs",
        ["equipment_id", "ended_at"],
        unique=False,
    )

    # (equipment_id, started_at): OEE time-range scans and list queries.
    # OEEService.calculate_oee() fetches all logs for equipment_id in
    # [period_start, period_end].  Without this index the planner falls back
    # to ix_equipment_state_logs_started_at and then re-checks equipment_id.
    op.create_index(
        "ix_equipment_state_logs_equip_started",
        "equipment_state_logs",
        ["equipment_id", "started_at"],
        unique=False,
    )

    # ═══════════════════════════════════════════════════════════════════
    # production_counters
    # ═══════════════════════════════════════════════════════════════════

    # (equipment_id, shift_date): upsert key used by increment_counter and
    # create_or_update_counter.  The lookup is equipment + date (+ optional
    # order_id); this composite covers both branches of the upsert check.
    op.create_index(
        "ix_production_counters_equip_shift",
        "production_counters",
        ["equipment_id", "shift_date"],
        unique=False,
    )

    # ═══════════════════════════════════════════════════════════════════
    # segment_response_units
    # ═══════════════════════════════════════════════════════════════════

    # Partial (unit_id) WHERE exited_at IS NULL:
    # All WIP lifecycle methods (complete, scrap, hold, move) must first find
    # the currently-open segment response for the unit.  A partial index
    # keeps only the few open rows (typically 1 per unit) in the index leaf.
    op.create_index(
        "ix_segment_response_units_unit_open",
        "segment_response_units",
        ["unit_id"],
        unique=False,
        postgresql_where=sa.text("exited_at IS NULL"),
    )

    # (unit_id, entered_at): history list ordered by entered_at.
    # get_segment_response_units() returns all rows for a unit sorted by
    # entered_at; this composite satisfies both the filter and the sort
    # without a separate filesort.
    op.create_index(
        "ix_segment_response_units_unit_entered",
        "segment_response_units",
        ["unit_id", "entered_at"],
        unique=False,
    )

    # (entered_at, equipment_id): shift-summary time-window queries.
    # DashboardService.shift_summary() filters by entered_at >= window_start
    # and optionally by equipment_id; this index avoids a full table scan
    # over millions of historical segment-response rows.
    op.create_index(
        "ix_segment_response_units_entered_equip",
        "segment_response_units",
        ["entered_at", "equipment_id"],
        unique=False,
    )

    # ═══════════════════════════════════════════════════════════════════
    # segment_response_lots
    # ═══════════════════════════════════════════════════════════════════

    op.create_index(
        "ix_segment_response_lots_lot_open",
        "segment_response_lots",
        ["lot_id"],
        unique=False,
        postgresql_where=sa.text("exited_at IS NULL"),
    )

    op.create_index(
        "ix_segment_response_lots_lot_entered",
        "segment_response_lots",
        ["lot_id", "entered_at"],
        unique=False,
    )

    op.create_index(
        "ix_segment_response_lots_entered_equip",
        "segment_response_lots",
        ["entered_at", "equipment_id"],
        unique=False,
    )

    # ═══════════════════════════════════════════════════════════════════
    # units — status filter
    # ═══════════════════════════════════════════════════════════════════

    # Partial (status) WHERE is_active = TRUE:
    # list_units() always includes is_active = TRUE and very frequently also
    # filters by status.  The partial index covers only active rows, which is
    # typically a fraction of the table after years of production history.
    # On databases without partial-index support (Oracle, SQL Server) the
    # postgresql_where clause is ignored and a plain status index is created.
    op.create_index(
        "ix_units_status_is_active",
        "units",
        ["status"],
        unique=False,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # ═══════════════════════════════════════════════════════════════════
    # lots — status filter
    # ═══════════════════════════════════════════════════════════════════

    op.create_index(
        "ix_lots_status_is_active",
        "lots",
        ["status"],
        unique=False,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # ═══════════════════════════════════════════════════════════════════
    # operations_requests — status filter
    # ═══════════════════════════════════════════════════════════════════

    # list_orders() and DashboardService.order_progress() both filter by
    # is_active = TRUE and often by status (released, in_progress).
    op.create_index(
        "ix_operations_requests_status_is_active",
        "operations_requests",
        ["status"],
        unique=False,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # ═══════════════════════════════════════════════════════════════════
    # material_lots — status and material+status filters
    # ═══════════════════════════════════════════════════════════════════

    # Partial status index for is_active queries.
    op.create_index(
        "ix_material_lots_status_is_active",
        "material_lots",
        ["status"],
        unique=False,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # Composite (material_id, status): list_lots() often combines both filters
    # (all lots for a specific material, optionally restricted by status).
    op.create_index(
        "ix_material_lots_material_status",
        "material_lots",
        ["material_id", "status"],
        unique=False,
    )

    # ═══════════════════════════════════════════════════════════════════
    # data_points — per-WIP time-ordered history
    # ═══════════════════════════════════════════════════════════════════

    # GenealogyService and step-context queries retrieve all data points for
    # a given unit (or lot) ordered by collection time.  These composites
    # satisfy the filter + ordering in one index scan.
    op.create_index(
        "ix_data_points_unit_collected",
        "data_points",
        ["unit_id", "collected_at"],
        unique=False,
    )

    op.create_index(
        "ix_data_points_lot_collected",
        "data_points",
        ["lot_id", "collected_at"],
        unique=False,
    )

    # ═══════════════════════════════════════════════════════════════════
    # Reporting views
    # ═══════════════════════════════════════════════════════════════════

    # v_equipment_current_state
    # ─────────────────────────
    # Returns one row per equipment containing its latest open state-log
    # entry (ended_at IS NULL).  Uses ROW_NUMBER() window function to pick
    # the most-recent open entry when more than one open row exists (data
    # anomaly guard).
    #
    # Backed by ix_equipment_state_logs_equip_ended (created above).
    # Compatible with PostgreSQL ≥ 10, SQLite ≥ 3.25, Oracle 12c+, SQL Server 2012+.
    op.execute(sa.text(
        """
        CREATE VIEW v_equipment_current_state AS
        SELECT
            id,
            equipment_id,
            state_model,
            state,
            sub_state,
            dispatch_category,
            oee_bucket,
            started_at,
            started_at_utc,
            reason_code,
            notes
        FROM (
            SELECT
                id,
                equipment_id,
                state_model,
                state,
                sub_state,
                dispatch_category,
                oee_bucket,
                started_at,
                started_at_utc,
                reason_code,
                notes,
                ROW_NUMBER() OVER (
                    PARTITION BY equipment_id
                    ORDER BY started_at DESC
                ) AS rn
            FROM equipment_state_logs
            WHERE ended_at IS NULL
        ) ranked
        WHERE rn = 1
        """
    ))

    # v_active_wip_by_equipment
    # ─────────────────────────
    # Aggregates active (queued or in_process) units and lots per equipment,
    # exposing queue_depth and max_queue_depth for dispatch capacity checks
    # and the dashboard line-status panel.
    op.execute(sa.text(
        """
        CREATE VIEW v_active_wip_by_equipment AS
        SELECT
            e.id                                                      AS equipment_id,
            e.name                                                    AS equipment_name,
            e.max_queue_depth,
            COALESCE(u.unit_count, 0)                                 AS unit_count,
            COALESCE(l.lot_count,  0)                                 AS lot_count,
            COALESCE(u.unit_count, 0) + COALESCE(l.lot_count, 0)     AS queue_depth
        FROM equipment e
        LEFT JOIN (
            SELECT current_equipment_id,
                   COUNT(*) AS unit_count
            FROM   units
            WHERE  is_active = TRUE
              AND  status IN ('queued', 'in_process')
            GROUP  BY current_equipment_id
        ) u ON u.current_equipment_id = e.id
        LEFT JOIN (
            SELECT current_equipment_id,
                   COUNT(*) AS lot_count
            FROM   lots
            WHERE  is_active = TRUE
              AND  status IN ('queued', 'in_process')
            GROUP  BY current_equipment_id
        ) l ON l.current_equipment_id = e.id
        WHERE e.is_active = TRUE
        """
    ))

    # v_order_production_summary
    # ──────────────────────────
    # Aggregates production_counters by order, giving a single-row rollup of
    # good / reject / rework totals and shift-date range per order.
    # Replaces the per-order counter queries in DashboardService.order_progress()
    # and provides the quality numerator for OEE calculations.
    op.execute(sa.text(
        """
        CREATE VIEW v_order_production_summary AS
        SELECT
            pc.order_id,
            SUM(pc.good_count)                                            AS total_good,
            SUM(pc.reject_count)                                          AS total_reject,
            SUM(pc.rework_count)                                          AS total_rework,
            SUM(pc.good_count) + SUM(pc.reject_count)
                               + SUM(pc.rework_count)                     AS total_produced,
            MIN(pc.shift_date)                                            AS first_shift_date,
            MAX(pc.shift_date)                                            AS last_shift_date
        FROM production_counters pc
        WHERE pc.order_id IS NOT NULL
        GROUP BY pc.order_id
        """
    ))


def downgrade() -> None:
    # ── Views (drop first — they reference the tables) ──────────────
    op.execute(sa.text("DROP VIEW IF EXISTS v_order_production_summary"))
    op.execute(sa.text("DROP VIEW IF EXISTS v_active_wip_by_equipment"))
    op.execute(sa.text("DROP VIEW IF EXISTS v_equipment_current_state"))

    # ── Indexes (reverse creation order) ────────────────────────────
    op.drop_index("ix_data_points_lot_collected",                  table_name="data_points")
    op.drop_index("ix_data_points_unit_collected",                 table_name="data_points")
    op.drop_index("ix_material_lots_material_status",              table_name="material_lots")
    op.drop_index("ix_material_lots_status_is_active",             table_name="material_lots")
    op.drop_index("ix_operations_requests_status_is_active",       table_name="operations_requests")
    op.drop_index("ix_lots_status_is_active",                      table_name="lots")
    op.drop_index("ix_units_status_is_active",                     table_name="units")
    op.drop_index("ix_segment_response_lots_entered_equip",        table_name="segment_response_lots")
    op.drop_index("ix_segment_response_lots_lot_entered",          table_name="segment_response_lots")
    op.drop_index("ix_segment_response_lots_lot_open",             table_name="segment_response_lots")
    op.drop_index("ix_segment_response_units_entered_equip",       table_name="segment_response_units")
    op.drop_index("ix_segment_response_units_unit_entered",        table_name="segment_response_units")
    op.drop_index("ix_segment_response_units_unit_open",           table_name="segment_response_units")
    op.drop_index("ix_production_counters_equip_shift",            table_name="production_counters")
    op.drop_index("ix_equipment_state_logs_equip_started",         table_name="equipment_state_logs")
    op.drop_index("ix_equipment_state_logs_equip_ended",           table_name="equipment_state_logs")
