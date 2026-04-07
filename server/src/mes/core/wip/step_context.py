"""
WIP-TRACK: Composite step-context builder for the RT-CLIENT.

Given a unit or lot ID, returns a single dict containing everything the
operator work screen needs:
  - wip: unit/lot details (id, serial/lot number, status, order_id, …)
  - step: current step details (id, name, step_type, sequence, …) or null
  - step_parameters: spec limits for the step
  - data_definitions: data collection requirements for the step
  - quality_tests: quality tests linked to the step
  - dispositions: available MRB/disposition transitions (empty if not MRB)
  - route_steps: all steps in the route (for progress tracker)
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.core.data_collection.models import DataDefinition
from mes.core.data_collection.schemas import DataDefinitionRead
from mes.core.product_def.models import RouteStep, StepParameter
from mes.core.product_def.schemas import RouteStepRead, StepParameterRead
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
        # Step details
        step_result = await session.execute(
            select(RouteStep).where(RouteStep.id == current_step_id)
        )
        step = step_result.scalar_one_or_none()
        if step is not None:
            step_data = RouteStepRead.model_validate(step).model_dump()

        # Step parameters (spec limits)
        param_result = await session.execute(
            select(StepParameter).where(
                StepParameter.step_id == current_step_id,
                StepParameter.is_active.is_(True),
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

        # Dispositions (MRB step transitions)
        dispositions = await RoutingEngineService.get_available_dispositions(
            session, current_step_id,
        )

    # 3. Load all route steps for progress tracker
    route_steps = []
    try:
        all_steps = await RoutingEngineService.get_route_steps(session, order_id)
        route_steps = [
            RouteStepRead.model_validate(s).model_dump() for s in all_steps
        ]
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
        "route_steps": route_steps,
    }
