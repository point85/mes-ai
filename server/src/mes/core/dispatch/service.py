"""
DISPATCH: Business logic service for the dispatching engine.

Implements dispatch evaluation with pluggable strategies and
dispatch execution.

Dispatch invariant: WIP is NEVER dispatched to equipment where
dispatch_category != 'available'. This is enforced in core, not in plugins.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.events import event_bus

from mes.core.physical_model.models import Equipment, WorkCell
from mes.core.product_def.models import RouteStep
from mes.core.wip.models import Unit, Lot
from mes.core.performance.models import EquipmentStateLog

from .events import dispatch_evaluated, dispatch_executed
from .exceptions import (
    InvalidDispatchTargetException,
    NoEligibleEquipmentException,
    NoRouteForDispatchException,
)
from .schemas import (
    DispatchOption,
    DispatchEvaluateResponse,
    DispatchExecuteResponse,
    DispatchQueueItem,
    DispatchStrategyInfo,
    DISPATCH_STRATEGIES,
)

logger = logging.getLogger("mes.dispatch")

# ── Built-in strategy descriptions ──────────────────────────────────

STRATEGY_DESCRIPTIONS: dict[str, str] = {
    "manual": "Operator manually selects destination from valid options",
    "first_available": "Route to the first available equipment at the next step",
    "shortest_queue": "Route to equipment with the shortest queue of WIP",
    "round_robin": "Distribute evenly across available equipment",
    "capability_match": "Route based on equipment capability and product requirements",
}


class DispatchService:
    """Dispatching engine: evaluates destinations and executes dispatch decisions."""

    @staticmethod
    def list_strategies() -> list[DispatchStrategyInfo]:
        """List all available dispatch strategies."""
        return [
            DispatchStrategyInfo(
                name=name,
                description=desc,
                strategy_type="built-in",
            )
            for name, desc in STRATEGY_DESCRIPTIONS.items()
        ]

    @staticmethod
    async def evaluate(
        session: AsyncSession,
        unit_id: UUID | None = None,
        lot_id: UUID | None = None,
        strategy: str = "first_available",
    ) -> DispatchEvaluateResponse:
        """
        Evaluate dispatch options for a unit or lot.

        Flow:
        1. Resolve the current step and route
        2. Find eligible equipment at the next step(s)
        3. Filter: only equipment with dispatch_category == 'available'
        4. Apply strategy to rank options
        5. Return ranked options with recommendation
        """
        # ── Resolve unit or lot ─────────────────────────────────────
        if unit_id is not None:
            result = await session.execute(
                select(Unit).where(Unit.id == unit_id)
            )
            wip = result.scalar_one_or_none()
            if wip is None:
                raise NotFoundException(resource="Unit", resource_id=str(unit_id))
            current_step_id = wip.current_step_id
            identifier = wip.serial_number
        elif lot_id is not None:
            result = await session.execute(
                select(Lot).where(Lot.id == lot_id)
            )
            wip = result.scalar_one_or_none()
            if wip is None:
                raise NotFoundException(resource="Lot", resource_id=str(lot_id))
            current_step_id = wip.current_step_id
            identifier = wip.lot_number
        else:
            raise NotFoundException(resource="Unit/Lot", resource_id="none")

        if current_step_id is None:
            raise NoRouteForDispatchException(identifier)

        # ── Get current step and find next step(s) ──────────────────
        curr_step_result = await session.execute(
            select(RouteStep).where(RouteStep.id == current_step_id)
        )
        curr_step = curr_step_result.scalar_one_or_none()
        if curr_step is None:
            raise NoRouteForDispatchException(identifier)

        # Find next steps in sequence order
        next_steps_result = await session.execute(
            select(RouteStep)
            .where(
                RouteStep.route_id == curr_step.route_id,
                RouteStep.sequence > curr_step.sequence,
                RouteStep.is_active.is_(True),
            )
            .order_by(RouteStep.sequence)
        )
        next_steps = next_steps_result.scalars().all()

        if not next_steps:
            # End of route — no dispatch needed
            return DispatchEvaluateResponse(
                unit_id=unit_id,
                lot_id=lot_id,
                strategy=strategy,
                options=[],
                recommended=None,
            )

        # For now, consider only the immediate next step
        target_step = next_steps[0]

        # ── Find eligible equipment at the target step ──────────────
        # Equipment at the work cell linked to the step
        if target_step.work_cell_id is None:
            return DispatchEvaluateResponse(
                unit_id=unit_id,
                lot_id=lot_id,
                strategy=strategy,
                options=[],
            )

        equip_stmt = (
            select(Equipment, WorkCell)
            .join(WorkCell, Equipment.work_cell_id == WorkCell.id)
            .where(
                Equipment.work_cell_id == target_step.work_cell_id,
                Equipment.is_active.is_(True),
            )
        )
        equip_result = await session.execute(equip_stmt)
        equip_rows = equip_result.all()

        # ── Filter by dispatch_category == 'available' ──────────────
        # Check the latest state log for each equipment
        options: list[DispatchOption] = []
        for equip, wc in equip_rows:
            # Get current dispatch category from state log
            state_stmt = (
                select(EquipmentStateLog)
                .where(
                    EquipmentStateLog.equipment_id == equip.id,
                    EquipmentStateLog.ended_at.is_(None),
                )
                .order_by(EquipmentStateLog.started_at.desc())
                .limit(1)
            )
            state_result = await session.execute(state_stmt)
            current_state = state_result.scalar_one_or_none()

            # If no state log exists, assume available (no state model = 100% availability)
            dispatch_cat = None
            if current_state is not None:
                dispatch_cat = current_state.dispatch_category
            else:
                dispatch_cat = "available"

            if dispatch_cat != "available":
                continue

            # Count items currently queued at this equipment
            unit_count_result = await session.execute(
                select(func.count()).select_from(Unit).where(
                    Unit.current_equipment_id == equip.id,
                    Unit.status.in_(("queued", "in_process")),
                )
            )
            lot_count_result = await session.execute(
                select(func.count()).select_from(Lot).where(
                    Lot.current_equipment_id == equip.id,
                    Lot.status.in_(("queued", "in_process")),
                )
            )
            queue_depth = (
                unit_count_result.scalar_one()
                + lot_count_result.scalar_one()
            )

            options.append(DispatchOption(
                equipment_id=equip.id,
                equipment_code=equip.code,
                equipment_name=equip.name,
                work_cell_id=wc.id,
                work_cell_code=wc.code,
                step_id=target_step.id,
                step_name=target_step.name,
                queue_depth=queue_depth,
            ))

        if not options:
            # Emit event for monitoring
            await event_bus.publish(dispatch_evaluated(
                unit_id=str(unit_id) if unit_id else None,
                strategy=strategy,
                recommendation=None,
            ))
            return DispatchEvaluateResponse(
                unit_id=unit_id,
                lot_id=lot_id,
                strategy=strategy,
                options=[],
            )

        # ── Apply strategy ──────────────────────────────────────────
        ranked = _apply_strategy(options, strategy)

        recommended = ranked[0] if ranked else None

        await event_bus.publish(dispatch_evaluated(
            unit_id=str(unit_id) if unit_id else None,
            strategy=strategy,
            recommendation=str(recommended.equipment_id) if recommended else None,
        ))

        return DispatchEvaluateResponse(
            unit_id=unit_id,
            lot_id=lot_id,
            strategy=strategy,
            options=ranked,
            recommended=recommended,
        )

    @staticmethod
    async def execute(
        session: AsyncSession,
        unit_id: UUID | None = None,
        lot_id: UUID | None = None,
        destination_equipment_id: UUID = None,  # type: ignore[assignment]
        destination_step_id: UUID = None,  # type: ignore[assignment]
    ) -> DispatchExecuteResponse:
        """
        Execute a dispatch decision: move the unit/lot to the destination.

        Validates that the destination equipment is available, then updates
        the unit/lot's current_step_id and current_equipment_id.
        """
        # ── Validate equipment exists ───────────────────────────────
        equip_result = await session.execute(
            select(Equipment).where(Equipment.id == destination_equipment_id)
        )
        equip = equip_result.scalar_one_or_none()
        if equip is None:
            raise NotFoundException(
                resource="Equipment", resource_id=str(destination_equipment_id),
            )

        # ── Update the unit or lot ──────────────────────────────────
        now = datetime.now(timezone.utc)

        if unit_id is not None:
            result = await session.execute(
                select(Unit).where(Unit.id == unit_id)
            )
            unit = result.scalar_one_or_none()
            if unit is None:
                raise NotFoundException(resource="Unit", resource_id=str(unit_id))
            unit.current_step_id = destination_step_id
            unit.current_equipment_id = destination_equipment_id

        if lot_id is not None:
            result = await session.execute(
                select(Lot).where(Lot.id == lot_id)
            )
            lot_obj = result.scalar_one_or_none()
            if lot_obj is None:
                raise NotFoundException(resource="Lot", resource_id=str(lot_id))
            lot_obj.current_step_id = destination_step_id
            lot_obj.current_equipment_id = destination_equipment_id

        await session.flush()

        # Emit event
        await event_bus.publish(dispatch_executed(
            unit_id=str(unit_id) if unit_id else None,
            destination_step_id=str(destination_step_id),
        ))

        logger.info(
            "Dispatch executed: unit=%s lot=%s → equip=%s step=%s",
            unit_id, lot_id, destination_equipment_id, destination_step_id,
        )

        return DispatchExecuteResponse(
            unit_id=unit_id,
            lot_id=lot_id,
            destination_equipment_id=destination_equipment_id,
            destination_step_id=destination_step_id,
            dispatched_at=now,
        )

    @staticmethod
    async def get_queue(
        session: AsyncSession,
        work_cell_id: UUID,
    ) -> list[DispatchQueueItem]:
        """Get the dispatch queue for a work cell (all WIP at its equipment)."""
        # Get all equipment in the work cell
        equip_result = await session.execute(
            select(Equipment.id).where(
                Equipment.work_cell_id == work_cell_id,
            )
        )
        equip_ids = [eid for (eid,) in equip_result.all()]

        if not equip_ids:
            return []

        # Get units at these equipment
        units_result = await session.execute(
            select(Unit).where(
                Unit.current_equipment_id.in_(equip_ids),
                Unit.status.in_(("queued", "in_process")),
            ).order_by(Unit.created_at)
        )
        units = units_result.scalars().all()

        # Get lots at these equipment
        lots_result = await session.execute(
            select(Lot).where(
                Lot.current_equipment_id.in_(equip_ids),
                Lot.status.in_(("queued", "in_process")),
            ).order_by(Lot.created_at)
        )
        lots = lots_result.scalars().all()

        queue: list[DispatchQueueItem] = []
        for u in units:
            queue.append(DispatchQueueItem(
                unit_id=u.id,
                serial_number=u.serial_number,
                order_id=u.order_id,
                current_step_id=u.current_step_id,
                status=u.status,
                equipment_id=u.current_equipment_id,
            ))
        for l in lots:
            queue.append(DispatchQueueItem(
                lot_id=l.id,
                lot_number=l.lot_number,
                order_id=l.order_id,
                current_step_id=l.current_step_id,
                status=l.status,
                equipment_id=l.current_equipment_id,
            ))

        return queue


# ── Strategy implementations ─────────────────────────────────────────

def _apply_strategy(
    options: list[DispatchOption], strategy: str,
) -> list[DispatchOption]:
    """Rank dispatch options using the specified strategy."""

    if strategy == "first_available":
        # Return in natural order (first found)
        for i, opt in enumerate(options):
            opt.score = float(len(options) - i)
            opt.reason = "first available"
        return options

    elif strategy == "shortest_queue":
        ranked = sorted(options, key=lambda o: o.queue_depth)
        for i, opt in enumerate(ranked):
            opt.score = float(len(ranked) - i)
            opt.reason = f"queue depth: {opt.queue_depth}"
        return ranked

    elif strategy == "round_robin":
        # Sort by queue depth (acts as a proxy for least-recently-used)
        ranked = sorted(options, key=lambda o: o.queue_depth)
        for i, opt in enumerate(ranked):
            opt.score = float(len(ranked) - i)
            opt.reason = "round robin"
        return ranked

    elif strategy == "capability_match":
        # For now, all eligible equipment is considered capable
        # Future: match equipment capabilities JSON against step requirements
        for i, opt in enumerate(options):
            opt.score = float(len(options) - i)
            opt.reason = "capability match (default)"
        return options

    elif strategy == "manual":
        # Return all options for operator selection — no ranking
        for opt in options:
            opt.score = 0.0
            opt.reason = "manual selection"
        return options

    else:
        return options
