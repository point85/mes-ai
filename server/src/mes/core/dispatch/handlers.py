"""
DISPATCH: Event handlers for automatic dispatching.

Handlers are auto-registered via @event_handler at import time and
subscribed to the event bus during application startup.

Trigger flow:
  1. WIP advances to a new step via WIPService.move_unit/move_lot
     (the routing engine has decided the next step) → wip.unit.moved
     / wip.lot.moved event fires.
  2. Handler evaluates dispatch options at the WIP's NEW current step
     (capability + capacity + availability).
  3. If destination found → auto-dispatch (shortest_queue strategy)
     assigns equipment to the WIP at its current step.
  4. If no destination → WIP stays at the step (blocked), event emitted.

Important: dispatch ONLY assigns equipment. It never advances steps.
The routing engine is the single source of truth for step transitions.
"""

from __future__ import annotations

import logging
from uuid import UUID

from mes.framework.db import async_session_factory
from mes.framework.events.decorators import event_handler
from mes.framework.events.schema import MESEvent

from .schemas import DispatchEvaluateResponse

logger = logging.getLogger("mes.dispatch.handlers")


@event_handler("wip.lot.moved")
async def on_lot_moved(event: MESEvent) -> None:
    """
    Auto-dispatch a lot after it advances to a new step.

    Skipped when the lot has reached the end of its route
    (to_step_id is None).
    """
    lot_id_str = event.payload.get("lot_id")
    to_step_id = event.payload.get("to_step_id")
    if not lot_id_str or not to_step_id:
        return

    logger.info(
        "Auto-dispatch triggered for lot %s (moved to step %s)",
        lot_id_str, to_step_id,
    )

    from .service import DispatchService

    async with async_session_factory() as session:
        try:
            result = await DispatchService.auto_dispatch(
                session, lot_id=UUID(lot_id_str),
            )
            await session.commit()

            if isinstance(result, DispatchEvaluateResponse) and result.blocked:
                logger.warning(
                    "Lot %s blocked: %s", lot_id_str, result.blocked_reason,
                )
            else:
                logger.info("Lot %s auto-dispatched successfully", lot_id_str)
        except Exception:
            logger.exception("Auto-dispatch failed for lot %s", lot_id_str)
            await session.rollback()


@event_handler("wip.unit.moved")
async def on_unit_moved(event: MESEvent) -> None:
    """
    Auto-dispatch a unit after it advances to a new step.

    Skipped when the unit has reached the end of its route
    (to_step_id is None).
    """
    unit_id_str = event.payload.get("unit_id")
    to_step_id = event.payload.get("to_step_id")
    if not unit_id_str or not to_step_id:
        return

    logger.info(
        "Auto-dispatch triggered for unit %s (moved to step %s)",
        unit_id_str, to_step_id,
    )

    from .service import DispatchService

    async with async_session_factory() as session:
        try:
            result = await DispatchService.auto_dispatch(
                session, unit_id=UUID(unit_id_str),
            )
            await session.commit()

            if isinstance(result, DispatchEvaluateResponse) and result.blocked:
                logger.warning(
                    "Unit %s blocked: %s", unit_id_str, result.blocked_reason,
                )
            else:
                logger.info("Unit %s auto-dispatched successfully", unit_id_str)
        except Exception:
            logger.exception("Auto-dispatch failed for unit %s", unit_id_str)
            await session.rollback()


@event_handler("wip.lot.completed")
async def on_lot_completed(event: MESEvent) -> None:
    """Hook for post-lot-completion actions (e.g. quality checks, reporting)."""
    pass


@event_handler("wip.unit.completed")
async def on_unit_completed(event: MESEvent) -> None:
    """Hook for post-unit-completion actions (e.g. quality checks, reporting)."""
    pass
