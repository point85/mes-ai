"""
ROUTE-ENGINE: Routing engine service for determining step progression.

Provides runtime logic for:
- Determining the first step in a route
- Determining the next step for a unit/lot given the current step
- Resolving the assigned route for a production order
- Graph-based routing via ProcessSegmentDependency edges (rework, MRB, conditional)
- Fallback to linear sequence-based routing when no transitions are defined

Route definition models (OperationsDefinition, ProcessSegment, SegmentParameter, ProcessSegmentDependency)
live in the product_def module since they are tightly coupled to ProductDefinition.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.core.product_def.models import (
    Disposition,
    OperationsDefinition,
    OperationsDefinitionProductAssignment,
    ProcessSegment,
    ProcessSegmentDependency,
)
from mes.core.operations.models import OperationsRequest
from mes.framework.api.exceptions import NotFoundException
from mes.core.wip.exceptions import NoRouteAssignedException, NoNextStepException

logger = logging.getLogger("mes.routing")

# Result values that map to transition conditions
_RESULT_TO_CONDITION: dict[str, str] = {
    "pass": "on_pass",
    "fail": "on_fail",
    "rework": "on_rework",
}


class RoutingEngineService:
    """
    Runtime routing engine — resolves step progression for WIP.

    Two routing modes:
    1. **Graph routing** (preferred): When the current step has outgoing
       ProcessSegmentDependency records, the engine evaluates them against the step
       completion result to pick the next step.
    2. **Linear fallback**: When no transitions are defined for a step,
       the engine falls back to the next step by ascending sequence number.

    For MRB / disposition steps, the caller must supply a disposition label
    that matches a ProcessSegmentDependency.label to select the correct path.
    """

    @staticmethod
    async def get_route_for_order(
        session: AsyncSession, order_id: UUID,
    ) -> OperationsDefinition:
        """
        Resolve the process route for a production order.

        Priority:
        1. order.route_id (explicitly assigned route)
        2. Product's default route (is_default=True)
        3. First route found for the product (fallback)
        Raises NoRouteAssignedException if none found.
        """
        # Load the order
        stmt = select(OperationsRequest).where(OperationsRequest.id == order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise NotFoundException(resource="OperationsRequest", resource_id=str(order_id))

        # 1. Explicitly assigned route
        if order.route_id is not None:
            route_stmt = (
                select(OperationsDefinition)
                .where(OperationsDefinition.id == order.route_id, OperationsDefinition.is_active.is_(True))
                .options(selectinload(OperationsDefinition.steps))
            )
            route_result = await session.execute(route_stmt)
            route = route_result.scalar_one_or_none()
            if route is not None:
                return route

        # 2. Product's default active route (via OperationsDefinitionProductAssignment)
        default_stmt = (
            select(OperationsDefinition)
            .join(
                OperationsDefinitionProductAssignment,
                OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
            )
            .where(
                OperationsDefinitionProductAssignment.product_id == order.product_id,
                OperationsDefinitionProductAssignment.is_active.is_(True),
                OperationsDefinition.is_default.is_(True),
                OperationsDefinition.is_active.is_(True),
            )
            .options(selectinload(OperationsDefinition.steps))
        )
        default_result = await session.execute(default_stmt)
        default_route = default_result.scalar_one_or_none()
        if default_route is not None:
            return default_route

        # 3. Fallback: first active route for the product
        fallback_stmt = (
            select(OperationsDefinition)
            .join(
                OperationsDefinitionProductAssignment,
                OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
            )
            .where(
                OperationsDefinitionProductAssignment.product_id == order.product_id,
                OperationsDefinitionProductAssignment.is_active.is_(True),
                OperationsDefinition.is_active.is_(True),
            )
            .options(selectinload(OperationsDefinition.steps))
            .order_by(OperationsDefinition.created_at)
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
    ) -> ProcessSegment:
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
        result: str | None = None,
        disposition: str | None = None,
    ) -> ProcessSegment | None:
        """
        Determine the next step after current_step_id in the order's route.

        Args:
            session:         DB session
            order_id:        The production order ID (for route resolution)
            current_step_id: Current step (None → returns first step)
            result:          Step completion result: 'pass', 'fail', 'rework'
                             Used to evaluate conditional transitions.
            disposition:     Operator-selected disposition name.
                             Looked up in the Disposition table first;
                             falls back to ProcessSegmentDependency-based routing.

        Returns:
            The next ProcessSegment, or None if the route is complete.

        Routing priority:
        1. Disposition-based routing (Disposition table lookup by name + route)
        2. Graph-based routing (ProcessSegmentDependency edges)
        3. Linear sequence fallback
        """
        if current_step_id is None:
            return await RoutingEngineService.get_first_step(session, order_id)

        route = await RoutingEngineService.get_route_for_order(session, order_id)

        # ── 1. Disposition-based routing ──────────────────────────────
        if disposition:
            disp_step = await RoutingEngineService._resolve_disposition(
                session, route.id, disposition,
            )
            if disp_step is not None:
                logger.info(
                    "Disposition routing: step %s → %s (disposition=%r)",
                    current_step_id, disp_step.id, disposition,
                )
                return disp_step

        # ── 2. Graph-based routing (ProcessSegmentDependency) ──────────────────
        trans_stmt = (
            select(ProcessSegmentDependency)
            .where(
                ProcessSegmentDependency.from_step_id == current_step_id,
                ProcessSegmentDependency.is_active.is_(True),
            )
            .order_by(ProcessSegmentDependency.priority.desc())
        )
        trans_result = await session.execute(trans_stmt)
        transitions = list(trans_result.scalars().all())

        if transitions:
            next_step = await RoutingEngineService._resolve_graph_transition(
                session, transitions, result, disposition,
            )
            if next_step is not None:
                logger.info(
                    "Graph routing: step %s → %s (result=%s, disposition=%s)",
                    current_step_id, next_step.id, result, disposition,
                )
                return next_step

        # ── 3. Linear sequence fallback ──────────────────────────────
        return await RoutingEngineService._resolve_linear_next(
            route, current_step_id,
        )

    @staticmethod
    async def _resolve_disposition(
        session: AsyncSession,
        route_id: UUID,
        disposition_name: str,
    ) -> ProcessSegment | None:
        """
        Look up a ProcessSegment by its linked Disposition name within the route.
        Joins ProcessSegment → Disposition and matches on Disposition.name.
        """
        stmt = (
            select(ProcessSegment)
            .join(Disposition, ProcessSegment.disposition_id == Disposition.id)
            .where(
                ProcessSegment.route_id == route_id,
                Disposition.name == disposition_name,
                ProcessSegment.is_active.is_(True),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _resolve_graph_transition(
        session: AsyncSession,
        transitions: list[ProcessSegmentDependency],
        result: str | None,
        disposition: str | None,
    ) -> ProcessSegment | None:
        """
        Evaluate transition edges to find the matching next step.

        Evaluation order (highest priority first):
        1. Disposition match: condition='disposition' AND label matches
        2. Result match: condition matches the result (on_pass/on_fail/on_rework)
        3. Always: condition='always'
        4. Default: is_default=True

        Returns None only if no transition matches (caller falls back to linear).
        """
        result_condition = _RESULT_TO_CONDITION.get(result or "", "")
        disposition_match: ProcessSegmentDependency | None = None
        result_match: ProcessSegmentDependency | None = None
        always_match: ProcessSegmentDependency | None = None
        default: ProcessSegmentDependency | None = None

        for t in transitions:
            # Collect disposition matches (highest priority) — match either
            # on the free-text label OR on the linked catalog Disposition.name.
            disp_match = False
            if disposition and t.condition == "disposition":
                if t.label == disposition:
                    disp_match = True
                elif t.disposition is not None and t.disposition.name == disposition:
                    disp_match = True
            if disp_match:
                if disposition_match is None:
                    disposition_match = t

            # Collect result-based matches
            elif result_condition and t.condition == result_condition:
                if result_match is None:
                    result_match = t

            # Collect always (unconditional) matches
            elif t.condition == "always":
                if always_match is None:
                    always_match = t

            # Track the default fallback
            if t.is_default and default is None:
                default = t

        # Priority: disposition > result > always > default
        chosen = disposition_match or result_match or always_match or default
        if chosen is None:
            return None

        # Load the target step
        step_stmt = select(ProcessSegment).where(
            ProcessSegment.id == chosen.to_step_id,
            ProcessSegment.is_active.is_(True),
        )
        step_result = await session.execute(step_stmt)
        return step_result.scalar_one_or_none()

    @staticmethod
    async def _resolve_linear_next(
        route: OperationsDefinition,
        current_step_id: UUID,
    ) -> ProcessSegment | None:
        """Fall back to next step by ascending sequence number."""
        steps = sorted(route.steps, key=lambda s: s.sequence)
        active_steps = [s for s in steps if s.is_active]

        current_index = None
        for i, step in enumerate(active_steps):
            if step.id == current_step_id:
                current_index = i
                break

        if current_index is None:
            logger.warning(
                "Step %s not found in route %s — returning None (complete)",
                current_step_id, route.id,
            )
            return None

        next_index = current_index + 1
        if next_index < len(active_steps):
            return active_steps[next_index]
        return None

    @staticmethod
    async def get_available_dispositions(
        session: AsyncSession,
        step_id: UUID,
    ) -> list[dict[str, str]]:
        """
        Return the disposition choices available at a step.

        Only transitions actually defined from the current step (via
        ``ProcessSegmentDependency`` rows with ``condition='disposition'``)
        are surfaced. The dropdown therefore matches the route diagram —
        a step whose only outgoing edge is ``always`` will return an empty
        list, while a branching step returns one entry per disposition edge.

        Two flavors are supported per outgoing transition:
          * Catalog-linked: ``disposition_id`` joined to the ``Disposition``
            table; we also resolve the disposition assigned to the target
            step (``to_step.disposition``) when the transition itself does
            not pin one, so the operator sees a meaningful name.
          * Legacy free-text: ``label`` only, returned as ``{label, to_step_id}``.
        """
        # Fetch outgoing disposition transitions with both ends preloaded so
        # we can read target-step disposition without a second round-trip.
        stmt = (
            select(ProcessSegmentDependency)
            .options(
                selectinload(ProcessSegmentDependency.to_step).selectinload(
                    ProcessSegment.disposition
                ),
            )
            .where(
                ProcessSegmentDependency.from_step_id == step_id,
                ProcessSegmentDependency.condition == "disposition",
                ProcessSegmentDependency.is_active.is_(True),
            )
            .order_by(ProcessSegmentDependency.priority.desc())
        )
        result = await session.execute(stmt)
        transitions = result.scalars().all()

        out: list[dict[str, str]] = []
        for t in transitions:
            # Prefer transition-pinned disposition, then target-step disposition.
            disp = t.disposition or (
                t.to_step.disposition if t.to_step is not None else None
            )
            if disp is not None:
                out.append({
                    "id": str(disp.id),
                    "name": disp.name,
                    "description": disp.description or "",
                    "category": disp.category,
                    "to_step_id": str(t.to_step_id),
                })
            else:
                out.append({
                    "label": t.label or "(unlabeled)",
                    "to_step_id": str(t.to_step_id),
                })
        return out

    @staticmethod
    async def get_process_segments(
        session: AsyncSession, order_id: UUID,
    ) -> list[ProcessSegment]:
        """Get all active steps for an order's route, sorted by sequence."""
        route = await RoutingEngineService.get_route_for_order(session, order_id)
        steps = sorted(route.steps, key=lambda s: s.sequence)
        return [s for s in steps if s.is_active]
