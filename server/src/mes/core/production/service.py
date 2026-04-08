"""
PROD-ORDER: Business logic service for production orders.

Provides CRUD, status-lifecycle transitions (release, complete), and
order-level queries.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import order_created, order_released, order_completed, order_started
from .exceptions import (
    DuplicateOrderNumberException,
    InvalidOrderTransitionException,
    OrderNotReleasedException,
)
from .models import ProductionOrder
from .schemas import ORDER_TRANSITIONS

logger = logging.getLogger("mes.production")


class ProductionOrderService:
    """Service class for production-order CRUD and lifecycle operations."""

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_orders(
        session: AsyncSession,
        params: PaginationParams,
        status: str | None = None,
        product_id: UUID | None = None,
    ) -> tuple[Sequence[ProductionOrder], str | None, bool]:
        """List active production orders with optional filters."""
        stmt = select(ProductionOrder).where(ProductionOrder.is_active.is_(True))
        if status is not None:
            stmt = stmt.where(ProductionOrder.status == status)
        if product_id is not None:
            stmt = stmt.where(ProductionOrder.product_id == product_id)
        return await paginate_query(session, stmt, ProductionOrder, params)

    @staticmethod
    async def get_order(session: AsyncSession, order_id: UUID) -> ProductionOrder:
        """Get a production order by ID. Raises NotFoundException if missing."""
        stmt = select(ProductionOrder).where(
            ProductionOrder.id == order_id,
            ProductionOrder.is_active.is_(True),
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise NotFoundException(resource="ProductionOrder", resource_id=str(order_id))
        return order

    # ─── Mutations ───────────────────────────────────────────────────

    @staticmethod
    async def create_order(session: AsyncSession, **kwargs: Any) -> ProductionOrder:
        """Create a new production order. Raises DuplicateOrderNumberException if order_number exists."""
        existing = await session.execute(
            select(ProductionOrder).where(
                ProductionOrder.order_number == kwargs["order_number"]
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateOrderNumberException(kwargs["order_number"])

        order = ProductionOrder(**kwargs)
        # Sync planned date _utc columns
        if order.planned_start is not None:
            order.planned_start_utc = order.planned_start
        if order.planned_end is not None:
            order.planned_end_utc = order.planned_end
        session.add(order)
        await session.flush()

        await event_bus.publish(
            order_created(str(order.id), order.order_number, str(order.product_id))
        )
        logger.info(
            "Created production order %s (%s)", order.id, order.order_number,
        )
        return order

    @staticmethod
    async def update_order(
        session: AsyncSession, order_id: UUID, **kwargs: Any,
    ) -> ProductionOrder:
        """Update a production order's fields. Only non-None values are applied."""
        order = await ProductionOrderService.get_order(session, order_id)

        # Check order_number uniqueness if changing
        new_number = kwargs.get("order_number")
        if new_number is not None and new_number != order.order_number:
            existing = await session.execute(
                select(ProductionOrder).where(
                    ProductionOrder.order_number == new_number,
                    ProductionOrder.id != order_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateOrderNumberException(new_number)

        for key, value in kwargs.items():
            if value is not None:
                setattr(order, key, value)
        await session.flush()

        logger.info("Updated production order %s (%s)", order.id, order.order_number)
        return order

    @staticmethod
    async def delete_order(session: AsyncSession, order_id: UUID) -> None:
        """Soft-delete a production order."""
        order = await ProductionOrderService.get_order(session, order_id)
        order.is_active = False
        await session.flush()
        logger.info("Soft-deleted production order %s (%s)", order.id, order.order_number)

    # ─── Lifecycle transitions ───────────────────────────────────────

    @staticmethod
    def _validate_transition(order: ProductionOrder, target_status: str) -> None:
        """Check that a status transition is allowed."""
        allowed = ORDER_TRANSITIONS.get(order.status, set())
        if target_status not in allowed:
            raise InvalidOrderTransitionException(
                order.order_number, order.status, target_status,
            )

    @staticmethod
    async def release_order(session: AsyncSession, order_id: UUID) -> ProductionOrder:
        """
        Transition an order from 'created' to 'released'.
        Makes it available for production (units/lots can be created against it).
        """
        order = await ProductionOrderService.get_order(session, order_id)
        ProductionOrderService._validate_transition(order, "released")
        order.status = "released"
        await session.flush()

        await event_bus.publish(
            order_released(str(order.id), str(order.product_id), order.quantity_ordered)
        )
        logger.info("Released production order %s (%s)", order.id, order.order_number)
        return order

    @staticmethod
    async def start_order(session: AsyncSession, order_id: UUID) -> ProductionOrder:
        """
        Transition an order from 'released' to 'in_progress'.
        Called automatically when the first unit/lot starts processing.
        """
        order = await ProductionOrderService.get_order(session, order_id)
        if order.status == "in_progress":
            return order  # idempotent
        ProductionOrderService._validate_transition(order, "in_progress")
        order.status = "in_progress"
        now = datetime.now(timezone.utc)
        order.actual_start = now
        order.actual_start_utc = now
        await session.flush()

        await event_bus.publish(order_started(str(order.id)))
        logger.info("Started production order %s (%s)", order.id, order.order_number)
        return order

    @staticmethod
    async def complete_order(session: AsyncSession, order_id: UUID) -> ProductionOrder:
        """
        Transition an order from 'in_progress' to 'completed'.
        """
        order = await ProductionOrderService.get_order(session, order_id)
        ProductionOrderService._validate_transition(order, "completed")
        order.status = "completed"
        now = datetime.now(timezone.utc)
        order.actual_end = now
        order.actual_end_utc = now
        await session.flush()

        await event_bus.publish(
            order_completed(str(order.id), order.quantity_completed)
        )
        logger.info(
            "Completed production order %s (%s) — %d completed, %d scrapped",
            order.id, order.order_number,
            order.quantity_completed, order.quantity_scrapped,
        )
        return order

    @staticmethod
    async def close_order(session: AsyncSession, order_id: UUID) -> ProductionOrder:
        """
        Transition an order to 'closed'. Can be called from any non-closed status.
        """
        order = await ProductionOrderService.get_order(session, order_id)
        ProductionOrderService._validate_transition(order, "closed")
        order.status = "closed"
        if order.actual_end is None:
            now = datetime.now(timezone.utc)
            order.actual_end = now
            order.actual_end_utc = now
        await session.flush()

        logger.info("Closed production order %s (%s)", order.id, order.order_number)
        return order

    @staticmethod
    async def increment_completed(
        session: AsyncSession, order_id: UUID, qty: int = 1,
    ) -> ProductionOrder:
        """Increment quantity_completed. Called when a unit/lot finishes final step."""
        order = await ProductionOrderService.get_order(session, order_id)
        order.quantity_completed += qty
        await session.flush()
        return order

    @staticmethod
    async def increment_scrapped(
        session: AsyncSession, order_id: UUID, qty: int = 1,
    ) -> ProductionOrder:
        """Increment quantity_scrapped. Called when a unit/lot is scrapped."""
        order = await ProductionOrderService.get_order(session, order_id)
        order.quantity_scrapped += qty
        await session.flush()
        return order
