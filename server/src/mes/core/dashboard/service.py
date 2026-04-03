"""
DASHBOARD: Aggregation service for dashboard views.

Provides pre-aggregated queries so dashboard clients can render
production status, line health, and shift summaries in a single call
instead of assembling data from many endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.core.production.models import ProductionOrder
from mes.core.wip.models import Unit, Lot
from mes.core.physical_model.models import Equipment, WorkCell, ProductionLine
from mes.core.performance.models import EquipmentStateLog

logger = logging.getLogger("mes.dashboard")


class DashboardService:
    """Pre-aggregated dashboard queries."""

    # ── Order Progress Rollup ────────────────────────────────────────

    @staticmethod
    async def order_progress(
        session: AsyncSession,
        status_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Rollup of all active production orders with completion percentages
        and WIP counts per status bucket.

        Returns a list of dicts with:
        - order_id, order_number, product_id, status
        - quantity_ordered, quantity_completed, quantity_scrapped
        - pct_complete (0–100)
        - wip_counts: {queued, in_process, on_hold, completed, scrapped}
        """
        stmt = select(ProductionOrder).where(ProductionOrder.is_active.is_(True))
        if status_filter:
            stmt = stmt.where(ProductionOrder.status == status_filter)
        stmt = stmt.order_by(ProductionOrder.priority.desc(), ProductionOrder.created_at)

        result = await session.execute(stmt)
        orders = result.scalars().all()

        summaries = []
        for order in orders:
            # Unit counts by status
            unit_stmt = (
                select(
                    Unit.status,
                    func.count().label("cnt"),
                )
                .where(Unit.order_id == order.id, Unit.is_active.is_(True))
                .group_by(Unit.status)
            )
            unit_result = await session.execute(unit_stmt)
            unit_counts: dict[str, int] = {
                "queued": 0, "in_process": 0, "on_hold": 0,
                "completed": 0, "scrapped": 0,
            }
            for row in unit_result:
                unit_counts[row.status] = row.cnt

            # Lot counts by status
            lot_stmt = (
                select(
                    Lot.status,
                    func.coalesce(func.sum(Lot.quantity), 0).label("total_qty"),
                )
                .where(Lot.order_id == order.id, Lot.is_active.is_(True))
                .group_by(Lot.status)
            )
            lot_result = await session.execute(lot_stmt)
            for row in lot_result:
                unit_counts[row.status] = unit_counts.get(row.status, 0) + int(row.total_qty)

            total = order.quantity_ordered or 1
            pct = round(
                (order.quantity_completed / total) * 100,
                1,
            )

            summaries.append({
                "order_id": str(order.id),
                "order_number": order.order_number,
                "product_id": str(order.product_id),
                "status": order.status,
                "priority": order.priority,
                "quantity_ordered": order.quantity_ordered,
                "quantity_completed": order.quantity_completed,
                "quantity_scrapped": order.quantity_scrapped,
                "pct_complete": min(pct, 100.0),
                "wip_counts": unit_counts,
            })

        return summaries

    # ── Line Status ──────────────────────────────────────────────────

    @staticmethod
    async def line_status(
        session: AsyncSession,
        line_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Status overview of production lines with per-equipment state
        and queue depth.

        Returns per line:
        - line_id, line_name
        - equipment: list of {equipment_id, name, state, dispatch_category,
          queue_depth, max_queue_depth}
        """
        stmt = select(ProductionLine).where(ProductionLine.is_active.is_(True))
        if line_id:
            stmt = stmt.where(ProductionLine.id == line_id)
        stmt = stmt.options(
            selectinload(ProductionLine.work_cells)
            .selectinload(WorkCell.equipment)
        )

        result = await session.execute(stmt)
        lines = result.scalars().unique().all()

        line_summaries = []
        for line in lines:
            equip_list = []
            for wc in line.work_cells:
                if not wc.is_active:
                    continue
                for eq in wc.equipment:
                    if not eq.is_active:
                        continue
                    # Current state
                    state_stmt = (
                        select(EquipmentStateLog)
                        .where(
                            EquipmentStateLog.equipment_id == eq.id,
                            EquipmentStateLog.ended_at.is_(None),
                        )
                        .order_by(EquipmentStateLog.started_at.desc())
                        .limit(1)
                    )
                    state_result = await session.execute(state_stmt)
                    state_log = state_result.scalar_one_or_none()

                    # Queue depth
                    q_unit = (
                        select(func.count())
                        .select_from(Unit)
                        .where(
                            Unit.current_equipment_id == eq.id,
                            Unit.status.in_(["queued", "in_process"]),
                        )
                    )
                    q_lot = (
                        select(func.count())
                        .select_from(Lot)
                        .where(
                            Lot.current_equipment_id == eq.id,
                            Lot.status.in_(["queued", "in_process"]),
                        )
                    )
                    u_count = (await session.execute(q_unit)).scalar() or 0
                    l_count = (await session.execute(q_lot)).scalar() or 0

                    equip_list.append({
                        "equipment_id": str(eq.id),
                        "name": eq.name,
                        "work_cell": wc.name,
                        "state": state_log.state if state_log else None,
                        "dispatch_category": (
                            state_log.dispatch_category if state_log else "available"
                        ),
                        "queue_depth": u_count + l_count,
                        "max_queue_depth": eq.max_queue_depth,
                    })

            line_summaries.append({
                "line_id": str(line.id),
                "line_name": line.name,
                "equipment_count": len(equip_list),
                "equipment": equip_list,
            })

        return line_summaries

    # ── Shift Summary ────────────────────────────────────────────────

    @staticmethod
    async def shift_summary(
        session: AsyncSession,
        hours: int = 8,
        equipment_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Aggregated production summary for the past N hours (default: 8-hour shift).

        Returns:
        - period_start, period_end
        - units_started, units_completed, units_scrapped
        - lots_started, lots_completed, lots_scrapped
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=hours)

        from mes.core.wip.models import UnitHistory, LotHistory

        # Unit history in time window
        unit_base = select(UnitHistory).where(UnitHistory.entered_at >= start)
        if equipment_id:
            unit_base = unit_base.where(UnitHistory.equipment_id == equipment_id)

        unit_started_q = select(func.count()).select_from(
            unit_base.subquery()
        )
        unit_completed_q = select(func.count()).select_from(
            unit_base.where(UnitHistory.exited_at.is_not(None)).subquery()
        )
        unit_scrapped_q = select(func.count()).select_from(
            select(Unit).where(
                Unit.status == "scrapped",
                Unit.updated_at >= start,
            ).subquery()
        )

        # Lot history in time window
        lot_base = select(LotHistory).where(LotHistory.entered_at >= start)
        if equipment_id:
            lot_base = lot_base.where(LotHistory.equipment_id == equipment_id)

        lot_started_q = select(func.count()).select_from(
            lot_base.subquery()
        )
        lot_completed_q = select(func.count()).select_from(
            lot_base.where(LotHistory.exited_at.is_not(None)).subquery()
        )
        lot_scrapped_q = select(func.count()).select_from(
            select(Lot).where(
                Lot.status == "scrapped",
                Lot.updated_at >= start,
            ).subquery()
        )

        return {
            "period_start": start.isoformat(),
            "period_end": now.isoformat(),
            "hours": hours,
            "equipment_id": str(equipment_id) if equipment_id else None,
            "units_started": (await session.execute(unit_started_q)).scalar() or 0,
            "units_completed": (await session.execute(unit_completed_q)).scalar() or 0,
            "units_scrapped": (await session.execute(unit_scrapped_q)).scalar() or 0,
            "lots_started": (await session.execute(lot_started_q)).scalar() or 0,
            "lots_completed": (await session.execute(lot_completed_q)).scalar() or 0,
            "lots_scrapped": (await session.execute(lot_scrapped_q)).scalar() or 0,
        }
