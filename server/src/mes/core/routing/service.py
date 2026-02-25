"""
ROUTE-ENGINE: Routing engine service for determining step progression.

Provides runtime logic for:
- Determining the first step in a route
- Determining the next step for a unit/lot given the current step
- Resolving the assigned route for a production order

Route definition models (ProcessRoute, RouteStep, StepParameter) live in
the product_def module since they are tightly coupled to ProductDefinition.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.core.product_def.models import ProcessRoute, RouteStep
from mes.core.production.models import ProductionOrder
from mes.framework.api.exceptions import NotFoundException
from mes.core.wip.exceptions import NoRouteAssignedException, NoNextStepException

logger = logging.getLogger("mes.routing")


class RoutingEngineService:
    """
    Runtime routing engine — resolves step progression for WIP.

    Route steps are ordered by their `sequence` field.
    The engine finds the current step's position and returns the next step
    in sequence order, or None if the current step is the last one.
    """

    @staticmethod
    async def get_route_for_order(
        session: AsyncSession, order_id: UUID,
    ) -> ProcessRoute:
        """
        Resolve the process route for a production order.

        Priority:
        1. order.route_id (explicitly assigned route)
        2. Product's default route (is_default=True)
        3. First route found for the product (fallback)
        Raises NoRouteAssignedException if none found.
        """
        # Load the order
        stmt = select(ProductionOrder).where(ProductionOrder.id == order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise NotFoundException(resource="ProductionOrder", resource_id=str(order_id))

        # 1. Explicitly assigned route
        if order.route_id is not None:
            route_stmt = (
                select(ProcessRoute)
                .where(ProcessRoute.id == order.route_id, ProcessRoute.is_active.is_(True))
                .options(selectinload(ProcessRoute.steps))
            )
            route_result = await session.execute(route_stmt)
            route = route_result.scalar_one_or_none()
            if route is not None:
                return route

        # 2. Product's default active route
        default_stmt = (
            select(ProcessRoute)
            .where(
                ProcessRoute.product_id == order.product_id,
                ProcessRoute.is_default.is_(True),
                ProcessRoute.is_active.is_(True),
            )
            .options(selectinload(ProcessRoute.steps))
        )
        default_result = await session.execute(default_stmt)
        default_route = default_result.scalar_one_or_none()
        if default_route is not None:
            return default_route

        # 3. Fallback: first active route for the product
        fallback_stmt = (
            select(ProcessRoute)
            .where(
                ProcessRoute.product_id == order.product_id,
                ProcessRoute.is_active.is_(True),
            )
            .options(selectinload(ProcessRoute.steps))
            .order_by(ProcessRoute.created_at)
            .limit(1)
        )
        fallback_result = await session.execute(fallback_stmt)
        fallback_route = fallback_result.scalar_one_or_none()
        if fallback_route is not None:
            return fallback_route

        raise NoRouteAssignedException(str(order_id))

    @staticmethod
    async def get_first_step(
        session: AsyncSession, order_id: UUID,
    ) -> RouteStep:
        """
        Get the first step in the route for a production order.
        Returns the step with the lowest sequence number.
        """
        route = await RoutingEngineService.get_route_for_order(session, order_id)
        steps = sorted(route.steps, key=lambda s: s.sequence)
        active_steps = [s for s in steps if s.is_active]
        if not active_steps:
            raise NoNextStepException("order:" + str(order_id), None)
        return active_steps[0]

    @staticmethod
    async def get_next_step(
        session: AsyncSession,
        order_id: UUID,
        current_step_id: UUID | None,
    ) -> RouteStep | None:
        """
        Determine the next step after current_step_id in the order's route.

        Returns None if current_step_id is the last step (unit/lot is complete).
        If current_step_id is None, returns the first step.
        """
        if current_step_id is None:
            return await RoutingEngineService.get_first_step(session, order_id)

        route = await RoutingEngineService.get_route_for_order(session, order_id)
        steps = sorted(route.steps, key=lambda s: s.sequence)
        active_steps = [s for s in steps if s.is_active]

        # Find current step's position
        current_index = None
        for i, step in enumerate(active_steps):
            if step.id == current_step_id:
                current_index = i
                break

        if current_index is None:
            # Current step not found in route — treat as complete
            logger.warning(
                "Step %s not found in route %s — returning None (complete)",
                current_step_id, route.id,
            )
            return None

        # Return next step or None if at end
        next_index = current_index + 1
        if next_index < len(active_steps):
            return active_steps[next_index]
        return None

    @staticmethod
    async def get_route_steps(
        session: AsyncSession, order_id: UUID,
    ) -> list[RouteStep]:
        """Get all active steps for an order's route, sorted by sequence."""
        route = await RoutingEngineService.get_route_for_order(session, order_id)
        steps = sorted(route.steps, key=lambda s: s.sequence)
        return [s for s in steps if s.is_active]
