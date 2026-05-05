"""
WIP-TRACK: Business logic service for units and lots.

Provides CRUD, lifecycle operations (start, complete, move, hold, scrap),
and history queries.  Delegates next-step resolution to the routing engine.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from mes.core.operations.service import OperationsRequestService

from .events import (
    unit_created, unit_started, unit_completed, unit_moved,
    unit_scrapped, unit_held, unit_released,
    lot_created, lot_started, lot_completed, lot_moved,
    lot_held, lot_released, lot_scrapped,
)
from .exceptions import (
    DuplicateSerialNumberException,
    DuplicateLotNumberException,
    InvalidWIPTransitionException,
    NoRouteAssignedException,
    NoNextStepException,
)
from .models import Unit, Lot, SegmentResponseUnit, SegmentResponseLot, EquipmentActual, MaterialActual

logger = logging.getLogger("mes.wip")


# ── Deferred event publishing ───────────────────────────────────────
#
# Events that trigger handlers which UPDATE the same DB rows we have
# pending in our open transaction (notably wip.unit.moved → dispatch
# auto-assign equipment) must be published WITHOUT awaiting the
# handler — otherwise the handler's UPDATE blocks on the row lock
# we still hold, causing a deadlock.  Scheduling via create_task
# defers handler execution until our caller (the route layer) yields
# control to the event loop, typically while awaiting session.commit().

_pending_publish_tasks: set[asyncio.Task] = set()


def _publish_after_commit(event) -> None:
    """Schedule an event to be published after the current transaction commits."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop (e.g. unit-test sync context) — best effort, skip.
        logger.debug("No running event loop; skipping deferred publish of %s", event.event_type)
        return
    task = loop.create_task(event_bus.publish(event))
    _pending_publish_tasks.add(task)
    task.add_done_callback(_pending_publish_tasks.discard)


# ═══════════════════════════════════════════════════════════════════
# RESOURCE ACTUALS HELPER (Item E — ISA-95 Part 4)
# ═══════════════════════════════════════════════════════════════════

async def _write_resource_actuals(
    session: AsyncSession,
    *,
    segment_response_unit_id: "UUID | None" = None,
    segment_response_lot_id: "UUID | None" = None,
    equipment_id: "UUID | None",
    started_at: "datetime",
    ended_at: "datetime",
    unit_id: "UUID | None" = None,
    lot_id: "UUID | None" = None,
    step_id: "UUID | None" = None,
) -> None:
    """
    Write EquipmentActual and MaterialActual rows for a completed segment.

    Called by complete_unit_step / complete_lot_step.  No-ops gracefully
    if no equipment was assigned.  MaterialActuals mirror existing
    MaterialConsumption rows for the same WIP/step, giving ISA-95 Part 4
    traceability without double-counting inventory.
    """
    from sqlalchemy import select as _select
    from mes.core.material.models import MaterialConsumption

    # ── EquipmentActual ─────────────────────────────────────────────
    if equipment_id is not None:
        eq_actual = EquipmentActual(
            segment_response_unit_id=segment_response_unit_id,
            segment_response_lot_id=segment_response_lot_id,
            equipment_id=equipment_id,
            state=None,  # Snapshot could be added from EquipmentStateLog if needed
            started_at=started_at,
            ended_at=ended_at,
            started_at_utc=started_at.replace(tzinfo=None),
            ended_at_utc=ended_at.replace(tzinfo=None),
        )
        session.add(eq_actual)

    # ── MaterialActual (mirrors MaterialConsumption for this WIP step) ─
    where_clauses = []
    if unit_id is not None:
        where_clauses.append(MaterialConsumption.unit_id == unit_id)
    elif lot_id is not None:
        where_clauses.append(MaterialConsumption.lot_id == lot_id)
    if step_id is not None:
        where_clauses.append(MaterialConsumption.step_id == step_id)

    if where_clauses:
        consumptions_result = await session.execute(
            _select(MaterialConsumption).where(*where_clauses)
        )
        for mc in consumptions_result.scalars().all():
            mat_actual = MaterialActual(
                segment_response_unit_id=segment_response_unit_id,
                segment_response_lot_id=segment_response_lot_id,
                material_id=mc.material_lot.material_id if mc.material_lot else None,
                material_lot_id=mc.material_lot_id,
                direction="consumed",
                quantity=mc.quantity_consumed,
                recorded_at=mc.consumed_at,
                recorded_at_utc=mc.consumed_at.replace(tzinfo=None) if mc.consumed_at else None,
            )
            session.add(mat_actual)


# ═══════════════════════════════════════════════════════════════════
# SHIFT CONTEXT HELPER
# ═══════════════════════════════════════════════════════════════════


