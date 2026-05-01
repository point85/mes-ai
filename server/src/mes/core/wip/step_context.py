"""
WIP-TRACK: Composite step-context builder for the RT-CLIENT.

Given a unit or lot ID, returns a single dict containing everything the
operator work screen needs:
  - wip: unit/lot details (id, serial/lot number, status, order_id, …)
  - step: current step details (id, name, step_type, sequence, …) or null
  - segment_parameters: spec limits for the step
  - data_definitions: data collection requirements for the step
  - quality_tests: quality tests linked to the step
  - dispositions: available MRB/disposition transitions (empty if not MRB)
  - process_segments: all steps in the route (for progress tracker)
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.core.data_collection.models import DataDefinition
from mes.core.data_collection.schemas import DataDefinitionRead
from mes.core.product_def.models import (
    ProcessSegment,
    ProcessSegmentInputDisposition,
    ProcessSegmentOutputDisposition,
    SegmentParameter,
)
from mes.core.product_def.schemas import DispositionRead, StepParameterRead
from mes.core.quality.models import QualityTest
from mes.core.quality.schemas import QualityTestRead
from mes.core.routing.service import RoutingEngineService
from mes.core.wip.schemas import UnitRead, LotRead
from mes.core.wip.service import UnitService, LotService


async def build_step_context(
    session: AsyncSession,
    *,
    unit_id: UUID | None = None,
    lot_id: UUID | None = None,
) -> dict:
    """Build the composite step-context payload."""

    # 1. Load WIP item
    if unit_id is not None:
        wip_obj = await UnitService.get_unit(session, unit_id)
        wip_data = UnitRead.model_validate(wip_obj).model_dump()
        wip_type = "unit"
        order_id = wip_obj.order_id
        current_step_id = wip_obj.current_step_id
    elif lot_id is not None:
        wip_obj = await LotService.get_lot(session, lot_id)
        wip_data = LotRead.model_validate(wip_obj).model_dump()
        wip_type = "lot"
        order_id = wip_obj.order_id
        current_step_id = wip_obj.current_step_id
    else:
        raise ValueError("unit_id or lot_id required")

    # 2. Load current step details
    step_data = None
    step_params = []
    data_defs = []
    quality_tests = []
    dispositions = []

    if current_step_id is not None:
        # Step details (with input/output disposition lists eagerly loaded)
        step_result = await session.execute(
            select(ProcessSegment)
            .where(ProcessSegment.id == current_step_id)
            .options(
                selectinload(ProcessSegment.input_dispositions).selectinload(
                    ProcessSegmentInputDisposition.disposition,
                ),
                selectinload(ProcessSegment.output_dispositions).selectinload(
                    ProcessSegmentOutputDisposition.disposition,
                ),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is not None:
            step_data = _step_to_dict(step)

        # Step parameters (spec limits)
        param_result = await session.execute(
            select(SegmentParameter).where(
                SegmentParameter.step_id == current_step_id,
                SegmentParameter.is_active.is_(True),
            )
        )
        step_params = [
            StepParameterRead.model_validate(p).model_dump()
            for p in param_result.scalars().all()
        ]

        # Data definitions for this step
        dd_result = await session.execute(
            select(DataDefinition).where(
                DataDefinition.step_id == current_step_id,
                DataDefinition.is_active.is_(True),
            )
        )
        data_defs = [
            DataDefinitionRead.model_validate(d).model_dump()
            for d in dd_result.scalars().all()
        ]

        # Quality tests for this step
        qt_result = await session.execute(
            select(QualityTest).where(
                QualityTest.step_id == current_step_id,
                QualityTest.is_active.is_(True),
            )
        )
        quality_tests = [
            QualityTestRead.model_validate(t).model_dump()
            for t in qt_result.scalars().all()
        ]

        # Dispositions (output disposition choices for this step)
        dispositions = await RoutingEngineService.get_available_dispositions(
            session, current_step_id,
        )

    # 3. Load all route steps for progress tracker
    process_segments = []
    try:
        all_steps = await RoutingEngineService.get_process_segments(session, order_id)
        # Eager-load disposition lists for each step in one round-trip.
        if all_steps:
            ids = [s.id for s in all_steps]
            full_rows = (await session.execute(
                select(ProcessSegment)
                .where(ProcessSegment.id.in_(ids))
                .options(
                    selectinload(ProcessSegment.input_dispositions).selectinload(
                        ProcessSegmentInputDisposition.disposition,
                    ),
                    selectinload(ProcessSegment.output_dispositions).selectinload(
                        ProcessSegmentOutputDisposition.disposition,
                    ),
                )
            )).scalars().all()
            full_by_id = {s.id: s for s in full_rows}
            ordered = sorted(
                (full_by_id[s.id] for s in all_steps if s.id in full_by_id),
                key=lambda s: s.sequence,
            )
            process_segments = [_step_to_dict(s) for s in ordered]
    except Exception:
        pass  # No route → empty

    return {
        "wip_type": wip_type,
        "wip": wip_data,
        "step": step_data,
        "step_parameters": step_params,
        "data_definitions": data_defs,
        "quality_tests": quality_tests,
        "dispositions": dispositions,
        "route_steps": process_segments,
    }


def _step_to_dict(step: ProcessSegment) -> dict:
    """Build a RouteStepRead-shaped dict from a ProcessSegment with its
    input/output disposition junction rows eagerly loaded."""
    return {
        "id": step.id,
        "route_id": step.route_id,
        "sequence": step.sequence,
        "name": step.name,
        "step_type": step.step_type,
        "equipment_class_id": step.equipment_class_id,
        "expected_cycle_time_sec": step.expected_cycle_time_sec,
        "erp_operation_number": step.erp_operation_number,
        "is_initial_step": step.is_initial_step,
        "input_dispositions": [
            DispositionRead.model_validate(r.disposition).model_dump()
            for r in step.input_dispositions
            if r.is_active
        ],
        "output_dispositions": [
            DispositionRead.model_validate(r.disposition).model_dump()
            for r in step.output_dispositions
            if r.is_active
        ],
        "is_active": step.is_active,
        "created_at": step.created_at,
        "updated_at": step.updated_at,
    }
