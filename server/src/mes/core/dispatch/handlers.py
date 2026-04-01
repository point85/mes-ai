"""
DISPATCH: Event handlers for automatic dispatching.

Handlers are auto-registered via @event_handler at import time and
subscribed to the event bus during application startup.

Trigger flow:
  1. Equipment completes work on a lot → wip.lot.completed event
  2. Handler evaluates dispatch options (capability + capacity + availability)
  3. If destination found → auto-dispatch (shortest_queue strategy)
  4. If no destination → lot stays at current step (blocked), event emitted
"""

from __future__ import annotations

import logging
from uuid import UUID

from mes.framework.db import async_session_factory
from mes.framework.events.decorators import event_handler
from mes.framework.events.schema import MESEvent

from .schemas import DispatchEvaluateResponse

logger = logging.getLogger("mes.dispatch.handlers")


@event_handler("wip.lot.completed")
async def on_lot_completed(event: MESEvent) -> None:
    """
    Auto-dispatch a lot after step completion.

    Triggered by any lot completion source: OPC-UA data change, MQTT message,
    or operator manual interaction (all go through LotService.complete_lot_step
    which publishes this event).
    """
    lot_id_str = event.payload.get("lot_id")
    if not lot_id_str:
        return

    logger.info("Auto-dispatch triggered for lot %s (step completed)", lot_id_str)

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


@event_handler("wip.unit.completed")
async def on_unit_completed(event: MESEvent) -> None:
    """
    Auto-dispatch a unit after step completion.

    Same trigger mechanism as lot completion.
    """
    unit_id_str = event.payload.get("unit_id")
    if not unit_id_str:
        return

    logger.info("Auto-dispatch triggered for unit %s (step completed)", unit_id_str)

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
