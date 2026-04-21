"""
WIP-TRACK: Serial number and lot number auto-generation service.

Provides template-based auto-generation with atomic sequence counters.
Templates use Python str.format() placeholders:

    "SN-{order}-{seq:05d}"   → "SN-WO-2026-001-00001"
    "LOT-{date}-{seq:04d}"   → "LOT-20260402-0001"

Available template variables:
    {seq}    — auto-incrementing sequence counter (per order)
    {order}  — production order number
    {product}— product code
    {date}   — current date as YYYYMMDD
    {year}   — 4-digit year
    {month}  — 2-digit month
    {day}    — 2-digit day
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.core.operations.models import OperationsRequest
from mes.core.product_def.models import ProductDefinition

logger = logging.getLogger("mes.wip.serial")

# Default templates (overridable per call)
DEFAULT_SERIAL_TEMPLATE = "SN-{order}-{seq:05d}"
DEFAULT_LOT_TEMPLATE = "LOT-{order}-{seq:04d}"


class SerialNumberService:
    """Generate unique serial numbers and lot numbers from templates."""

    @staticmethod
    async def generate_serial_number(
        session: AsyncSession,
        order_id: UUID,
        template: str | None = None,
    ) -> str:
        """
        Generate the next serial number for an order.

        Uses atomic counting of existing units on the order to derive
        the sequence number, ensuring uniqueness even under concurrency
        (the caller still validates uniqueness before committing).
        """
        from mes.core.wip.models import Unit

        tpl = template or DEFAULT_SERIAL_TEMPLATE
        order, product = await _load_context(session, order_id)
        now = datetime.now(timezone.utc)

        # Count existing units for this order to get sequence
        count_stmt = (
            select(func.count())
            .select_from(Unit)
            .where(Unit.order_id == order_id)
        )
        result = await session.execute(count_stmt)
        seq = (result.scalar() or 0) + 1

        return _format_template(tpl, order, product, seq, now)

    @staticmethod
    async def generate_lot_number(
        session: AsyncSession,
        order_id: UUID,
        template: str | None = None,
    ) -> str:
        """Generate the next lot number for an order."""
        from mes.core.wip.models import Lot

        tpl = template or DEFAULT_LOT_TEMPLATE
        order, product = await _load_context(session, order_id)
        now = datetime.now(timezone.utc)

        count_stmt = (
            select(func.count())
            .select_from(Lot)
            .where(Lot.order_id == order_id)
        )
        result = await session.execute(count_stmt)
        seq = (result.scalar() or 0) + 1

        return _format_template(tpl, order, product, seq, now)


async def _load_context(
    session: AsyncSession, order_id: UUID,
) -> tuple[OperationsRequest, ProductDefinition | None]:
    """Load order and product for template variable resolution."""
    from mes.core.operations.models import OperationsRequest as PO
    from mes.core.product_def.models import ProductDefinition as PD

    stmt = select(PO).where(PO.id == order_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        from mes.framework.api.exceptions import NotFoundException
        raise NotFoundException(resource="OperationsRequest", resource_id=str(order_id))

    product = None
    if order.product_id:
        p_stmt = select(PD).where(PD.id == order.product_id)
        p_result = await session.execute(p_stmt)
        product = p_result.scalar_one_or_none()

    return order, product


def _format_template(
    template: str,
    order: OperationsRequest,
    product: ProductDefinition | None,
    seq: int,
    now: datetime,
) -> str:
    """Fill a template string with available variables."""
    variables = {
        "seq": seq,
        "order": order.order_number,
        "product": product.code if product else "UNKNOWN",
        "date": now.strftime("%Y%m%d"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
    }
    return template.format(**variables)