async def _resolve_shift_context(
    session: AsyncSession,
    equipment_id: UUID | None,
    at_dt: datetime,
) -> tuple[str | None, str | None, str | None]:
    """
    Walk the ISA-95 physical hierarchy (equipment → work_cell → production_line
    → area → site) to find the first configured work schedule, then resolve the
    active shift/team at *at_dt*.

    Returns ``(work_schedule_name, shift_name, team_name)``.
    All three are ``None`` when no schedule is configured or no shift is active.
    If multiple shift instances overlap *at_dt* the one with the earliest
    ``start_datetime`` (oldest) is chosen.
    """
    if equipment_id is None:
        return None, None, None

    from mes.core.physical_model.models import (
        Equipment as EquipmentModel,
        WorkCell,
        ProductionLine,
        Area,
        Site,
    )
    from mes.core.work_schedule.service import (
        WorkScheduleService,
        compute_shift_instances_for_time,
    )

    equip_result = await session.execute(
        select(EquipmentModel)
        .where(EquipmentModel.id == equipment_id)
        .options(
            selectinload(EquipmentModel.work_cell)
            .selectinload(WorkCell.production_line),
            selectinload(EquipmentModel.work_cell)
            .selectinload(WorkCell.area),
            selectinload(EquipmentModel.work_cell)
            .selectinload(WorkCell.site),
        )
    )
    equip = equip_result.scalar_one_or_none()
    if equip is None or equip.work_cell is None:
        return None, None, None

    wc = equip.work_cell
    schedule_id = (
        wc.work_schedule_id
        or (wc.production_line.work_schedule_id if wc.production_line else None)
        or (wc.area.work_schedule_id if wc.area else None)
        or (wc.site.work_schedule_id if wc.site else None)
    )
    if schedule_id is None:
        return None, None, None

    try:
        schedule = await WorkScheduleService.get_schedule(session, schedule_id)
    except Exception:  # noqa: BLE001
        logger.warning("Could not load work schedule %s for shift context", schedule_id)
        return None, None, None

    # Shift times (start_time, end_time) are stored as local factory times, so
    # we must convert at_dt to the site's local timezone before comparing.
    # Fall back to UTC if the site has no timezone configured.
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    site_tz_str = wc.site.timezone if (wc.site and wc.site.timezone) else None
    try:
        local_tz = ZoneInfo(site_tz_str) if site_tz_str else timezone.utc
    except ZoneInfoNotFoundError:
        logger.warning("Unknown site timezone %r — falling back to UTC", site_tz_str)
        local_tz = timezone.utc
    local_dt = at_dt.astimezone(local_tz).replace(tzinfo=None) if at_dt.tzinfo else at_dt
    instances = compute_shift_instances_for_time(schedule, local_dt)
    if not instances:
        return schedule.name, None, None

    earliest = min(instances, key=lambda i: i.start_datetime)
    return schedule.name, earliest.shift_name, earliest.team_name


# ═══════════════════════════════════════════════════════════════════
# UNIT SERVICE
# ═══════════════════════════════════════════════════════════════════


