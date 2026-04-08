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
from sqlalchemy.orm import selectinload

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import equipment_state_changed, oee_calculated, production_counter_updated
from .models import EquipmentStateLog, ProductionCounter, Reason

logger = logging.getLogger("mes.performance")


class ReasonService:
    """Service class for hierarchical reason code management."""

    @staticmethod
    async def create_reason(
        session: AsyncSession, **kwargs: Any,
    ) -> Reason:
        """Create a new reason code."""
        reason = Reason(**kwargs)
        session.add(reason)
        await session.flush()
        logger.info("Reason created: code=%s name=%s", reason.code, reason.name)
        return reason

    @staticmethod
    async def list_reasons(
        session: AsyncSession,
    ) -> Sequence[Reason]:
        """Return all active reasons (flat list; client builds the tree)."""
        stmt = (
            select(Reason)
            .where(Reason.is_active.is_(True))
            .order_by(Reason.code)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_reason(
        session: AsyncSession, reason_id: UUID,
    ) -> Reason:
        """Get a single reason by ID."""
        stmt = select(Reason).where(
            Reason.id == reason_id,
            Reason.is_active.is_(True),
        )
        result = await session.execute(stmt)
        reason = result.scalar_one_or_none()
        if reason is None:
            raise NotFoundException(resource="Reason", resource_id=str(reason_id))
        return reason

    @staticmethod
    async def update_reason(
        session: AsyncSession, reason_id: UUID, **kwargs: Any,
    ) -> Reason:
        """Update an existing reason."""
        stmt = select(Reason).where(
            Reason.id == reason_id,
            Reason.is_active.is_(True),
        )
        result = await session.execute(stmt)
        reason = result.scalar_one_or_none()
        if reason is None:
            raise NotFoundException(resource="Reason", resource_id=str(reason_id))
        for key, value in kwargs.items():
            if value is not None:
                setattr(reason, key, value)
        await session.flush()
        return reason

    @staticmethod
    async def delete_reason(
        session: AsyncSession, reason_id: UUID,
    ) -> None:
        """Soft-delete a reason."""
        stmt = select(Reason).where(
            Reason.id == reason_id,
            Reason.is_active.is_(True),
        )
        result = await session.execute(stmt)
        reason = result.scalar_one_or_none()
        if reason is None:
            raise NotFoundException(resource="Reason", resource_id=str(reason_id))
        reason.is_active = False
        await session.flush()


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
            prev_log.ended_at_utc = started_at

        kwargs["started_at_utc"] = started_at
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

    @staticmethod
    async def increment_counter(
        session: AsyncSession,
        equipment_id: UUID,
        good_delta: int = 0,
        reject_delta: int = 0,
        rework_delta: int = 0,
        order_id: UUID | None = None,
        source_plugin: str = "manual",
    ) -> ProductionCounter:
        """
        Atomically increment production counters for today's shift.

        Creates the counter row if it doesn't exist yet. Deltas are added
        to the current values (not replaced). Emits a
        ``production.counter.updated`` event on success.
        """
        from datetime import date as date_type

        today = date_type.today()

        conditions = [
            ProductionCounter.equipment_id == equipment_id,
            ProductionCounter.shift_date == today,
        ]
        if order_id is not None:
            conditions.append(ProductionCounter.order_id == order_id)
        else:
            conditions.append(ProductionCounter.order_id.is_(None))

        stmt = select(ProductionCounter).where(and_(*conditions))
        result = await session.execute(stmt)
        counter = result.scalar_one_or_none()

        if counter is not None:
            counter.good_count += good_delta
            counter.reject_count += reject_delta
            counter.rework_count += rework_delta
        else:
            counter = ProductionCounter(
                equipment_id=equipment_id,
                order_id=order_id,
                shift_date=today,
                good_count=good_delta,
                reject_count=reject_delta,
                rework_count=rework_delta,
            )
            session.add(counter)

        await session.flush()

        await event_bus.publish(production_counter_updated(
            equipment_id=str(equipment_id),
            good_delta=good_delta,
            reject_delta=reject_delta,
            rework_delta=rework_delta,
            source_plugin=source_plugin,
        ))

        logger.info(
            "Counter incremented: equip=%s good=+%d reject=+%d rework=+%d (source=%s)",
            equipment_id, good_delta, reject_delta, rework_delta, source_plugin,
        )
        return counter


class OEEService:
    """Calculates OEE (Overall Equipment Effectiveness) metrics.

    Implements the standard OEE formula addressing the Six Big Losses:

    Availability Losses:
        1. Planned Downtime (changeovers, maintenance)    → oee_bucket: downtime_planned
        2. Unplanned Downtime (breakdowns)                → oee_bucket: downtime_unplanned

    Performance Losses:
        3. Minor Stops / Idling                           → captured via speed loss
        4. Reduced Speed / Slow Cycles                    → captured via speed loss

    Quality Losses:
        5. Production Rejects                             → reject_count
        6. Startup Rejects / Reduced Yield                → reject_count + rework_count

    Formulas:
        Availability = Run Time / Planned Production Time
        Performance  = (Ideal Cycle Time × Total Count) / Run Time
        Quality      = Good Count / Total Count
        OEE          = Availability × Performance × Quality
    """

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

        Availability: run_time / planned_production_time
            Run Time = time in uptime states (value_add + non_value)
            Planned Production Time = Run Time + Downtime (excludes 'excluded' bucket)
            Uses EquipmentStateLog.oee_bucket

        Performance: (ideal_cycle_time × total_count) / run_time
            Ideal Cycle Time derived from EquipmentMaterial.design_speed (Nameplate Capacity)
            Falls back to ProductionCounter.ideal_cycle_time_sec if set
            Run Time = same uptime computed for Availability

        Quality: good_count / total_count
            Uses ProductionCounter (good + reject + rework = total)
        """
        # ── 1. Availability from state logs ─────────────────────────
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

        uptime_value_add = buckets.get("uptime_value_add", 0)
        uptime_non_value = buckets.get("uptime_non_value", 0)
        downtime_planned = buckets.get("downtime_planned", 0)
        downtime_unplanned = buckets.get("downtime_unplanned", 0)
        excluded_time = buckets.get("excluded", 0)

        run_time = uptime_value_add + uptime_non_value
        planned_production_time = run_time + downtime_planned + downtime_unplanned
        availability = run_time / planned_production_time if planned_production_time > 0 else 0.0

        # ── 2. Counters (good / reject / rework) ───────────────────
        counter_stmt = select(
            func.sum(ProductionCounter.good_count).label("total_good"),
            func.sum(ProductionCounter.reject_count).label("total_reject"),
            func.sum(ProductionCounter.rework_count).label("total_rework"),
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

        # ── 3. Ideal Cycle Time (from EquipmentMaterial or counter) ─
        ideal_cycle_time = await OEEService._resolve_ideal_cycle_time(
            session, equipment_id, row.avg_cycle_time,
        )

        # ── 4. Performance: (ideal_cycle × total_count) / run_time ──
        if run_time > 0 and ideal_cycle_time > 0:
            performance_raw = (ideal_cycle_time * total_count) / run_time
        else:
            performance_raw = 0.0
        # Cap at 1.0: exceeding 100% indicates incorrect ideal cycle time
        performance = min(performance_raw, 1.0)

        # ── 5. Quality: good / total ────────────────────────────────
        quality = total_good / total_count if total_count > 0 else 0.0

        oee = availability * performance * quality

        # ── 6. Speed loss (Performance Losses 3+4) ──────────────────
        #    Theoretical production time = ideal_cycle_time × total_count
        #    Speed loss = run_time − theoretical production time
        theoretical_production_time = ideal_cycle_time * total_count if ideal_cycle_time > 0 else 0
        speed_loss_sec = max(0, run_time - theoretical_production_time) if run_time > 0 else 0

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
                "planned_production_time_sec": round(planned_production_time, 2),
                "run_time_sec": round(run_time, 2),
                "excluded_time_sec": round(excluded_time, 2),
                "ideal_cycle_time_sec": round(ideal_cycle_time, 4) if ideal_cycle_time else None,
                "total_good": total_good,
                "total_reject": total_reject,
                "total_rework": total_rework,
                "total_count": total_count,
                "state_log_count": len(logs),
            },
            "six_big_losses": {
                "planned_downtime_sec": round(downtime_planned, 2),
                "unplanned_downtime_sec": round(downtime_unplanned, 2),
                "speed_loss_sec": round(speed_loss_sec, 2),
                "quality_loss_count": total_reject + total_rework,
            },
        }

    @staticmethod
    async def _resolve_ideal_cycle_time(
        session: AsyncSession,
        equipment_id: UUID,
        counter_avg_cycle_time: float | None,
    ) -> float:
        """
        Determine ideal cycle time in seconds for an equipment.

        Priority:
        1. EquipmentMaterial.design_speed (Nameplate Capacity) — converted to sec/unit
        2. ProductionCounter.ideal_cycle_time_sec average (fallback)
        3. 0.0 (no data available)

        Conversion: If design_speed is 120 EA/h, the denominator UoM (h)
        has a multiplier to seconds (3600). ideal_cycle_time = 3600 / 120 = 30 sec/unit.
        """
        from mes.core.physical_model.models import EquipmentMaterial
        from mes.core.uom.models import UnitOfMeasure

        em_stmt = (
            select(EquipmentMaterial)
            .options(
                selectinload(EquipmentMaterial.design_speed_unit)
                .selectinload(UnitOfMeasure.denominator_uom)
            )
            .where(EquipmentMaterial.equipment_id == equipment_id)
            .limit(1)
        )
        em_result = await session.execute(em_stmt)
        em = em_result.scalar_one_or_none()

        if em is not None and em.design_speed > 0:
            rate_uom = em.design_speed_unit
            if rate_uom and rate_uom.denominator_uom:
                # denominator_uom.multiplier converts to base time unit (seconds)
                # e.g. "h" has multiplier=3600 → ideal = 3600 / 120 = 30 sec/unit
                denominator_in_seconds = rate_uom.denominator_uom.multiplier
                return denominator_in_seconds / em.design_speed

            # Fallback: assume rate is per hour if UoM lookup fails
            return 3600.0 / em.design_speed

        # Fallback to counter-stored ideal cycle time
        if counter_avg_cycle_time and counter_avg_cycle_time > 0:
            return float(counter_avg_cycle_time)

        return 0.0
