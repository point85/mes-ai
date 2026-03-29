"""
PERF-ANALYSIS: REST API routes for performance analysis.

Endpoints:
- GET  /api/v1/performance/state-models                        List registered state models
- GET  /api/v1/performance/state-models/{model_id}             Get state model by ID
- GET  /api/v1/performance/equipment/{equip_id}/current-state  Current state + valid transitions
- POST /api/v1/performance/equipment/{equip_id}/transition     Trigger a state transition
- GET  /api/v1/performance/oee                                 Calculate OEE for equipment + time range
- GET  /api/v1/performance/equipment-states                    Query equipment state history
- POST /api/v1/performance/equipment-states                    Record equipment state change
- GET  /api/v1/performance/counters                            Query production counters
- POST /api/v1/performance/counters                            Record/update production counter
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.pagination import PaginationParams, get_pagination_params
from mes.framework.api.responses import list_response, success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .engine import (
    DEFAULT_DISPATCH_CATEGORY,
    DEFAULT_OEE_BUCKET,
    DEFAULT_STATE,
    EquipmentStateEngine,
)
from .schemas import (
    CounterCreateUpdate,
    EquipmentCurrentStateRead,
    EquipmentStateLogRead,
    EquipmentStateModelRead,
    EquipmentTransitionRequest,
    OEEResult,
    ProductionCounterRead,
    StateChangeRequest,
)
from .service import EquipmentStateService, OEEService, ProductionCounterService

router = APIRouter(prefix="/api/v1/performance", tags=["Performance Analysis"])


# ═══════════════════════════════════════════════════════════════════
# State Model Definitions
# ═══════════════════════════════════════════════════════════════════


@router.get("/state-models")
async def list_state_models(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """List all registered equipment state models (e.g. PackML, SEMI E10)."""
    models = await EquipmentStateEngine.list_state_models(session)
    return success_response(
        [EquipmentStateModelRead.model_validate(m).model_dump() for m in models],
    )


@router.get("/state-models/{model_id}")
async def get_state_model(
    model_id: str,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """Get a specific state model definition by its plugin ID."""
    model = await EquipmentStateEngine.get_state_model(session, model_id)
    return success_response(
        EquipmentStateModelRead.model_validate(model).model_dump(),
    )


# ═══════════════════════════════════════════════════════════════════
# Equipment State Transitions
# ═══════════════════════════════════════════════════════════════════


@router.get("/equipment/{equip_id}/current-state")
async def get_equipment_current_state(
    equip_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """Get the current state for equipment, including valid next transitions."""
    from mes.core.physical_model.models import Equipment
    from sqlalchemy import select as sa_select

    eq_stmt = sa_select(Equipment).where(
        Equipment.id == equip_id, Equipment.is_active.is_(True),
    )
    result = await session.execute(eq_stmt)
    equipment = result.scalar_one_or_none()
    if equipment is None:
        from mes.framework.api.exceptions import NotFoundException
        raise NotFoundException(resource="Equipment", resource_id=str(equip_id))

    model_id = equipment.state_model_id
    current_log = await EquipmentStateService.get_current_state(session, equip_id)

    if model_id is None:
        # No state model → 100 % available default
        return success_response(
            EquipmentCurrentStateRead(
                equipment_id=equip_id,
                state_model="default",
                state=current_log.state if current_log else DEFAULT_STATE,
                dispatch_category=current_log.dispatch_category if current_log else DEFAULT_DISPATCH_CATEGORY,
                oee_bucket=current_log.oee_bucket if current_log else DEFAULT_OEE_BUCKET,
                started_at=current_log.started_at if current_log else None,
                valid_transitions=[],
            ).model_dump(),
        )

    model = await EquipmentStateEngine.get_state_model(session, model_id)
    current_state = current_log.state if current_log else model.initial_state
    valid = EquipmentStateEngine.get_valid_next_states(model.transitions, current_state)

    state_def = EquipmentStateEngine._find_state_def(model.states, current_state)

    return success_response(
        EquipmentCurrentStateRead(
            equipment_id=equip_id,
            state_model=model_id,
            state=current_state,
            dispatch_category=state_def["dispatch_category"] if state_def else DEFAULT_DISPATCH_CATEGORY,
            oee_bucket=state_def["oee_bucket"] if state_def else DEFAULT_OEE_BUCKET,
            started_at=current_log.started_at if current_log else None,
            valid_transitions=valid,
        ).model_dump(),
    )


@router.post("/equipment/{equip_id}/transition", status_code=201)
async def transition_equipment(
    equip_id: UUID,
    body: EquipmentTransitionRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """Trigger a state transition for equipment."""
    log = await EquipmentStateEngine.transition_equipment(
        session,
        equipment_id=equip_id,
        new_state=body.new_state,
        reason_code=body.reason_code,
        notes=body.notes,
    )
    await session.commit()
    return success_response(EquipmentStateLogRead.model_validate(log).model_dump())


# ═══════════════════════════════════════════════════════════════════
# OEE Calculation
# ═══════════════════════════════════════════════════════════════════


@router.get("/oee")
async def calculate_oee(
    equipment_id: UUID = Query(..., description="Equipment ID"),
    period_start: datetime = Query(..., description="Period start (ISO 8601)"),
    period_end: datetime = Query(..., description="Period end (ISO 8601)"),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """Calculate OEE (Overall Equipment Effectiveness) for an equipment over a time range."""
    result = await OEEService.calculate_oee(
        session, equipment_id, period_start, period_end,
    )
    return success_response(result)


# ═══════════════════════════════════════════════════════════════════
# Equipment State Log
# ═══════════════════════════════════════════════════════════════════


@router.get("/equipment-states")
async def list_equipment_states(
    equipment_id: UUID | None = Query(None),
    started_after: datetime | None = Query(None),
    started_before: datetime | None = Query(None),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """Query equipment state history."""
    items, cursor, has_more = await EquipmentStateService.list_state_logs(
        session, params,
        equipment_id=equipment_id,
        started_after=started_after,
        started_before=started_before,
    )
    return list_response(
        [EquipmentStateLogRead.model_validate(s).model_dump() for s in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/equipment-states", status_code=201)
async def record_state_change(
    body: StateChangeRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """Record an equipment state change."""
    log = await EquipmentStateService.record_state_change(session, **body.model_dump())
    await session.commit()
    return success_response(EquipmentStateLogRead.model_validate(log).model_dump())


# ═══════════════════════════════════════════════════════════════════
# Production Counters
# ═══════════════════════════════════════════════════════════════════


@router.get("/counters")
async def list_counters(
    equipment_id: UUID | None = Query(None),
    order_id: UUID | None = Query(None),
    shift_date: date | None = Query(None),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """Query production counters."""
    items, cursor, has_more = await ProductionCounterService.list_counters(
        session, params,
        equipment_id=equipment_id,
        order_id=order_id,
        shift_date=shift_date,
    )
    return list_response(
        [ProductionCounterRead.model_validate(c).model_dump() for c in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/counters", status_code=201)
async def create_or_update_counter(
    body: CounterCreateUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """Create or update a production counter (upsert by equipment+date+order)."""
    counter = await ProductionCounterService.create_or_update_counter(
        session, **body.model_dump(),
    )
    await session.commit()
    return success_response(ProductionCounterRead.model_validate(counter).model_dump())
