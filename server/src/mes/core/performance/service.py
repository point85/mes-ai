"""
PERF-ANALYSIS: Business logic service for performance analysis.

Provides equipment state logging, production counter management,
and OEE (Overall Equipment Effectiveness) calculation.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import equipment_state_changed, oee_calculated
from .models import EquipmentStateLog, ProductionCounter

logger = logging.getLogger("mes.performance")


class EquipmentStateService:
    """Service class for equipment state log management."""

    @staticmethod
    async def record_state_change(
        session: AsyncSession, **kwargs: Any,
    ) -> EquipmentStateLog:
        """
        Record an equipment state change.

        Closes the previous open state log (sets ended_at) before
        inserting the new state.
        """
        equipment_id = kwargs["equipment_id"]
        started_at = kwargs["started_at"]

        # Close the currently open state log for this equipment
        stmt = (
            select(EquipmentStateLog)
            .where(
                EquipmentStateLog.equipment_id == equipment_id,
                EquipmentStateLog.ended_at.is_(None),
            )
            .order_by(EquipmentStateLog.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        prev_log = result.scalar_one_or_none()
        if prev_log is not None:
            prev_log.ended_at = started_at

        log = EquipmentStateLog(**kwargs)
        session.add(log)
        await session.flush()

        # Emit state changed event
        await event_bus.publish(equipment_state_changed(
            equipment_id=str(equipment_id),
            state=kwargs["state"],
            dispatch_category=kwargs["dispatch_category"],
        ))

        logger.info(
            "Equipment state change: equip=%s state=%s category=%s",
            equipment_id, kwargs["state"], kwargs["dispatch_category"],
        )
        return log

    @staticmethod
    async def list_state_logs(
        session: AsyncSession,
        params: PaginationParams,
        equipment_id: UUID | None = None,
        started_after: datetime | None = None,
        started_before: datetime | None = None,
    ) -> tuple[Sequence[EquipmentStateLog], str | None, bool]:
        """List equipment state logs with optional filters."""
        stmt = select(EquipmentStateLog)
        if equipment_id is not None:
            stmt = stmt.where(EquipmentStateLog.equipment_id == equipment_id)
        if started_after is not None:
            stmt = stmt.where(EquipmentStateLog.started_at >= started_after)
        if started_before is not None:
            stmt = stmt.where(EquipmentStateLog.started_at <= started_before)
        return await paginate_query(session, stmt, EquipmentStateLog, params)

    @staticmethod
    async def get_current_state(
        session: AsyncSession, equipment_id: UUID,
    ) -> EquipmentStateLog | None:
        """Get the current (open) state for an equipment."""
        stmt = (
            select(EquipmentStateLog)
            .where(
                EquipmentStateLog.equipment_id == equipment_id,
                EquipmentStateLog.ended_at.is_(None),
            )
            .order_by(EquipmentStateLog.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class ProductionCounterService:
    """Service class for production counter management."""

    @staticmethod
    async def create_or_update_counter(
        session: AsyncSession, **kwargs: Any,
    ) -> ProductionCounter:
        """Create or update a production counter (upsert by equipment+shift_date+order)."""
        equipment_id = kwargs["equipment_id"]
        shift_date = kwargs["shift_date"]
        order_id = kwargs.get("order_id")

        # Look for existing counter
        conditions = [
            ProductionCounter.equipment_id == equipment_id,
            ProductionCounter.shift_date == shift_date,
        ]
        if order_id is not None:
            conditions.append(ProductionCounter.order_id == order_id)
        else:
            conditions.append(ProductionCounter.order_id.is_(None))

        stmt = select(ProductionCounter).where(and_(*conditions))
        result = await session.execute(stmt)
        counter = result.scalar_one_or_none()

        if counter is not None:
            # Update existing
            for key in ("good_count", "reject_count", "rework_count",
                        "ideal_cycle_time_sec", "actual_run_time_sec"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(counter, key, kwargs[key])
        else:
            counter = ProductionCounter(**kwargs)
            session.add(counter)

        await session.flush()
        return counter

    @staticmethod
    async def list_counters(
        session: AsyncSession,
        params: PaginationParams,
        equipment_id: UUID | None = None,
        order_id: UUID | None = None,
        shift_date: Any = None,
    ) -> tuple[Sequence[ProductionCounter], str | None, bool]:
        """List production counters with optional filters."""
        stmt = select(ProductionCounter)
        if equipment_id is not None:
            stmt = stmt.where(ProductionCounter.equipment_id == equipment_id)
        if order_id is not None:
            stmt = stmt.where(ProductionCounter.order_id == order_id)
        if shift_date is not None:
            stmt = stmt.where(ProductionCounter.shift_date == shift_date)
        return await paginate_query(session, stmt, ProductionCounter, params)


class OEEService:
    """Calculates OEE (Overall Equipment Effectiveness) metrics."""

    @staticmethod
    async def calculate_oee(
        session: AsyncSession,
        equipment_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """
        Calculate OEE for an equipment over a time period.

        OEE = Availability × Performance × Quality

        Availability: uptime / (uptime + downtime)
            uses EquipmentStateLog.oee_bucket
        Performance: (ideal_cycle_time × total_count) / actual_run_time
            uses ProductionCounter
        Quality: good_count / total_count
            uses ProductionCounter
        """
        # ── Availability from state logs ────────────────────────────
        stmt = select(EquipmentStateLog).where(
            EquipmentStateLog.equipment_id == equipment_id,
            EquipmentStateLog.started_at >= period_start,
            EquipmentStateLog.started_at <= period_end,
        )
        result = await session.execute(stmt)
        logs = result.scalars().all()

        buckets: dict[str, float] = defaultdict(float)
        for log in logs:
            end = log.ended_at or period_end
            duration = (end - log.started_at).total_seconds()
            buckets[log.oee_bucket] += duration

        uptime = buckets.get("uptime_value_add", 0) + buckets.get("uptime_non_value", 0)
        downtime = buckets.get("downtime_planned", 0) + buckets.get("downtime_unplanned", 0)
        total_time = uptime + downtime
        availability = uptime / total_time if total_time > 0 else 0.0

        # ── Performance & Quality from counters ─────────────────────
        counter_stmt = select(
            func.sum(ProductionCounter.good_count).label("total_good"),
            func.sum(ProductionCounter.reject_count).label("total_reject"),
            func.sum(ProductionCounter.rework_count).label("total_rework"),
            func.sum(ProductionCounter.actual_run_time_sec).label("total_run_time"),
            func.avg(ProductionCounter.ideal_cycle_time_sec).label("avg_cycle_time"),
        ).where(
            ProductionCounter.equipment_id == equipment_id,
            ProductionCounter.shift_date >= period_start.date(),
            ProductionCounter.shift_date <= period_end.date(),
        )
        counter_result = await session.execute(counter_stmt)
        row = counter_result.one()

        total_good = row.total_good or 0
        total_reject = row.total_reject or 0
        total_rework = row.total_rework or 0
        total_count = total_good + total_reject + total_rework
        total_run_time = row.total_run_time or 0
        avg_cycle_time = row.avg_cycle_time or 0

        # Performance: (ideal_cycle × total_count) / actual_run_time
        if total_run_time > 0 and avg_cycle_time > 0:
            performance = (avg_cycle_time * total_count) / total_run_time
        else:
            performance = 0.0

        # Quality: good / total
        quality = total_good / total_count if total_count > 0 else 0.0

        oee = availability * performance * quality

        # Emit event
        await event_bus.publish(oee_calculated(
            equipment_id=str(equipment_id),
            oee=round(oee, 4),
        ))

        return {
            "equipment_id": equipment_id,
            "period_start": period_start,
            "period_end": period_end,
            "availability": round(availability, 4),
            "performance": round(performance, 4),
            "quality": round(quality, 4),
            "oee": round(oee, 4),
            "details": {
                "uptime_sec": round(uptime, 2),
                "downtime_sec": round(downtime, 2),
                "total_good": total_good,
                "total_reject": total_reject,
                "total_rework": total_rework,
                "total_run_time_sec": round(total_run_time, 2),
                "avg_ideal_cycle_time_sec": round(avg_cycle_time, 4) if avg_cycle_time else None,
                "state_log_count": len(logs),
            },
        }
