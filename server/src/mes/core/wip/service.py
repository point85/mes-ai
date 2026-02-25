"""
WIP-TRACK: Business logic service for units and lots.

Provides CRUD, lifecycle operations (start, complete, move, hold, scrap),
and history queries.  Delegates next-step resolution to the routing engine.
"""

from __future__ import annotations

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

from mes.core.production.service import ProductionOrderService

from .events import (
    unit_created, unit_started, unit_completed, unit_moved,
    unit_scrapped, unit_held, unit_released,
    lot_created, lot_started, lot_completed, lot_moved,
)
from .exceptions import (
    DuplicateSerialNumberException,
    DuplicateLotNumberException,
    InvalidWIPTransitionException,
    NoRouteAssignedException,
    NoNextStepException,
)
from .models import Unit, Lot, UnitHistory, LotHistory

logger = logging.getLogger("mes.wip")


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
    ) -> tuple[Sequence[Unit], str | None, bool]:
        stmt = select(Unit).where(Unit.is_active.is_(True))
        if status is not None:
            stmt = stmt.where(Unit.status == status)
        if order_id is not None:
            stmt = stmt.where(Unit.order_id == order_id)
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
    async def get_unit_history(
        session: AsyncSession, unit_id: UUID,
    ) -> Sequence[UnitHistory]:
        """Get all history records for a unit, ordered by entered_at."""
        # Verify unit exists
        await UnitService.get_unit(session, unit_id)
        stmt = (
            select(UnitHistory)
            .where(UnitHistory.unit_id == unit_id)
            .order_by(UnitHistory.entered_at)
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
        await ProductionOrderService.start_order(session, unit.order_id)

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
        unit.status = "in_process"
        await session.flush()

        # Create history record
        history = UnitHistory(
            unit_id=unit.id,
            step_id=unit.current_step_id,
            equipment_id=unit.current_equipment_id,
            entered_at=datetime.now(timezone.utc),
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
        data_snapshot: dict | None = None,
    ) -> Unit:
        """
        Complete the current step for a unit.
        Updates the open history record with exit time and result.
        """
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status != "in_process":
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "complete",
            )

        # Close the open history record for the current step
        stmt = (
            select(UnitHistory)
            .where(
                UnitHistory.unit_id == unit_id,
                UnitHistory.step_id == unit.current_step_id,
                UnitHistory.exited_at.is_(None),
            )
            .order_by(UnitHistory.entered_at.desc())
        )
        history_result = await session.execute(stmt)
        history = history_result.scalar_one_or_none()
        if history is not None:
            history.exited_at = datetime.now(timezone.utc)
            history.result = result
            history.data_snapshot = data_snapshot

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
    ) -> Unit:
        """
        Move a unit to the next step (or specific target step).
        If target_step_id is None, the routing engine determines the next step.
        If there is no next step, the unit is completed.
        """
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status not in ("in_process", "queued"):
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "move",
            )

        from_step_id = unit.current_step_id

        if target_step_id is not None:
            unit.current_step_id = target_step_id
        else:
            # Use routing engine
            from mes.core.routing.service import RoutingEngineService
            next_step = await RoutingEngineService.get_next_step(
                session, unit.order_id, unit.current_step_id,
            )
            if next_step is None:
                # No more steps — unit is complete
                unit.status = "completed"
                unit.current_step_id = None
                unit.current_equipment_id = None
                await session.flush()

                # Increment order completed count
                await ProductionOrderService.increment_completed(
                    session, unit.order_id,
                )
                await event_bus.publish(
                    unit_moved(str(unit.id), str(from_step_id), None)
                )
                logger.info("Unit %s completed all route steps", unit.id)
                return unit

            unit.current_step_id = next_step.id

        unit.current_equipment_id = None  # Reset equipment on move
        unit.status = "queued"
        await session.flush()

        await event_bus.publish(
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
        session: AsyncSession, unit_id: UUID, reason: str,
    ) -> Unit:
        """Scrap a unit. Increments the order's scrapped count."""
        unit = await UnitService.get_unit(session, unit_id)
        if unit.status in ("completed", "scrapped"):
            raise InvalidWIPTransitionException(
                unit.serial_number, unit.status, "scrap",
            )
        step_id = unit.current_step_id
        unit.status = "scrapped"
        unit.current_equipment_id = None
        await session.flush()

        # Increment order scrapped count
        await ProductionOrderService.increment_scrapped(session, unit.order_id)

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
    ) -> tuple[Sequence[Lot], str | None, bool]:
        stmt = select(Lot).where(Lot.is_active.is_(True))
        if status is not None:
            stmt = stmt.where(Lot.status == status)
        if order_id is not None:
            stmt = stmt.where(Lot.order_id == order_id)
        return await paginate_query(session, stmt, Lot, params)

    @staticmethod
    async def get_lot(session: AsyncSession, lot_id: UUID) -> Lot:
        stmt = select(Lot).where(Lot.id == lot_id, Lot.is_active.is_(True))
        result = await session.execute(stmt)
        lot = result.scalar_one_or_none()
        if lot is None:
            raise NotFoundException(resource="Lot", resource_id=str(lot_id))
        return lot

    @staticmethod
    async def get_lot_history(
        session: AsyncSession, lot_id: UUID,
    ) -> Sequence[LotHistory]:
        await LotService.get_lot(session, lot_id)
        stmt = (
            select(LotHistory)
            .where(LotHistory.lot_id == lot_id)
            .order_by(LotHistory.entered_at)
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

        await ProductionOrderService.start_order(session, lot.order_id)

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
        lot.status = "in_process"
        await session.flush()

        history = LotHistory(
            lot_id=lot.id,
            step_id=lot.current_step_id,
            equipment_id=lot.current_equipment_id,
            entered_at=datetime.now(timezone.utc),
            quantity_in=lot.quantity,
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
            select(LotHistory)
            .where(
                LotHistory.lot_id == lot_id,
                LotHistory.step_id == lot.current_step_id,
                LotHistory.exited_at.is_(None),
            )
            .order_by(LotHistory.entered_at.desc())
        )
        history_result = await session.execute(stmt)
        history = history_result.scalar_one_or_none()
        if history is not None:
            history.exited_at = datetime.now(timezone.utc)
            history.quantity_out = quantity_out
            history.quantity_scrapped = quantity_scrapped

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
    ) -> Lot:
        lot = await LotService.get_lot(session, lot_id)
        if lot.status not in ("in_process", "queued"):
            raise InvalidWIPTransitionException(
                lot.lot_number, lot.status, "move",
            )

        from_step_id = lot.current_step_id

        if target_step_id is not None:
            lot.current_step_id = target_step_id
        else:
            from mes.core.routing.service import RoutingEngineService
            next_step = await RoutingEngineService.get_next_step(
                session, lot.order_id, lot.current_step_id,
            )
            if next_step is None:
                lot.status = "completed"
                lot.current_step_id = None
                lot.current_equipment_id = None
                await session.flush()

                await ProductionOrderService.increment_completed(
                    session, lot.order_id, lot.quantity,
                )
                await event_bus.publish(
                    lot_moved(str(lot.id), str(from_step_id), None)
                )
                logger.info("Lot %s completed all route steps", lot.id)
                return lot

            lot.current_step_id = next_step.id

        lot.current_equipment_id = None
        lot.status = "queued"
        await session.flush()

        await event_bus.publish(
            lot_moved(
                str(lot.id),
                str(from_step_id) if from_step_id else None,
                str(lot.current_step_id) if lot.current_step_id else None,
            )
        )
        logger.info("Moved lot %s to step %s", lot.id, lot.current_step_id)
        return lot
