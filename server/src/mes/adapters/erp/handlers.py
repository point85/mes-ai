"""
ERP Adapter: Event handlers for automatic outbound reporting.

When a lot/unit completes a step, auto-enqueue ERP outbound reports:
- Completion report (qty produced at the step)
- Consumption report (BOM materials consumed at the step — future)

Handlers are auto-registered via @event_handler at import time and
subscribed to the event bus during application startup.

Trigger flow:
  1. Operator/equipment completes work at a step → wip.lot.completed event
  2. Handler looks up production order (erp_reference) and route step (erp_operation_number)
  3. Enqueues a completion report to the ERP outbound queue
  4. Queue processes it → sends to ERP adapter → retry on failure
"""

from __future__ import annotations

import logging
from uuid import UUID

from mes.framework.db import async_session_factory
from mes.framework.events.decorators import event_handler
from mes.framework.events.schema import MESEvent

logger = logging.getLogger("mes.adapters.erp.handlers")


@event_handler("wip.lot.completed")
async def on_lot_completed_erp_report(event: MESEvent) -> None:
    """
    Auto-enqueue ERP completion report when a lot completes a step.

    Uses the production order's erp_reference and the route step's
    erp_operation_number to build the outbound report.
    """
    lot_id_str = event.payload.get("lot_id")
    step_id_str = event.payload.get("step_id")
    quantity_out = event.payload.get("quantity_out", 0)
    quantity_scrapped = event.payload.get("quantity_scrapped", 0)

    if not lot_id_str or not step_id_str:
        return

    from sqlalchemy import select
    from mes.core.wip.models import Lot
    from mes.core.production.models import ProductionOrder
    from mes.core.product_def.models import ProcessSegment
    from mes.adapters.erp.queue import ERPOutboundQueueService

    async with async_session_factory() as session:
        try:
            # Look up lot → order → erp_reference
            lot_result = await session.execute(
                select(Lot).where(Lot.id == UUID(lot_id_str))
            )
            lot = lot_result.scalar_one_or_none()
            if lot is None:
                return

            order_result = await session.execute(
                select(ProductionOrder).where(ProductionOrder.id == lot.order_id)
            )
            order = order_result.scalar_one_or_none()
            if order is None or order.erp_reference is None:
                # No ERP reference — nothing to report
                return

            # Look up step → erp_operation_number
            step_result = await session.execute(
                select(ProcessSegment).where(ProcessSegment.id == UUID(step_id_str))
            )
            step = step_result.scalar_one_or_none()
            erp_op = step.erp_operation_number if step else None

            # Enqueue completion report
            await ERPOutboundQueueService.enqueue(
                session,
                report_type="completion",
                payload={
                    "order_id": order.erp_reference,
                    "qty_good": quantity_out,
                    "qty_reject": quantity_scrapped,
                    "step_id": erp_op,
                    "lot_id": lot_id_str,
                    "lot_number": lot.lot_number,
                },
            )
            await session.commit()

            logger.info(
                "Enqueued ERP completion for lot %s step %s (good=%d scrap=%d)",
                lot.lot_number, erp_op or step_id_str, quantity_out, quantity_scrapped,
            )
        except Exception:
            logger.exception("Failed to enqueue ERP report for lot %s", lot_id_str)
            await session.rollback()


@event_handler("wip.unit.completed")
async def on_unit_completed_erp_report(event: MESEvent) -> None:
    """
    Auto-enqueue ERP completion report when a unit completes a step.

    Units always report qty_good=1 (single piece tracking).
    """
    unit_id_str = event.payload.get("unit_id")
    step_id_str = event.payload.get("step_id")
    result = event.payload.get("result", "pass")

    if not unit_id_str or not step_id_str:
        return

    from sqlalchemy import select
    from mes.core.wip.models import Unit
    from mes.core.production.models import ProductionOrder
    from mes.core.product_def.models import ProcessSegment
    from mes.adapters.erp.queue import ERPOutboundQueueService

    async with async_session_factory() as session:
        try:
            unit_result = await session.execute(
                select(Unit).where(Unit.id == UUID(unit_id_str))
            )
            unit = unit_result.scalar_one_or_none()
            if unit is None:
                return

            order_result = await session.execute(
                select(ProductionOrder).where(ProductionOrder.id == unit.order_id)
            )
            order = order_result.scalar_one_or_none()
            if order is None or order.erp_reference is None:
                return

            step_result = await session.execute(
                select(ProcessSegment).where(ProcessSegment.id == UUID(step_id_str))
            )
            step = step_result.scalar_one_or_none()
            erp_op = step.erp_operation_number if step else None

            qty_good = 1 if result == "pass" else 0
            qty_reject = 0 if result == "pass" else 1

            await ERPOutboundQueueService.enqueue(
                session,
                report_type="completion",
                payload={
                    "order_id": order.erp_reference,
                    "qty_good": qty_good,
                    "qty_reject": qty_reject,
                    "step_id": erp_op,
                    "unit_id": unit_id_str,
                    "serial_number": unit.serial_number,
                },
            )
            await session.commit()

            logger.info(
                "Enqueued ERP completion for unit %s step %s (result=%s)",
                unit.serial_number, erp_op or step_id_str, result,
            )
        except Exception:
            logger.exception("Failed to enqueue ERP report for unit %s", unit_id_str)
            await session.rollback()
