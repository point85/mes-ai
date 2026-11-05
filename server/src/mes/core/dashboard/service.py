"""
DASHBOARD: Aggregation service for dashboard views.

Provides pre-aggregated queries so dashboard clients can render
production status, line health, and shift summaries in a single call
instead of assembling data from many endpoints.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from datetime import date, datetime, time, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.core.operations.models import OperationsRequest
from mes.core.performance.models import EquipmentStateLog, ProductionCounter, Reason
from mes.core.physical_model.models import Equipment, WorkCell, ProductionLine
from mes.core.wip.models import Unit, Lot
from mes.framework.api.exceptions import NotFoundException, ValidationException
from .models import DashboardAlertRule
from .schemas import AlertRuleCreate, AlertRuleUpdate, AlertTestRequest

logger = logging.getLogger("mes.dashboard")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_duration(minutes: float) -> str:
    total = int(minutes)
    days, rem = divmod(total, 1440)
    hours, mins = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {mins}m"
    if hours:
        return f"{hours}h {mins}m"
    return f"{minutes:.1f} minutes"

class DashboardService:
    """Pre-aggregated dashboard queries."""

    # ── Order Progress Rollup ────────────────────────────────────────

    @staticmethod
    async def order_progress(
        session: AsyncSession,
        status_filter: str | None = None,
        include_inactive: bool = False,
        created_within_hours: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Rollup of all active production orders (or all, if include_inactive) with completion percentages
        and WIP counts per status bucket.

        Returns a list of dicts with:
        - order_id, order_number, product_id, status
        - quantity_ordered, quantity_completed, quantity_scrapped
        - pct_complete (0–100)
        - wip_counts: {queued, in_process, on_hold, completed, scrapped}
        """
        stmt = select(OperationsRequest)
        if not include_inactive:
            stmt = stmt.where(OperationsRequest.is_active.is_(True))
        if created_within_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=created_within_hours)
            stmt = stmt.where(OperationsRequest.created_at >= cutoff)
        if status_filter:
            stmt = stmt.where(OperationsRequest.status == status_filter)
        stmt = stmt.order_by(OperationsRequest.priority.desc(), OperationsRequest.created_at)

        result = await session.execute(stmt)
        orders = result.scalars().all()

        summaries: list[dict[str, Any]] = []
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
                key = "completed" if row.status == "finished" else row.status
                unit_counts[key] = unit_counts.get(key, 0) + row.cnt

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
                key = "completed" if row.status == "finished" else row.status
                unit_counts[key] = unit_counts.get(key, 0) + int(row.total_qty)

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

        line_summaries: list[dict[str, Any]] = []
        for line in lines:
            equip_list: list[dict[str, Any]] = []
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
        order_id: UUID | None = None,
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

        from mes.core.wip.models import SegmentResponseUnit, SegmentResponseLot

        # Counts are of distinct units/lots (not route-step records) so they agree with
        # the production trends, which use the same completed/scrapped definitions.
        done_statuses = ("completed", "finished")

        def on_equipment(stmt: Any, history: Any, owner: Any, owner_key: Any) -> Any:
            if equipment_id is None:
                return stmt
            return stmt.where(
                select(history.id).where(
                    owner_key == owner.id, history.equipment_id == equipment_id,
                ).exists()
            )

        unit_scrap_time = func.coalesce(Unit.scrapped_at, Unit.updated_at)
        lot_scrap_time = func.coalesce(Lot.scrapped_at, Lot.updated_at)

        unit_started_stmt = select(func.count(func.distinct(SegmentResponseUnit.unit_id))).where(
            SegmentResponseUnit.entered_at >= start,
        )
        if equipment_id is not None:
            unit_started_stmt = unit_started_stmt.where(
                SegmentResponseUnit.equipment_id == equipment_id,
            )
        if order_id is not None:
            unit_started_stmt = unit_started_stmt.where(
                SegmentResponseUnit.unit_id.in_(select(Unit.id).where(Unit.order_id == order_id))
            )
        unit_started_q = unit_started_stmt
        unit_completed_q = on_equipment(
            select(func.count()).select_from(Unit).where(
                Unit.status.in_(done_statuses), Unit.updated_at >= start,
                *([Unit.order_id == order_id] if order_id is not None else []),
            ),
            SegmentResponseUnit, Unit, SegmentResponseUnit.unit_id,
        )
        unit_scrapped_q = on_equipment(
            select(func.count()).select_from(Unit).where(
                Unit.status == "scrapped", unit_scrap_time >= start,
                *([Unit.order_id == order_id] if order_id is not None else []),
            ),
            SegmentResponseUnit, Unit, SegmentResponseUnit.unit_id,
        )

        lot_started_stmt = select(func.count(func.distinct(SegmentResponseLot.lot_id))).where(
            SegmentResponseLot.entered_at >= start,
        )
        if equipment_id is not None:
            lot_started_stmt = lot_started_stmt.where(
                SegmentResponseLot.equipment_id == equipment_id,
            )
        if order_id is not None:
            lot_started_stmt = lot_started_stmt.where(
                SegmentResponseLot.lot_id.in_(select(Lot.id).where(Lot.order_id == order_id))
            )
        lot_started_q = lot_started_stmt
        lot_completed_q = on_equipment(
            select(func.count()).select_from(Lot).where(
                Lot.status.in_(done_statuses), Lot.updated_at >= start,
                *([Lot.order_id == order_id] if order_id is not None else []),
            ),
            SegmentResponseLot, Lot, SegmentResponseLot.lot_id,
        )
        lot_scrapped_q = on_equipment(
            select(func.count()).select_from(Lot).where(
                Lot.status == "scrapped", lot_scrap_time >= start,
                *([Lot.order_id == order_id] if order_id is not None else []),
            ),
            SegmentResponseLot, Lot, SegmentResponseLot.lot_id,
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

    @staticmethod
    async def production_trends(
        session: AsyncSession,
        days: int = 30,
        equipment_id: UUID | None = None,
        order_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Return daily good/reject/rework counts and optional equipment OEE."""
        today = datetime.now(timezone.utc).date()
        first_day = today - timedelta(days=days - 1)
        stmt = (
            select(
                ProductionCounter.shift_date,
                func.coalesce(func.sum(ProductionCounter.good_count), 0).label("good"),
                func.coalesce(func.sum(ProductionCounter.reject_count), 0).label("reject"),
                func.coalesce(func.sum(ProductionCounter.rework_count), 0).label("rework"),
                func.avg(ProductionCounter.ideal_cycle_time_sec).label("avg_cycle_time"),
            )
            .where(
                ProductionCounter.shift_date >= first_day,
                ProductionCounter.shift_date <= today,
            )
            .group_by(ProductionCounter.shift_date)
            .order_by(ProductionCounter.shift_date)
        )
        if equipment_id is not None:
            stmt = stmt.where(ProductionCounter.equipment_id == equipment_id)
        if order_id is not None:
            stmt = stmt.where(ProductionCounter.order_id == order_id)

        rows = (await session.execute(stmt)).all()
        by_day = {
            row.shift_date: {
                "good": int(row.good),
                "reject": int(row.reject),
                "rework": int(row.rework),
                "avg_cycle_time": row.avg_cycle_time,
            }
            for row in rows
        }
        source = "counters"
        if not rows:
            by_day = await DashboardService._wip_daily_counts(
                session, first_day, today, equipment_id, order_id,
            )
            source = "wip" if by_day else "none"
        state_logs: list[EquipmentStateLog] = []
        ideal_cycle_time = 0.0
        if equipment_id is not None:
            period_start = datetime.combine(first_day, time.min, tzinfo=timezone.utc)
            period_end = datetime.combine(
                today + timedelta(days=1), time.min, tzinfo=timezone.utc,
            )
            state_stmt = select(EquipmentStateLog).where(
                EquipmentStateLog.equipment_id == equipment_id,
                EquipmentStateLog.started_at < period_end,
                or_(
                    EquipmentStateLog.ended_at.is_(None),
                    EquipmentStateLog.ended_at > period_start,
                ),
            )
            state_logs = list((await session.execute(state_stmt)).scalars().all())
            from mes.core.performance.service import OEEService

            cycle_times = [
                row.avg_cycle_time for row in rows if row.avg_cycle_time is not None
            ]
            average_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else None
            ideal_cycle_time = await OEEService.resolve_ideal_cycle_time(
                session, equipment_id, average_cycle_time,
            )

        series: list[dict[str, Any]] = []
        for offset in range(days):
            day = first_day + timedelta(days=offset)
            values = by_day.get(
                day, {"good": 0, "reject": 0, "rework": 0, "avg_cycle_time": None},
            )
            point: dict[str, Any] = {"date": day.isoformat(), **values, "oee": None}
            if equipment_id is not None:
                day_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
                day_end = day_start + timedelta(days=1)
                buckets: dict[str, float] = {}
                for log in state_logs:
                    log_start = _as_utc(log.started_at)
                    log_end = _as_utc(log.ended_at) if log.ended_at else day_end
                    seconds = max(
                        0.0,
                        (min(log_end, day_end) - max(log_start, day_start)).total_seconds(),
                    )
                    buckets[log.oee_bucket] = buckets.get(log.oee_bucket, 0.0) + seconds
                run_time = buckets.get("uptime_value_add", 0) + buckets.get("uptime_non_value", 0)
                planned_time = run_time + buckets.get("downtime_planned", 0) + buckets.get("downtime_unplanned", 0)
                availability = run_time / planned_time if planned_time > 0 else 0.0
                total_count = values["good"] + values["reject"] + values["rework"]
                performance = min(
                    (ideal_cycle_time * total_count) / run_time if run_time > 0 else 0.0,
                    1.0,
                )
                quality = values["good"] / total_count if total_count > 0 else 0.0
                if planned_time > 0 and total_count > 0 and ideal_cycle_time > 0:
                    point["oee"] = round(availability * performance * quality, 4)
            point.pop("avg_cycle_time", None)
            series.append(point)
        return {
            "period_start": first_day.isoformat(),
            "period_end": today.isoformat(),
            "days": days,
            "equipment_id": str(equipment_id) if equipment_id else None,
            "order_id": str(order_id) if order_id else None,
            "source": source,
            "series": series,
        }

    @staticmethod
    async def _wip_events(
        session: AsyncSession,
        first_day: date,
        today: date,
        equipment_id: UUID | None,
        order_id: UUID | None,
    ) -> list[tuple[date, UUID, str]]:
        """WIP-derived (UTC day, order_id, good|reject|rework) events from unit history."""
        from mes.core.wip.models import SegmentResponseUnit

        start = datetime.combine(first_day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)

        def scoped(stmt: Any) -> Any:
            if order_id is not None:
                stmt = stmt.where(Unit.order_id == order_id)
            if equipment_id is not None:
                stmt = stmt.where(
                    select(SegmentResponseUnit.id).where(
                        SegmentResponseUnit.unit_id == Unit.id,
                        SegmentResponseUnit.equipment_id == equipment_id,
                    ).exists()
                )
            return stmt

        events: list[tuple[date, UUID, str]] = []

        def add(moment: datetime | None, unit_order_id: UUID, key: str) -> None:
            if moment is None:
                return
            day = _as_utc(moment).date()
            if first_day <= day <= today:
                events.append((day, unit_order_id, key))

        good_stmt = scoped(
            select(Unit.updated_at, Unit.order_id).where(
                Unit.status.in_(("completed", "finished")),
                Unit.updated_at >= start,
                Unit.updated_at < end,
            )
        )
        for moment, unit_order_id in (await session.execute(good_stmt)).all():
            add(moment, unit_order_id, "good")

        scrap_time = func.coalesce(Unit.scrapped_at, Unit.updated_at)
        reject_stmt = scoped(
            select(scrap_time, Unit.order_id).where(
                Unit.status == "scrapped", scrap_time >= start, scrap_time < end,
            )
        )
        for moment, unit_order_id in (await session.execute(reject_stmt)).all():
            add(moment, unit_order_id, "reject")

        rework_stmt = (
            select(SegmentResponseUnit.exited_at, Unit.order_id)
            .join(Unit, Unit.id == SegmentResponseUnit.unit_id)
            .where(
                SegmentResponseUnit.result == "rework",
                SegmentResponseUnit.exited_at >= start,
                SegmentResponseUnit.exited_at < end,
            )
        )
        if order_id is not None:
            rework_stmt = rework_stmt.where(Unit.order_id == order_id)
        if equipment_id is not None:
            rework_stmt = rework_stmt.where(SegmentResponseUnit.equipment_id == equipment_id)
        for moment, unit_order_id in (await session.execute(rework_stmt)).all():
            add(moment, unit_order_id, "rework")
        return events

    @staticmethod
    async def _wip_daily_counts(
        session: AsyncSession,
        first_day: date,
        today: date,
        equipment_id: UUID | None,
        order_id: UUID | None,
    ) -> dict[date, dict[str, Any]]:
        """Derive daily good/reject/rework counts from WIP unit history (UTC days)."""
        result: dict[date, dict[str, Any]] = {}
        for day, _order, key in await DashboardService._wip_events(
            session, first_day, today, equipment_id, order_id,
        ):
            entry = result.setdefault(
                day, {"good": 0, "reject": 0, "rework": 0, "avg_cycle_time": None},
            )
            entry[key] += 1
        return result

    @staticmethod
    async def loss_breakdown(
        session: AsyncSession,
        days: int = 7,
        equipment_id: UUID | None = None,
        order_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Break downtime, production quality loss, and output down by reason/order/date."""
        end = datetime.now(timezone.utc)
        today = end.date()
        first_day = today - timedelta(days=days - 1)
        start = datetime.combine(first_day, time.min, tzinfo=timezone.utc)
        state_stmt = (
            select(EquipmentStateLog, Reason.name.label("reason_name"))
            .outerjoin(Reason, Reason.code == EquipmentStateLog.reason_code)
            .where(
                EquipmentStateLog.started_at < end,
                or_(
                    EquipmentStateLog.ended_at.is_(None),
                    EquipmentStateLog.ended_at > start,
                ),
                EquipmentStateLog.oee_bucket.in_(("downtime_planned", "downtime_unplanned")),
            )
        )
        if equipment_id is not None:
            state_stmt = state_stmt.where(EquipmentStateLog.equipment_id == equipment_id)
        state_rows = (await session.execute(state_stmt)).all()

        reason_totals: dict[tuple[str | None, str | None, str], float] = {}
        for log, reason_name in state_rows:
            clipped_start = max(_as_utc(log.started_at), start)
            clipped_end = min(_as_utc(log.ended_at) if log.ended_at else end, end)
            minutes = max(0.0, (clipped_end - clipped_start).total_seconds() / 60)
            key = (log.reason_code, reason_name, log.oee_bucket)
            reason_totals[key] = reason_totals.get(key, 0.0) + minutes

        reason_rows: list[dict[str, Any]] = [
            {
                "reason_code": code,
                "reason_name": name or "Unspecified",
                "loss_type": bucket,
                "minutes": round(minutes, 1),
            }
            for (code, name, bucket), minutes in reason_totals.items()
        ]
        reason_rows.sort(key=lambda item: item["minutes"], reverse=True)

        counter_stmt = (
            select(
                ProductionCounter.shift_date,
                ProductionCounter.order_id,
                OperationsRequest.order_number,
                OperationsRequest.created_at,
                func.coalesce(func.sum(ProductionCounter.good_count), 0).label("good"),
                func.coalesce(func.sum(ProductionCounter.reject_count), 0).label("reject"),
                func.coalesce(func.sum(ProductionCounter.rework_count), 0).label("rework"),
            )
            .outerjoin(OperationsRequest, OperationsRequest.id == ProductionCounter.order_id)
            .where(
                ProductionCounter.shift_date >= first_day,
                ProductionCounter.shift_date <= today,
            )
            .group_by(
                ProductionCounter.shift_date,
                ProductionCounter.order_id,
                OperationsRequest.order_number,
                OperationsRequest.created_at,
            )
        )
        if equipment_id is not None:
            counter_stmt = counter_stmt.where(ProductionCounter.equipment_id == equipment_id)
        if order_id is not None:
            counter_stmt = counter_stmt.where(ProductionCounter.order_id == order_id)
        counter_rows = (await session.execute(counter_stmt)).all()

        source = "counters"
        if not counter_rows:
            wip_events = await DashboardService._wip_events(
                session, first_day, today, equipment_id, order_id,
            )
            source = "wip" if wip_events else "none"
            order_ids = {order for _day, order, _key in wip_events}
            numbers: dict[UUID, tuple[str, datetime]] = {}
            if order_ids:
                number_rows = await session.execute(
                    select(
                        OperationsRequest.id, OperationsRequest.order_number,
                        OperationsRequest.created_at,
                    ).where(
                        OperationsRequest.id.in_(order_ids),
                    )
                )
                numbers = {row[0]: (row[1], row[2]) for row in number_rows.all()}
            wip_totals: dict[tuple[date, UUID], dict[str, int]] = {}
            for day, order, key in wip_events:
                wip_totals.setdefault((day, order), {"good": 0, "reject": 0, "rework": 0})[key] += 1
            counter_rows = [
                SimpleNamespace(
                    shift_date=day, order_id=order,
                    order_number=numbers.get(order, (None, None))[0],
                    created_at=numbers.get(order, (None, None))[1],
                    **counts,
                )
                for (day, order), counts in wip_totals.items()
            ]

        orders: dict[tuple[UUID | None, str | None, datetime | None], dict[str, int]] = {}
        shifts: dict[date, dict[str, int]] = {}
        for row in counter_rows:
            counts = {"good": int(row.good), "reject": int(row.reject), "rework": int(row.rework)}
            order_key = (row.order_id, row.order_number, row.created_at)
            order_counts = orders.setdefault(
                order_key, {"good": 0, "reject": 0, "rework": 0},
            )
            day_counts = shifts.setdefault(
                row.shift_date, {"good": 0, "reject": 0, "rework": 0},
            )
            for metric, value in counts.items():
                order_counts[metric] += value
                day_counts[metric] += value

        order_rows: list[dict[str, Any]] = [
            {
                "order_id": str(order_key_id) if order_key_id else None,
                "order_number": order_number or "Unassigned",
                "created_at": created_at.isoformat() if created_at else None,
                **counts,
            }
            for (order_key_id, order_number, created_at), counts in orders.items()
        ]
        order_rows.sort(key=lambda item: item["reject"] + item["rework"], reverse=True)
        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "equipment_id": str(equipment_id) if equipment_id else None,
            "order_id": str(order_id) if order_id else None,
            "source": source,
            "by_reason": reason_rows,
            "by_order": order_rows,
            "by_shift_date": [
                {"date": day.isoformat(), **counts}
                for day, counts in sorted(shifts.items())
            ],
        }

    @staticmethod
    async def list_alert_rules(session: AsyncSession) -> list[DashboardAlertRule]:
        result = await session.execute(
            select(DashboardAlertRule)
            .where(DashboardAlertRule.is_active.is_(True))
            .order_by(DashboardAlertRule.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_alert_rule(
        session: AsyncSession, body: AlertRuleCreate,
    ) -> DashboardAlertRule:
        if body.equipment_id is not None:
            equipment = await session.get(Equipment, body.equipment_id)
            if equipment is None or not equipment.is_active:
                raise NotFoundException(resource="Equipment", resource_id=str(body.equipment_id))
        rule = DashboardAlertRule(**body.model_dump())
        session.add(rule)
        await session.flush()
        return rule

    @staticmethod
    async def update_alert_rule(
        session: AsyncSession, rule_id: UUID, body: AlertRuleUpdate,
    ) -> DashboardAlertRule:
        rule = await session.get(DashboardAlertRule, rule_id)
        if rule is None or not rule.is_active:
            raise NotFoundException(resource="DashboardAlertRule", resource_id=str(rule_id))
        rule.is_enabled = body.is_enabled
        await session.flush()
        return rule

    @staticmethod
    async def update_alert_rule_definition(
        session: AsyncSession, rule_id: UUID, body: AlertRuleCreate,
    ) -> DashboardAlertRule:
        rule = await session.get(DashboardAlertRule, rule_id)
        if rule is None or not rule.is_active:
            raise NotFoundException(resource="DashboardAlertRule", resource_id=str(rule_id))
        if body.equipment_id is not None:
            equipment = await session.get(Equipment, body.equipment_id)
            if equipment is None or not equipment.is_active:
                raise NotFoundException(resource="Equipment", resource_id=str(body.equipment_id))
        rule.name = body.name
        rule.metric = body.metric
        rule.threshold = body.threshold
        rule.window_minutes = body.window_minutes
        rule.equipment_id = body.equipment_id
        await session.flush()
        return rule

    @staticmethod
    async def delete_alert_rule(session: AsyncSession, rule_id: UUID) -> None:
        rule = await session.get(DashboardAlertRule, rule_id)
        if rule is None or not rule.is_active:
            raise NotFoundException(resource="DashboardAlertRule", resource_id=str(rule_id))
        rule.is_active = False
        await session.flush()

    @staticmethod
    async def test_alert_rule(
        session: AsyncSession, rule_id: UUID, sample: AlertTestRequest,
    ) -> dict[str, Any]:
        """Dry-run a rule against caller-supplied sample data without persisting anything."""
        rule = await session.get(DashboardAlertRule, rule_id)
        if rule is None or not rule.is_active:
            raise NotFoundException(resource="DashboardAlertRule", resource_id=str(rule_id))

        def require(**values: float | int | None) -> None:
            missing = [name for name, value in values.items() if value is None]
            if missing:
                raise ValidationException(
                    f"Missing sample data for this rule: {', '.join(missing)}",
                )

        good = sample.good_count or 0
        reject = sample.reject_count or 0
        rework = sample.rework_count or 0
        total = good + reject + rework
        if rule.metric in ("downtime_minutes_above", "current_downtime_above"):
            require(downtime_minutes=sample.downtime_minutes)
            observed = float(sample.downtime_minutes or 0)
            triggered = observed > rule.threshold
            message = (
                f"Continuously down for {_format_duration(observed)}"
                if rule.metric == "current_downtime_above"
                else f"Downtime is {observed:.1f} minutes"
            )
        elif rule.metric == "scrap_rate_above":
            require(good_count=sample.good_count, reject_count=sample.reject_count,
                    rework_count=sample.rework_count)
            if total == 0:
                raise ValidationException("Enter at least one good, reject or rework count")
            observed = (reject + rework) / total
            triggered = observed > rule.threshold
            message = f"Scrap/rework rate is {observed:.1%}"
        else:
            require(
                run_minutes=sample.run_minutes,
                downtime_minutes=sample.downtime_minutes,
                ideal_cycle_time_sec=sample.ideal_cycle_time_sec,
            )
            run_sec = float(sample.run_minutes or 0) * 60
            planned_sec = run_sec + float(sample.downtime_minutes or 0) * 60
            if total == 0 or planned_sec == 0:
                raise ValidationException("Enter run time and at least one produced count")
            availability = run_sec / planned_sec
            performance = min(
                float(sample.ideal_cycle_time_sec or 0) * total / run_sec if run_sec > 0 else 0.0,
                1.0,
            )
            quality = good / total
            observed = availability * performance * quality
            triggered = observed < rule.threshold
            message = f"OEE is {observed:.1%}"
        return {
            "would_trigger": triggered,
            "observed_value": round(observed, 4),
            "threshold": rule.threshold,
            "message": message,
        }

    @staticmethod
    async def evaluate_alerts(
        session: AsyncSession,
        rules: list[DashboardAlertRule] | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate enabled alert rules on demand and return only currently active alerts."""
        from mes.core.performance.service import OEEService

        active_rules = rules if rules is not None else await DashboardService.list_alert_rules(session)
        now = datetime.now(timezone.utc)
        alerts: list[dict[str, Any]] = []
        for rule in active_rules:
            if not rule.is_enabled:
                continue
            start = now - timedelta(minutes=rule.window_minutes)
            observed: float | None = None
            down_since: datetime | None = None
            if rule.metric == "oee_below" and rule.equipment_id is not None:
                result = await OEEService.calculate_oee(
                    session, rule.equipment_id, start, now, publish_event=False,
                )
                if (
                    result["details"]["total_count"] == 0
                    and result["details"]["state_log_count"] == 0
                ):
                    continue
                if (
                    result["details"]["total_count"] == 0
                    or result["details"]["planned_production_time_sec"] == 0
                    or result["details"]["ideal_cycle_time_sec"] is None
                ):
                    continue
                observed = float(result["oee"])
                triggered = observed < rule.threshold
                metric_label = "OEE"
            elif rule.metric == "scrap_rate_above":
                stmt = select(
                    func.coalesce(func.sum(ProductionCounter.reject_count), 0).label("reject"),
                    func.coalesce(func.sum(ProductionCounter.rework_count), 0).label("rework"),
                    func.coalesce(func.sum(ProductionCounter.good_count), 0).label("good"),
                ).where(
                    ProductionCounter.shift_date >= start.date(),
                    ProductionCounter.shift_date <= now.date(),
                )
                if rule.equipment_id is not None:
                    stmt = stmt.where(ProductionCounter.equipment_id == rule.equipment_id)
                row = (await session.execute(stmt)).one()
                total = int(row.good) + int(row.reject) + int(row.rework)
                if total == 0:
                    continue
                observed = (int(row.reject) + int(row.rework)) / total
                triggered = observed > rule.threshold
                metric_label = "Scrap/rework rate"
            elif rule.metric == "downtime_minutes_above":
                stmt = select(EquipmentStateLog).where(
                    EquipmentStateLog.started_at < now,
                    or_(
                        EquipmentStateLog.ended_at.is_(None),
                        EquipmentStateLog.ended_at > start,
                    ),
                    EquipmentStateLog.oee_bucket.in_(("downtime_planned", "downtime_unplanned")),
                )
                if rule.equipment_id is not None:
                    stmt = stmt.where(EquipmentStateLog.equipment_id == rule.equipment_id)
                logs = (await session.execute(stmt)).scalars().all()
                observed = sum(
                    max(
                        0.0,
                        (
                            min(_as_utc(log.ended_at) if log.ended_at else now, now)
                            - max(_as_utc(log.started_at), start)
                        ).total_seconds() / 60,
                    )
                    for log in logs
                )
                triggered = observed > rule.threshold
                metric_label = "Downtime"
                open_starts = [_as_utc(log.started_at) for log in logs if log.ended_at is None]
                if open_starts:
                    down_since = min(open_starts)
            elif rule.metric == "current_downtime_above":
                stmt = select(EquipmentStateLog).where(
                    EquipmentStateLog.ended_at.is_(None),
                    EquipmentStateLog.oee_bucket.in_(("downtime_planned", "downtime_unplanned")),
                )
                if rule.equipment_id is not None:
                    stmt = stmt.where(EquipmentStateLog.equipment_id == rule.equipment_id)
                open_logs = (await session.execute(stmt)).scalars().all()
                if not open_logs:
                    continue
                longest = min(open_logs, key=lambda log: _as_utc(log.started_at))
                down_since = _as_utc(longest.started_at)
                observed = max(0.0, (now - down_since).total_seconds() / 60)
                triggered = observed > rule.threshold
                metric_label = "Downtime"
                start = down_since
            else:
                continue
            if triggered:
                if rule.metric == "current_downtime_above":
                    message = f"Continuously down for {_format_duration(observed)}"
                elif rule.metric == "downtime_minutes_above":
                    message = f"Downtime is {observed:.1f} minutes in the last {rule.window_minutes} min"
                else:
                    message = f"{metric_label} is {observed:.1%}"
                if down_since is not None:
                    message += f" (down since {down_since.strftime('%Y-%m-%d %H:%M')} UTC)"
                alerts.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "metric": rule.metric,
                    "equipment_id": rule.equipment_id,
                    "observed_value": round(observed, 4),
                    "threshold": rule.threshold,
                    "window_start": start,
                    "window_end": now,
                    "message": message,
                })
        return alerts