class UnitService:
    """Service class for unit lifecycle operations."""

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_units(
        session: AsyncSession,
        params: PaginationParams,
        status: str | None = None,
        order_id: UUID | None = None,
        equipment_id: UUID | None = None,
    ) -> tuple[Sequence[Unit], str | None, bool]:
        stmt = select(Unit).where(Unit.is_active.is_(True)).options(selectinload(Unit.order))
        if status is not None:
            stmt = stmt.where(Unit.status == status)
        if order_id is not None:
            stmt = stmt.where(Unit.order_id == order_id)
        if equipment_id is not None:
            stmt = stmt.where(Unit.current_equipment_id == equipment_id)
        return await paginate_query(session, stmt, Unit, params)

    @staticmethod
    async def get_unit(session: AsyncSession, unit_id: UUID) -> Unit:
        stmt = select(Unit).where(Unit.id == unit_id, Unit.is_active.is_(True))
        result = await session.execute(stmt)
        unit = result.scalar_one_or_none()
        if unit is None:
            raise NotFoundException(resource="Unit", resource_id=str(unit_id))
        return unit

    @staticmethod
    async def get_unit_by_serial(
        session: AsyncSession, serial_number: str,
    ) -> Unit:
        """Look up a unit by serial number. Used for barcode scanning."""
        stmt = select(Unit).where(
            Unit.serial_number == serial_number,
            Unit.is_active.is_(True),
        )
        result = await session.execute(stmt)
        unit = result.scalar_one_or_none()
        if unit is None:
            raise NotFoundException(resource="Unit", resource_id=serial_number)
        return unit

    @staticmethod
    async def get_segment_response_units(
        session: AsyncSession, unit_id: UUID,
    ) -> Sequence[SegmentResponseUnit]:
        """Get all history records for a unit, ordered by entered_at."""
        # Verify unit exists
        await UnitService.get_unit(session, unit_id)
        stmt = (
            select(SegmentResponseUnit)
            .where(SegmentResponseUnit.unit_id == unit_id)
            .order_by(SegmentResponseUnit.entered_at)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    # ─── Create ──────────────────────────────────────────────────────

    @staticmethod
    async def create_unit(session: AsyncSession, **kwargs: Any) -> Unit:
        """Create a new unit. The order must be released or in_progress."""
        sn = kwargs["serial_number"]
        existing = await session.execute(
            select(Unit).where(Unit.serial_number == sn)
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateSerialNumberException(sn)

        unit = Unit(**kwargs)
        session.add(unit)
        await session.flush()

        # Auto-transition order to in_progress if it's released
        await OperationsRequestService.start_order(session, unit.order_id)

        await event_bus.publish(
            unit_created(str(unit.id), str(unit.order_id), unit.serial_number)
        )
        logger.info("Created unit %s (SN=%s, order=%s)", unit.id, sn, unit.order_id)
        return unit

    # ─── Lifecycle ───────────────────────────────────────────────────

    @staticmethod
    async def start_unit(
        session: AsyncSession,
        unit_id: UUID,
        equipment_id: UUID | None = None,
    ) -> Unit:
        """
        Start processing a unit at its current step.
        Status: queued → in_process  OR  re-start after move.
        """
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status not in ("queued", "in_process"):
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "start",
            )

        # If no current step, resolve the first step from the route
        if unit.current_step_id is None:
            from mes.core.routing.service import RoutingEngineService
            first_step = await RoutingEngineService.get_first_step(
                session, unit.order_id,
            )
            unit.current_step_id = first_step.id

        if equipment_id is not None:
            unit.current_equipment_id = equipment_id
        elif unit.current_equipment_id is None:
            # Auto-dispatch: pick a recommended equipment via DISPATCH module.
            # Silently no-op if no eligible equipment is available — the unit
            # still transitions to in_process; an operator can assign later.
            from mes.core.dispatch.service import DispatchService
            try:
                await DispatchService.auto_dispatch(session, unit_id=unit.id)
                # auto_dispatch.execute writes unit.current_equipment_id on this
                # same session, so unit.current_equipment_id is now populated
                # (or still None if dispatch was blocked).
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Auto-dispatch failed for unit %s on start: %s",
                    unit.id, exc,
                )
        unit.status = "in_process"
        await session.flush()

        # Create history record
        now = datetime.now(timezone.utc)
        ws_name, sft_name, tm_name = await _resolve_shift_context(
            session, unit.current_equipment_id, now,
        )
        history = SegmentResponseUnit(
            unit_id=unit.id,
            step_id=unit.current_step_id,
            equipment_id=unit.current_equipment_id,
            entered_at=now,
            entered_at_utc=now.replace(tzinfo=None),
            work_schedule_name=ws_name,
            shift_name=sft_name,
            team_name=tm_name,
        )
        session.add(history)
        await session.flush()

        await event_bus.publish(
            unit_started(
                str(unit.id),
                str(unit.current_step_id),
                str(unit.current_equipment_id) if unit.current_equipment_id else None,
            )
        )
        logger.info("Started unit %s at step %s", unit.id, unit.current_step_id)
        return unit

    @staticmethod
    async def complete_unit_step(
        session: AsyncSession,
        unit_id: UUID,
        result: str = "pass",
        disposition: str | None = None,
        data_snapshot: dict | None = None,
        failure_mode: str | None = None,
        defect_code_id: UUID | None = None,
    ) -> Unit:
        """
        Complete the current step for a unit.
        Updates the open history record with exit time, result, and RCA fields.
        Auto-creates a NonConformance when result='fail'.
        """
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status != "in_process":
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "complete",
            )

        # Close the open history record for the current step
        stmt = (
            select(SegmentResponseUnit)
            .where(
                SegmentResponseUnit.unit_id == unit_id,
                SegmentResponseUnit.step_id == unit.current_step_id,
                SegmentResponseUnit.exited_at.is_(None),
            )
            .order_by(SegmentResponseUnit.entered_at.desc())
        )
        history_result = await session.execute(stmt)
        history = history_result.scalar_one_or_none()
        entered_at_snapshot = None
        if history is not None:
            now = datetime.now(timezone.utc)
            entered_at_snapshot = history.entered_at
            history.exited_at = now
            history.exited_at_utc = now.replace(tzinfo=None)
            history.result = result
            history.data_snapshot = data_snapshot
            # Item B: persist RCA fields on the history row
            history.disposition = disposition
            history.failure_mode = failure_mode
            history.defect_code_id = defect_code_id

        await session.flush()

        # Item E: write EquipmentActual and MaterialActual rows
        if history is not None and entered_at_snapshot is not None:
            await _write_resource_actuals(
                session,
                segment_response_unit_id=history.id,
                equipment_id=unit.current_equipment_id,
                started_at=entered_at_snapshot,
                ended_at=history.exited_at,
                unit_id=unit_id,
                step_id=unit.current_step_id,
            )
            await session.flush()

        # Item C: auto-create NonConformance when the step fails
        if result == "fail":
            from mes.core.quality.service import NonConformanceService
            description = failure_mode or f"Step failed: {unit.current_step_id}"
            await NonConformanceService.create_nc(
                session,
                unit_id=unit_id,
                step_id=unit.current_step_id,
                nc_type="defect",
                description=description,
                disposition=None,  # left open for QA to assign controlled value
                status="open",
            )
            await session.flush()

        await event_bus.publish(
            unit_completed(str(unit.id), str(unit.current_step_id), result)
        )
        logger.info(
            "Completed step %s for unit %s (result=%s)",
            unit.current_step_id, unit.id, result,
        )
        return unit

    @staticmethod
    async def move_unit(
        session: AsyncSession,
        unit_id: UUID,
        target_step_id: UUID | None = None,
        result: str | None = None,
        disposition: str | None = None,
    ) -> Unit:
        """
        Move a unit to the next step (or specific target step).

        Args:
            target_step_id: Explicit destination (bypasses routing engine).
            result:         Step completion result ('pass'/'fail'/'rework')
                            for graph-based conditional routing.
            disposition:    Operator-selected label for MRB/disposition steps.

        If target_step_id is None, the routing engine determines the next step
        using transitions (if defined) or linear sequence fallback.
        If there is no next step, the unit is completed.
        """
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status not in ("in_process", "queued"):
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "move",
            )

        from_step_id = unit.current_step_id

        # Close any open history record for the current step
        if from_step_id is not None:
            close_stmt = (
                select(SegmentResponseUnit)
                .where(
                    SegmentResponseUnit.unit_id == unit_id,
                    SegmentResponseUnit.step_id == from_step_id,
                    SegmentResponseUnit.exited_at.is_(None),
                )
                .order_by(SegmentResponseUnit.entered_at.desc())
            )
            close_result = await session.execute(close_stmt)
            open_history = close_result.scalar_one_or_none()
            if open_history is not None:
                now = datetime.now(timezone.utc)
                open_history.exited_at = now
                open_history.exited_at_utc = now.replace(tzinfo=None)
                open_history.result = result or open_history.result
                await session.flush()

        if target_step_id is not None:
            unit.current_step_id = target_step_id
        else:
            # Use routing engine (graph-aware)
            from mes.core.routing.service import RoutingEngineService

            # If no explicit result, look up the last history record
            step_result = result
            if step_result is None and from_step_id is not None:
                hist_stmt = (
                    select(SegmentResponseUnit)
                    .where(
                        SegmentResponseUnit.unit_id == unit_id,
                        SegmentResponseUnit.step_id == from_step_id,
                    )
                    .order_by(SegmentResponseUnit.entered_at.desc())
                    .limit(1)
                )
                hist_result = await session.execute(hist_stmt)
                last_hist = hist_result.scalar_one_or_none()
                if last_hist is not None:
                    step_result = last_hist.result

            next_step = await RoutingEngineService.get_next_step(
                session, unit.order_id, unit.current_step_id,
                result=step_result, disposition=disposition,
            )
            if next_step is None:
                # No more steps — unit is complete
                unit.status = "completed"
                unit.current_step_id = None
                unit.current_equipment_id = None
                await session.flush()

                # Increment order completed count
                await OperationsRequestService.increment_completed(
                    session, unit.order_id,
                )
                await event_bus.publish(
                    unit_moved(str(unit.id), str(from_step_id), None)
                )
                logger.info("Unit %s completed all route steps", unit.id)
                return unit

            unit.current_step_id = next_step.id

        # On any step change, equipment must be re-assigned by dispatch
        # for the new step.  (Dispatch is decoupled: it runs as a deferred
        # event handler against wip.unit.moved.)
        if unit.current_step_id != from_step_id:
            unit.current_equipment_id = None

        unit.status = "queued"
        await session.flush()

        _publish_after_commit(
            unit_moved(
                str(unit.id),
                str(from_step_id) if from_step_id else None,
                str(unit.current_step_id) if unit.current_step_id else None,
            )
        )
        logger.info("Moved unit %s to step %s", unit.id, unit.current_step_id)
        return unit

    @staticmethod
    async def hold_unit(
        session: AsyncSession, unit_id: UUID, reason: str,
    ) -> Unit:
        """Place a unit on hold."""
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status in ("completed", "scrapped"):
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "hold",
            )
        unit.status = "on_hold"
        await session.flush()

        await event_bus.publish(unit_held(str(unit.id), reason))
        logger.info("Held unit %s: %s", unit.id, reason)
        return unit

    @staticmethod
    async def release_hold_unit(
        session: AsyncSession, unit_id: UUID,
    ) -> Unit:
        """Release a unit from hold, returning it to 'queued'."""
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status != "on_hold":
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "release-hold",
            )
        unit.status = "queued"
        await session.flush()

        await event_bus.publish(unit_released(str(unit.id)))
        logger.info("Released hold on unit %s", unit.id)
        return unit

    @staticmethod
    async def scrap_unit(
        session: AsyncSession,
        unit_id: UUID,
        reason: str,
        disposition: str | None = None,
        defect_code_id: UUID | None = None,
        failure_mode: str | None = None,
    ) -> Unit:
        """Scrap a unit. Persists scrap context and increments the order's scrapped count."""
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status in ("completed", "scrapped"):
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "scrap",
            )
        step_id = unit.current_step_id
        now = datetime.now(timezone.utc)
        unit.status = "scrapped"
        unit.current_equipment_id = None
        # Item A: persist scrap context on the unit row
        unit.scrap_reason = reason
        unit.scrap_disposition = disposition
        unit.defect_code_id = defect_code_id
        unit.scrapped_at = now
        await session.flush()

        # Item B: annotate the open history record for this step
        if step_id is not None:
            stmt = (
                select(SegmentResponseUnit)
                .where(
                    SegmentResponseUnit.unit_id == unit_id,
                    SegmentResponseUnit.step_id == step_id,
                    SegmentResponseUnit.exited_at.is_(None),
                )
                .order_by(SegmentResponseUnit.entered_at.desc())
            )
            history_result = await session.execute(stmt)
            history = history_result.scalar_one_or_none()
            if history is not None:
                history.exited_at = now
                history.exited_at_utc = now.replace(tzinfo=None)
                history.result = "fail"
                history.disposition = disposition
                history.failure_mode = failure_mode
                history.defect_code_id = defect_code_id
                history.scrap_reason = reason

        # Item C: auto-create a NonConformance record
        from mes.core.quality.service import NonConformanceService
        await NonConformanceService.create_nc(
            session,
            unit_id=unit_id,
            step_id=step_id,
            nc_type="defect",
            description=reason,
            disposition="scrap",
            status="open",
        )
        await session.flush()

        # Increment order scrapped count
        await OperationsRequestService.increment_scrapped(session, unit.order_id)

        await event_bus.publish(
            unit_scrapped(
                str(unit.id),
                str(step_id) if step_id else None,
                reason,
            )
        )
        logger.info("Scrapped unit %s: %s", unit.id, reason)
        return unit


