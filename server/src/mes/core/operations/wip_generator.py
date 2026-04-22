"""
OPS-REQUEST: Background task that generates WIP (lots/units) for released operations requests.

Polls the database every ``interval`` seconds for production orders in
``released`` status.  For each order:

- **process** products (``product_type == "process"``) → one lot with the
  full ``quantity_ordered``.
- **discrete** products (``product_type == "discrete"``) → N individual
  units, one per piece in ``quantity_ordered``.

After WIP is created the order auto-transitions to ``in_progress``
(handled by ``UnitService.create_unit`` / ``LotService.create_lot``).
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.core.product_def.models import ProductDefinition
from mes.core.operations.models import OperationsRequest
from mes.core.wip.serial import SerialNumberService
from mes.core.wip.service import LotService, UnitService

logger = logging.getLogger("mes.production.wip_generator")

WIP_GENERATOR_INTERVAL_SEC = 5  # default polling interval


async def _generate_wip_for_order(session: AsyncSession, order: OperationsRequest) -> int:
    """
    Create lots or units for a single released order.

    Returns the number of WIP items created.
    """
    product = await session.get(ProductDefinition, order.product_id)
    if product is None:
        logger.warning(
            "Order %s references missing product %s — skipping",
            order.order_number,
            order.product_id,
        )
        return 0

    if product.product_type == "process":
        # Batch / lot-tracked: one lot with the full quantity
        lot_number = await SerialNumberService.generate_lot_number(
            session, order.id,
        )
        await LotService.create_lot(
            session,
            lot_number=lot_number,
            order_id=order.id,
            product_id=order.product_id,
            quantity=order.quantity_ordered,
        )
        return 1
    else:
        # Discrete / unit-tracked: one unit per piece
        count = 0
        for _ in range(order.quantity_ordered):
            serial = await SerialNumberService.generate_serial_number(
                session, order.id,
            )
            await UnitService.create_unit(
                session,
                serial_number=serial,
                order_id=order.id,
                product_id=order.product_id,
            )
            count += 1
        return count


async def process_released_orders(session: AsyncSession) -> int:
    """
    Find all released orders and generate WIP for each.

    Returns the total number of WIP items created across all orders.
    """
    stmt = (
        select(OperationsRequest)
        .where(
            OperationsRequest.status == "released",
            OperationsRequest.is_active.is_(True),
        )
        .order_by(OperationsRequest.priority.desc(), OperationsRequest.created_at)
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()

    if not orders:
        return 0

    total = 0
    for order in orders:
        try:
            created = await _generate_wip_for_order(session, order)
            total += created
        except Exception:
            logger.exception(
                "Failed to generate WIP for order %s — skipping",
                order.order_number,
            )
    return total


async def wip_generator_loop(interval: int = WIP_GENERATOR_INTERVAL_SEC) -> None:
    """
    Long-running background coroutine.

    Wakes every *interval* seconds, opens a fresh DB session,
    processes all released orders, and commits.
    """
    from mes.framework.db import async_session_factory

    logger.info(
        "WIP generator started (interval=%ds)",
        interval,
    )
    while True:
        await asyncio.sleep(interval)
        try:
            async with async_session_factory() as session:
                created = await process_released_orders(session)
                await session.commit()
                if created > 0:
                    logger.info("WIP generator: created %d items", created)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("WIP generator processing error")
