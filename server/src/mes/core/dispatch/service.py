"""
DISPATCH: Business logic service for the dispatching engine.

Implements dispatch evaluation with pluggable strategies and
dispatch execution.

Dispatch invariants (enforced in core, not plugins):
1. Equipment must have dispatch_category == 'available' (or no state model)
2. Equipment must be set up for the material (EquipmentMaterial row exists)
   — skipped if unit/lot has no material_id or equipment has no material setups
3. Equipment input queue must not be at max_queue_depth
   — skipped if max_queue_depth is null (unlimited)

When no eligible equipment is found, the lot/unit is BLOCKED.
When an available equipment's input queue is empty, the equipment is STARVED.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.events import event_bus

from mes.core.physical_model.models import Equipment, EquipmentMaterial, WorkCell
from mes.core.product_def.models import ProcessSegment, SegmentEquipmentRequirement
from mes.core.wip.models import Unit, Lot
from mes.core.performance.models import EquipmentStateLog

from .events import (
    dispatch_evaluated,
    dispatch_executed,
    dispatch_blocked,
    equipment_starved,
)
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
    EquipmentDispatchStatus,
    StepEquipmentStatus,
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
        1. Resolve the WIP's CURRENT step (the routing engine has already
           advanced the unit/lot to the step that needs equipment)
        2. Find eligible equipment at that step
        3. Filter: availability (dispatch_category == 'available')
        4. Filter: capability (EquipmentMaterial for the lot's material)
        5. Filter: capacity (queue_depth < max_queue_depth)
        6. Apply strategy to rank options
        7. Return ranked options with recommendation (or blocked=True)

        NOTE: Dispatch never advances steps — that is the routing engine's
        sole responsibility. Dispatch only assigns equipment.
        """
        # ── Resolve unit or lot ─────────────────────────────────────
        material_id: UUID | None = None
        if unit_id is not None:
            result = await session.execute(
                select(Unit).where(Unit.id == unit_id)
            )
            wip = result.scalar_one_or_none()
            if wip is None:
                raise NotFoundException(resource="Unit", resource_id=str(unit_id))
            current_step_id = wip.current_step_id
            identifier = wip.serial_number
            material_id = wip.material_id
        elif lot_id is not None:
            result = await session.execute(
                select(Lot).where(Lot.id == lot_id)
            )
            wip = result.scalar_one_or_none()
            if wip is None:
                raise NotFoundException(resource="Lot", resource_id=str(lot_id))
            current_step_id = wip.current_step_id
            identifier = wip.lot_number
            material_id = wip.material_id
        else:
            raise NotFoundException(resource="Unit/Lot", resource_id="none")

        if current_step_id is None:
            raise NoRouteForDispatchException(identifier)

        # ── Use the WIP's CURRENT step as the dispatch target ───────
        # The routing engine has already moved the unit/lot to the step
        # that needs equipment. Dispatch's job is solely to pick equipment.
        target_step_result = await session.execute(
            select(ProcessSegment).where(ProcessSegment.id == current_step_id)
        )
        target_step = target_step_result.scalar_one_or_none()
        if target_step is None:
            raise NoRouteForDispatchException(identifier)

        # ── Find eligible equipment at the target step ──────────────
        # ISA-95 Process Segment dispatch priority:
        #   1. SegmentEquipmentRequirement rows (specific equipment for this step)
        #   2. equipment_class_id on the step (all equipment of that class)
        #   3. No constraint → empty options

        equip_rows: list[tuple] = []

        # 1. Check step-level equipment requirements
        equip_req_result = await session.execute(
            select(SegmentEquipmentRequirement).where(
                SegmentEquipmentRequirement.step_id == target_step.id,
                SegmentEquipmentRequirement.is_active.is_(True),
            )
        )
        equip_reqs = equip_req_result.scalars().all()

        if equip_reqs:
            # Use specific equipment from requirements
            req_equip_ids = [r.equipment_id for r in equip_reqs]
            equip_stmt = (
                select(Equipment, WorkCell)
                .join(WorkCell, Equipment.work_cell_id == WorkCell.id)
                .where(
                    Equipment.id.in_(req_equip_ids),
                    Equipment.is_active.is_(True),
                )
            )
            equip_result = await session.execute(equip_stmt)
            equip_rows = equip_result.all()

        elif target_step.equipment_class_id is not None:
            # 2. Find all equipment belonging to the required class
            equip_stmt = (
                select(Equipment, WorkCell)
                .join(WorkCell, Equipment.work_cell_id == WorkCell.id)
                .where(
                    Equipment.equipment_class_id == target_step.equipment_class_id,
                    Equipment.is_active.is_(True),
                )
            )
            equip_result = await session.execute(equip_stmt)
            equip_rows = equip_result.all()

        else:
            # 3. No equipment constraint — cannot dispatch
            return DispatchEvaluateResponse(
                unit_id=unit_id,
                lot_id=lot_id,
                strategy=strategy,
                options=[],
            )

        # ── Filter by availability, capability, capacity ────────────
        options: list[DispatchOption] = []
        blocked_reasons: list[str] = []

        for equip, wc in equip_rows:
            # 1. AVAILABILITY: check dispatch_category
            dispatch_cat = await _get_dispatch_category(session, equip.id)
            if dispatch_cat != "available":
                blocked_reasons.append(
                    f"{equip.code}: unavailable ({dispatch_cat})"
                )
                continue

            # 2. CAPABILITY: check EquipmentMaterial for the lot's material
            if material_id is not None:
                has_setup = await _has_material_setup(
                    session, equip.id, material_id,
                )
                if not has_setup:
                    blocked_reasons.append(
                        f"{equip.code}: not set up for material"
                    )
                    continue

            # 3. CAPACITY: check queue depth vs max_queue_depth
            queue_depth = await _get_queue_depth(session, equip.id)

            if equip.max_queue_depth is not None and queue_depth >= equip.max_queue_depth:
                blocked_reasons.append(
                    f"{equip.code}: queue full ({queue_depth}/{equip.max_queue_depth})"
                )
                continue

            options.append(DispatchOption(
                equipment_id=equip.id,
                equipment_code=equip.code,
                equipment_name=equip.name,
                work_cell_id=wc.id,
                work_cell_code=wc.code,
                step_id=target_step.id,
                step_name=target_step.name,
                queue_depth=queue_depth,
                max_queue_depth=equip.max_queue_depth,
            ))

        if not options:
            # BLOCKED — no eligible equipment
            reason = "; ".join(blocked_reasons) if blocked_reasons else "no equipment at step"
            await event_bus.publish(dispatch_blocked(
                unit_id=str(unit_id) if unit_id else None,
                lot_id=str(lot_id) if lot_id else None,
                reason=reason,
            ))
            logger.warning(
                "Dispatch blocked: %s %s — %s",
                "unit" if unit_id else "lot",
                unit_id or lot_id,
                reason,
            )
            return DispatchEvaluateResponse(
                unit_id=unit_id,
                lot_id=lot_id,
                strategy=strategy,
                options=[],
                blocked=True,
                blocked_reason=reason,
            )

        # ── Apply strategy ──────────────────────────────────────────
        ranked = _apply_strategy(options, strategy)

        recommended = ranked[0] if ranked else None

        await event_bus.publish(dispatch_evaluated(
            unit_id=str(unit_id) if unit_id else None,
            lot_id=str(lot_id) if lot_id else None,
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
        Execute a dispatch decision: assign equipment to the unit/lot.

        Validates:
        - Equipment exists and is active
        - Equipment is in 'available' dispatch category
        - Equipment has capacity (queue not full)
        - Equipment can process the material (if material_id set)
        - destination_step_id matches the WIP's current step (defensive —
          dispatch must NEVER move WIP between steps; that is the routing
          engine's responsibility)

        Then updates unit/lot current_equipment_id only. The current_step_id
        is left untouched — only WIPService.move_unit/move_lot may change it.
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

        # ── Validate availability ───────────────────────────────────
        dispatch_cat = await _get_dispatch_category(session, equip.id)
        if dispatch_cat != "available":
            raise InvalidDispatchTargetException(
                equip.code,
                f"dispatch_category is '{dispatch_cat}', must be 'available'",
            )

        # ── Validate capacity ───────────────────────────────────────
        if equip.max_queue_depth is not None:
            queue_depth = await _get_queue_depth(session, equip.id)
            if queue_depth >= equip.max_queue_depth:
                raise InvalidDispatchTargetException(
                    equip.code,
                    f"queue full ({queue_depth}/{equip.max_queue_depth})",
                )

        # ── Validate material capability ────────────────────────────
        material_id: UUID | None = None

        # ── Update the unit or lot ──────────────────────────────────
        now = datetime.now(timezone.utc)

        if unit_id is not None:
            result = await session.execute(
                select(Unit).where(Unit.id == unit_id)
            )
            unit = result.scalar_one_or_none()
            if unit is None:
                raise NotFoundException(resource="Unit", resource_id=str(unit_id))
            if (
                destination_step_id is not None
                and unit.current_step_id is not None
                and destination_step_id != unit.current_step_id
            ):
                raise InvalidDispatchTargetException(
                    equip.code,
                    f"step mismatch: unit is at step {unit.current_step_id}, "
                    f"dispatch target was step {destination_step_id}; "
                    f"dispatch may not advance steps",
                )
            material_id = unit.material_id
            unit.current_equipment_id = destination_equipment_id

        if lot_id is not None:
            result = await session.execute(
                select(Lot).where(Lot.id == lot_id)
            )
            lot_obj = result.scalar_one_or_none()
            if lot_obj is None:
                raise NotFoundException(resource="Lot", resource_id=str(lot_id))
            if (
                destination_step_id is not None
                and lot_obj.current_step_id is not None
                and destination_step_id != lot_obj.current_step_id
            ):
                raise InvalidDispatchTargetException(
                    equip.code,
                    f"step mismatch: lot is at step {lot_obj.current_step_id}, "
                    f"dispatch target was step {destination_step_id}; "
                    f"dispatch may not advance steps",
                )
            material_id = lot_obj.material_id
            lot_obj.current_equipment_id = destination_equipment_id

        # Validate material setup (after resolving WIP to get material_id)
        if material_id is not None:
            has_setup = await _has_material_setup(session, equip.id, material_id)
            if not has_setup:
                raise InvalidDispatchTargetException(
                    equip.code,
                    f"not set up for material {material_id}",
                )

        await session.flush()

        # Emit event
        await event_bus.publish(dispatch_executed(
            unit_id=str(unit_id) if unit_id else None,
            lot_id=str(lot_id) if lot_id else None,
            destination_step_id=str(destination_step_id),
            destination_equipment_id=str(destination_equipment_id),
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

    @staticmethod
    async def get_equipment_status(
        session: AsyncSession,
        equipment_id: UUID,
    ) -> EquipmentDispatchStatus:
        """
        Get the dispatch-level status of a single equipment.

        Returns availability state, queue depth, and starved/at-capacity flags.
        """
        equip_result = await session.execute(
            select(Equipment).where(Equipment.id == equipment_id)
        )
        equip = equip_result.scalar_one_or_none()
        if equip is None:
            raise NotFoundException(resource="Equipment", resource_id=str(equipment_id))

        dispatch_cat = await _get_dispatch_category(session, equip.id)
        queue_depth = await _get_queue_depth(session, equip.id)

        is_starved = dispatch_cat == "available" and queue_depth == 0
        is_at_capacity = (
            equip.max_queue_depth is not None and queue_depth >= equip.max_queue_depth
        )

        if is_starved:
            await event_bus.publish(equipment_starved(str(equip.id)))

        return EquipmentDispatchStatus(
            equipment_id=equip.id,
            equipment_code=equip.code,
            equipment_name=equip.name,
            dispatch_category=dispatch_cat,
            queue_depth=queue_depth,
            max_queue_depth=equip.max_queue_depth,
            is_starved=is_starved,
            is_at_capacity=is_at_capacity,
        )

    @staticmethod
    async def auto_dispatch(
        session: AsyncSession,
        unit_id: UUID | None = None,
        lot_id: UUID | None = None,
    ) -> DispatchEvaluateResponse | DispatchExecuteResponse:
        """
        Evaluate and automatically execute dispatch for a unit or lot.

        Uses 'shortest_queue' strategy. If a destination is found, executes the
        dispatch. If blocked (no eligible equipment), returns the blocked
        evaluation response without error.

        This is the handler for lot/unit completion triggers (OPC-UA, MQTT, manual).
        """
        eval_result = await DispatchService.evaluate(
            session,
            unit_id=unit_id,
            lot_id=lot_id,
            strategy="shortest_queue",
        )

        if eval_result.blocked or eval_result.recommended is None:
            return eval_result

        recommended = eval_result.recommended
        exec_result = await DispatchService.execute(
            session,
            unit_id=unit_id,
            lot_id=lot_id,
            destination_equipment_id=recommended.equipment_id,
            destination_step_id=recommended.step_id,
        )

        return exec_result

    @staticmethod
    async def get_step_equipment(
        session: AsyncSession,
        step_id: UUID,
        material_id: UUID | None = None,
        assigned_equipment_id: UUID | None = None,
    ) -> list[StepEquipmentStatus]:
        """
        Return status of all equipment at a step's work cell.

        Includes dispatch_category, PackML state, queue depth, material setup,
        and whether the WIP is currently assigned to that equipment.
        """
        # Resolve step → equipment candidates
        # Priority: step equipment requirements > equipment_class_id
        step_result = await session.execute(
            select(ProcessSegment).where(ProcessSegment.id == step_id)
        )
        step_obj = step_result.scalar_one_or_none()
        if step_obj is None:
            return []

        # 1. Check step-level equipment requirements
        equip_req_result = await session.execute(
            select(SegmentEquipmentRequirement).where(
                SegmentEquipmentRequirement.step_id == step_id,
                SegmentEquipmentRequirement.is_active.is_(True),
            )
        )
        equip_reqs = equip_req_result.scalars().all()

        if equip_reqs:
            req_equip_ids = [r.equipment_id for r in equip_reqs]
            equip_result = await session.execute(
                select(Equipment).where(
                    Equipment.id.in_(req_equip_ids),
                    Equipment.is_active.is_(True),
                ).order_by(Equipment.code)
            )
        elif step_obj.equipment_class_id is not None:
            equip_result = await session.execute(
                select(Equipment).where(
                    Equipment.equipment_class_id == step_obj.equipment_class_id,
                    Equipment.is_active.is_(True),
                ).order_by(Equipment.code)
            )
        else:
            return []

        equipment_list = equip_result.scalars().all()

        statuses: list[StepEquipmentStatus] = []
        for equip in equipment_list:
            dispatch_cat = await _get_dispatch_category(session, equip.id)
            queue_depth = await _get_queue_depth(session, equip.id)

            # Current state log for PackML / SEMI-E10 state
            state_log_result = await session.execute(
                select(EquipmentStateLog)
                .where(
                    EquipmentStateLog.equipment_id == equip.id,
                    EquipmentStateLog.ended_at.is_(None),
                )
                .order_by(EquipmentStateLog.started_at.desc())
                .limit(1)
            )
            state_log = state_log_result.scalar_one_or_none()

            # Material setup check
            has_material = True
            if material_id is not None:
                has_material = await _has_material_setup(
                    session, equip.id, material_id,
                )

            has_spare = (
                equip.max_queue_depth is None
                or queue_depth < equip.max_queue_depth
            )

            statuses.append(StepEquipmentStatus(
                equipment_id=equip.id,
                equipment_code=equip.code,
                equipment_name=equip.name,
                dispatch_category=dispatch_cat,
                state_model=(
                    state_log.state_model if state_log else equip.state_model_id
                ),
                state=state_log.state if state_log else None,
                queue_depth=queue_depth,
                max_queue_depth=equip.max_queue_depth,
                has_spare_capacity=has_spare,
                material_setup=has_material,
                is_assigned=(
                    assigned_equipment_id is not None
                    and equip.id == assigned_equipment_id
                ),
            ))

        return statuses


# ── Helper functions ─────────────────────────────────────────────────

async def _get_dispatch_category(session: AsyncSession, equipment_id: UUID) -> str:
    """Get the current dispatch_category for an equipment from its latest state log."""
    state_stmt = (
        select(EquipmentStateLog.dispatch_category)
        .where(
            EquipmentStateLog.equipment_id == equipment_id,
            EquipmentStateLog.ended_at.is_(None),
        )
        .order_by(EquipmentStateLog.started_at.desc())
        .limit(1)
    )
    state_result = await session.execute(state_stmt)
    row = state_result.scalar_one_or_none()
    # No state log → no state model → assume available
    return row if row is not None else "available"


async def _get_queue_depth(session: AsyncSession, equipment_id: UUID) -> int:
    """Count the number of WIP items (units + lots) queued or in-process at an equipment."""
    unit_count_result = await session.execute(
        select(func.count()).select_from(Unit).where(
            Unit.current_equipment_id == equipment_id,
            Unit.status.in_(("queued", "in_process")),
        )
    )
    lot_count_result = await session.execute(
        select(func.count()).select_from(Lot).where(
            Lot.current_equipment_id == equipment_id,
            Lot.status.in_(("queued", "in_process")),
        )
    )
    return unit_count_result.scalar_one() + lot_count_result.scalar_one()


async def _has_material_setup(
    session: AsyncSession, equipment_id: UUID, material_id: UUID,
) -> bool:
    """
    Check if an equipment has been set up to process a specific material.

    Returns True if:
    - Equipment has no material setups at all (universally capable)
    - Equipment has an EquipmentMaterial row for this material

    Returns False if equipment has material setups but not for this material.
    """
    # Check if equipment has ANY material setups
    any_setup_stmt = select(
        exists().where(EquipmentMaterial.equipment_id == equipment_id)
    )
    any_result = await session.execute(any_setup_stmt)
    has_any = any_result.scalar_one()

    if not has_any:
        # No material setups → universally capable
        return True

    # Check if specific material is configured
    specific_stmt = select(
        exists().where(
            EquipmentMaterial.equipment_id == equipment_id,
            EquipmentMaterial.material_id == material_id,
        )
    )
    specific_result = await session.execute(specific_stmt)
    return specific_result.scalar_one()


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