# ═══════════════════════════════════════════════════════════════════
# LOT SERVICE
# ═══════════════════════════════════════════════════════════════════


class LotService:
    """Service class for lot lifecycle operations."""

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_lots(
        session: AsyncSession,
        params: PaginationParams,
        status: str | None = None,
        order_id: UUID | None = None,
        equipment_id: UUID | None = None,
    ) -> tuple[Sequence[Lot], str | None, bool]:
        stmt = select(Lot).where(Lot.is_active.is_(True)).options(selectinload(Lot.product), selectinload(Lot.order))
        if status is not None:
            stmt = stmt.where(Lot.status == status)
        if order_id is not None:
            stmt = stmt.where(Lot.order_id == order_id)
        if equipment_id is not None:
            stmt = stmt.where(Lot.current_equipment_id == equipment_id)
        return await paginate_query(session, stmt, Lot, params)

    @staticmethod
    async def get_lot(session: AsyncSession, lot_id: UUID) -> Lot:
        stmt = select(Lot).where(Lot.id == lot_id, Lot.is_active.is_(True)).options(selectinload(Lot.product), selectinload(Lot.order))
        result = await session.execute(stmt)
        lot = result.scalar_one_or_none()
        if lot is None:
            raise NotFoundException(resource="Lot", resource_id=str(lot_id))
        return lot

    @staticmethod
    async def get_lot_by_number(
        session: AsyncSession, lot_number: str,
    ) -> Lot:
        """Look up a lot by lot number. Used for barcode scanning."""
        stmt = select(Lot).where(
            Lot.lot_number == lot_number,
            Lot.is_active.is_(True),
        ).options(selectinload(Lot.product), selectinload(Lot.order))
        result = await session.execute(stmt)
        lot = result.scalar_one_or_none()
        if lot is None:
            raise NotFoundException(resource="Lot", resource_id=lot_number)
        return lot

    @staticmethod
    async def get_segment_response_lots(
        session: AsyncSession, lot_id: UUID,
    ) -> Sequence[SegmentResponseLot]:
        await LotService.get_lot(session, lot_id)
        stmt = (
            select(SegmentResponseLot)
            .where(SegmentResponseLot.lot_id == lot_id)
            .order_by(SegmentResponseLot.entered_at)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    # ─── Create ──────────────────────────────────────────────────────

    @staticmethod
    async def create_lot(session: AsyncSession, **kwargs: Any) -> Lot:
        ln = kwargs["lot_number"]
        existing = await session.execute(
            select(Lot).where(Lot.lot_number == ln)
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateLotNumberException(ln)

        lot = Lot(**kwargs)
        session.add(lot)
        await session.flush()

        await OperationsRequestService.start_order(session, lot.order_id)

        await event_bus.publish(
            lot_created(str(lot.id), str(lot.order_id), lot.lot_number, lot.quantity)
        )
        logger.info("Created lot %s (LN=%s, order=%s)", lot.id, ln, lot.order_id)
        return lot

    # ─── Lifecycle ───────────────────────────────────────────────────

    @staticmethod
    async def start_lot(
        session: AsyncSession,
        lot_id: UUID,
        equipment_id: UUID | None = None,
    ) -> Lot:
        lot = await LotService.get_lot(session, lot_id)
        if lot.status not in ("queued", "in_process"):
            raise InvalidWIPTransitionException(
                lot.lot_number, lot.status, "start",
            )

        if lot.current_step_id is None:
            from mes.core.routing.service import RoutingEngineService
            first_step = await RoutingEngineService.get_first_step(
                session, lot.order_id,
            )
            lot.current_step_id = first_step.id

        if equipment_id is not None:
            lot.current_equipment_id = equipment_id
        elif lot.current_equipment_id is None:
            # Auto-dispatch: pick a recommended equipment via DISPATCH module.
            # Silently no-op if dispatch is blocked — operator can assign later.
            from mes.core.dispatch.service import DispatchService
            try:
                await DispatchService.auto_dispatch(session, lot_id=lot.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Auto-dispatch failed for lot %s on start: %s",
                    lot.id, exc,
                )
        lot.status = "in_process"
        await session.flush()

        now = datetime.now(timezone.utc)
        ws_name, sft_name, tm_name = await _resolve_shift_context(
            session, lot.current_equipment_id, now,
        )
        history = SegmentResponseLot(
            lot_id=lot.id,
            step_id=lot.current_step_id,
            equipment_id=lot.current_equipment_id,
            entered_at=now,
            entered_at_utc=now.replace(tzinfo=None),
            quantity_in=lot.quantity,
            work_schedule_name=ws_name,
            shift_name=sft_name,
            team_name=tm_name,
        )
        session.add(history)
        await session.flush()

        await event_bus.publish(
            lot_started(
                str(lot.id),
                str(lot.current_step_id),
                str(lot.current_equipment_id) if lot.current_equipment_id else None,
            )
        )
        logger.info("Started lot %s at step %s", lot.id, lot.current_step_id)
        return lot

    @staticmethod
    async def complete_lot_step(
        session: AsyncSession,
        lot_id: UUID,
        quantity_out: int | None = None,
        quantity_scrapped: int = 0,
        disposition: str | None = None,
        result: str = "pass",
        failure_mode: str | None = None,
        defect_code_id: UUID | None = None,
        data_snapshot: dict | None = None,
    ) -> Lot:
        lot = await LotService.get_lot(session, lot_id)
        if lot.status != "in_process":
            raise InvalidWIPTransitionException(
                lot.lot_number, lot.status, "complete",
            )

        if quantity_out is None:
            quantity_out = lot.quantity - quantity_scrapped

        # Close the open history record
        stmt = (
            select(SegmentResponseLot)
            .where(
                SegmentResponseLot.lot_id == lot_id,
                SegmentResponseLot.step_id == lot.current_step_id,
                SegmentResponseLot.exited_at.is_(None),
            )
            .order_by(SegmentResponseLot.entered_at.desc())
        )
        history_result = await session.execute(stmt)
        history = history_result.scalar_one_or_none()
        entered_at_snapshot = None
        if history is not None:
            now = datetime.now(timezone.utc)
            entered_at_snapshot = history.entered_at
            history.exited_at = now
            history.exited_at_utc = now.replace(tzinfo=None)
            history.quantity_out = quantity_out
            history.quantity_scrapped = quantity_scrapped
            # Item B: persist RCA fields on the history row
            history.result = result if quantity_scrapped == 0 or result != "pass" else "pass"
            history.disposition = disposition
            history.failure_mode = failure_mode
            history.defect_code_id = defect_code_id
            if data_snapshot:
                history.data_snapshot = data_snapshot
            if quantity_scrapped > 0 and not history.scrap_reason:
                history.scrap_reason = failure_mode

        # Update lot quantity to reflect output (may shrink due to scrap)
        lot.quantity = quantity_out

        # Propagate step-level scrap to the production order immediately
        if quantity_scrapped > 0:
            await OperationsRequestService.increment_scrapped(
                session, lot.order_id, quantity_scrapped,
            )

        await session.flush()

        # Item E: write EquipmentActual and MaterialActual rows
        if history is not None and entered_at_snapshot is not None:
            await _write_resource_actuals(
                session,
                segment_response_lot_id=history.id,
                equipment_id=lot.current_equipment_id,
                started_at=entered_at_snapshot,
                ended_at=history.exited_at,
                lot_id=lot_id,
                step_id=lot.current_step_id,
            )
            await session.flush()

        # Item C: auto-create NonConformance when result is fail or there is scrap
        if result == "fail" or quantity_scrapped > 0:
            from mes.core.quality.service import NonConformanceService
            description = failure_mode or (
                f"{quantity_scrapped} unit(s) scrapped at step {lot.current_step_id}"
                if quantity_scrapped > 0 else f"Step failed: {lot.current_step_id}"
            )
            # Use a controlled vocabulary value for NC disposition;
            # never pass the operator's free-text disposition string here.
            nc_disposition = "scrap" if quantity_scrapped > 0 else None
            await NonConformanceService.create_nc(
                session,
                lot_id=lot_id,
                step_id=lot.current_step_id,
                nc_type="defect",
                description=description,
                disposition=nc_disposition,
                status="open",
            )
            await session.flush()

        await event_bus.publish(
            lot_completed(
                str(lot.id), str(lot.current_step_id),
                quantity_out, quantity_scrapped,
            )
        )
        logger.info(
            "Completed step %s for lot %s (out=%d, scrapped=%d)",
            lot.current_step_id, lot.id, quantity_out, quantity_scrapped,
        )
        return lot

    @staticmethod
    async def move_lot(
        session: AsyncSession,
        lot_id: UUID,
        target_step_id: UUID | None = None,
        result: str | None = None,
        disposition: str | None = None,
    ) -> Lot:
        lot = await LotService.get_lot(session, lot_id)
        if lot.status not in ("in_process", "queued"):
            raise InvalidWIPTransitionException(
                lot.lot_number, lot.status, "move",
            )

        from_step_id = lot.current_step_id

        # Close any open history record for the current step
        if from_step_id is not None:
            close_stmt = (
                select(SegmentResponseLot)
                .where(
                    SegmentResponseLot.lot_id == lot_id,
                    SegmentResponseLot.step_id == from_step_id,
                    SegmentResponseLot.exited_at.is_(None),
                )
                .order_by(SegmentResponseLot.entered_at.desc())
            )
            close_result = await session.execute(close_stmt)
            open_history = close_result.scalar_one_or_none()
            if open_history is not None:
                now = datetime.now(timezone.utc)
                open_history.exited_at = now
                open_history.exited_at_utc = now.replace(tzinfo=None)
                await session.flush()

        if target_step_id is not None:
            lot.current_step_id = target_step_id
        else:
            from mes.core.routing.service import RoutingEngineService

            # If no explicit result, look up the last lot history record
            step_result = result
            if step_result is None and from_step_id is not None:
                hist_stmt = (
                    select(SegmentResponseLot)
                    .where(
                        SegmentResponseLot.lot_id == lot_id,
                        SegmentResponseLot.step_id == from_step_id,
                    )
                    .order_by(SegmentResponseLot.entered_at.desc())
                    .limit(1)
                )
                hist_result = await session.execute(hist_stmt)
                last_hist = hist_result.scalar_one_or_none()
                if last_hist is not None and last_hist.quantity_scrapped > 0:
                    step_result = "fail"
                elif last_hist is not None:
                    step_result = "pass"

            next_step = await RoutingEngineService.get_next_step(
                session, lot.order_id, lot.current_step_id,
                result=step_result, disposition=disposition,
            )
            if next_step is None:
                lot.status = "completed"
                lot.current_step_id = None
                lot.current_equipment_id = None
                await session.flush()

                await OperationsRequestService.increment_completed(
                    session, lot.order_id, lot.quantity,
                )
                await event_bus.publish(
                    lot_moved(str(lot.id), str(from_step_id), None)
                )
                logger.info("Lot %s completed all route steps", lot.id)
                return lot

            lot.current_step_id = next_step.id

        # On any step change, equipment must be re-assigned by dispatch
        # for the new step.  (Dispatch is decoupled: it runs as a deferred
        # event handler against wip.lot.moved.)
        if lot.current_step_id != from_step_id:
            lot.current_equipment_id = None

        lot.status = "queued"
        await session.flush()

        _publish_after_commit(
            lot_moved(
                str(lot.id),
                str(from_step_id) if from_step_id else None,
                str(lot.current_step_id) if lot.current_step_id else None,
            )
        )
        logger.info("Moved lot %s to step %s", lot.id, lot.current_step_id)
        return lot

    @staticmethod
    async def hold_lot(
        session: AsyncSession, lot_id: UUID, reason: str,
    ) -> Lot:
        """Place a lot on hold."""
        lot = await LotService.get_lot(session, lot_id)
        if lot.status in ("completed", "scrapped"):
            raise InvalidWIPTransitionException(
                lot.lot_number, lot.status, "hold",
            )
        lot.status = "on_hold"
        await session.flush()

        await event_bus.publish(lot_held(str(lot.id), reason))
        logger.info("Held lot %s: %s", lot.id, reason)
        return lot

    @staticmethod
    async def release_hold_lot(
        session: AsyncSession, lot_id: UUID,
    ) -> Lot:
        """Release a lot from hold, returning it to 'queued'."""
        lot = await LotService.get_lot(session, lot_id)
        if lot.status != "on_hold":
            raise InvalidWIPTransitionException(
                lot.lot_number, lot.status, "release-hold",
            )
        lot.status = "queued"
        await session.flush()

        await event_bus.publish(lot_released(str(lot.id)))
        logger.info("Released hold on lot %s", lot.id)
        return lot

    @staticmethod
    async def scrap_lot(
        session: AsyncSession,
        lot_id: UUID,
        reason: str,
        disposition: str | None = None,
        defect_code_id: UUID | None = None,
        failure_mode: str | None = None,
    ) -> Lot:
        """Scrap a lot. Persists scrap context and increments the order's scrapped count."""
        lot = await LotService.get_lot(session, lot_id)
        if lot.status in ("completed", "scrapped"):
            raise InvalidWIPTransitionException(
                lot.lot_number, lot.status, "scrap",
            )
        step_id = lot.current_step_id
        now = datetime.now(timezone.utc)
        lot.status = "scrapped"
        lot.current_equipment_id = None
        # Item A: persist scrap context on the lot row
        lot.scrap_reason = reason
        lot.scrap_disposition = disposition
        lot.defect_code_id = defect_code_id
        lot.scrapped_at = now
        await session.flush()

        # Item B: annotate the open history record for this step
        if step_id is not None:
            stmt = (
                select(SegmentResponseLot)
                .where(
                    SegmentResponseLot.lot_id == lot_id,
                    SegmentResponseLot.step_id == step_id,
                    SegmentResponseLot.exited_at.is_(None),
                )
                .order_by(SegmentResponseLot.entered_at.desc())
            )
            history_result = await session.execute(stmt)
            history = history_result.scalar_one_or_none()
            if history is not None:
                history.exited_at = now
                history.exited_at_utc = now.replace(tzinfo=None)
                history.result = "fail"
                history.disposition = disposition
                history.failure_mode = failure_mode
                history.defect_code_id = defect_code_id
                history.scrap_reason = reason

        # Item C: auto-create a NonConformance record
        from mes.core.quality.service import NonConformanceService
        await NonConformanceService.create_nc(
            session,
            lot_id=lot_id,
            step_id=step_id,
            nc_type="defect",
            description=reason,
            disposition="scrap",
            status="open",
        )
        await session.flush()

        await OperationsRequestService.increment_scrapped(
            session, lot.order_id, lot.quantity,
        )

        await event_bus.publish(
            lot_scrapped(
                str(lot.id),
                str(step_id) if step_id else None,
                reason,
                lot.quantity,
            )
        )
        logger.info("Scrapped lot %s (qty=%d): %s", lot.id, lot.quantity, reason)
        return lot
