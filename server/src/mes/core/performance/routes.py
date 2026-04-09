"""
PERF-ANALYSIS: REST API routes for performance analysis.

Endpoints:
- GET    /api/v1/performance/reasons                            List all reasons
- POST   /api/v1/performance/reasons                            Create a reason
- GET    /api/v1/performance/reasons/{reason_id}                Get a reason
- PUT    /api/v1/performance/reasons/{reason_id}                Update a reason
- DELETE /api/v1/performance/reasons/{reason_id}                Delete a reason
- GET    /api/v1/performance/state-models                       List registered state models
- GET    /api/v1/performance/state-models/{model_id}            Get state model by ID
- GET    /api/v1/performance/equipment/{equip_id}/current-state Current state + valid transitions
- POST   /api/v1/performance/equipment/{equip_id}/transition    Trigger a state transition
- POST   /api/v1/performance/equipment/{equip_id}/manual-transition  Manual transition with reason
- POST   /api/v1/performance/equipment/{equip_id}/simulate-opcua-state  Simulate OPC-UA state change
- POST   /api/v1/performance/equipment/{equip_id}/simulate-mqtt-state   Simulate MQTT state message
- POST   /api/v1/performance/equipment/{equip_id}/simulate-mqtt-counts  Simulate MQTT production counts
- GET    /api/v1/performance/oee                                Calculate OEE for equipment + time range
- GET    /api/v1/performance/equipment-states                   Query equipment state history
- POST   /api/v1/performance/equipment-states                   Record equipment state change
- GET    /api/v1/performance/counters                           Query production counters
- POST   /api/v1/performance/counters                           Record/update production counter
- POST   /api/v1/performance/counters/increment                 Atomically increment counters (delta-based)
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
    CounterIncrementRequest,
    EquipmentCurrentStateRead,
    EquipmentStateLogRead,
    EquipmentStateModelRead,
    EquipmentTransitionRequest,
    ManualTransitionRequest,
    OEEResult,
    SimulateMqttCountRequest,
    SimulateMqttStateRequest,
    SimulateOpcuaStateRequest,
    ProductionCounterRead,
    ReasonCreate,
    ReasonRead,
    ReasonUpdate,
    StateChangeRequest,
)
from .service import EquipmentStateService, OEEService, ProductionCounterService, ReasonService

router = APIRouter(prefix="/api/v1/performance", tags=["Performance Analysis"])


# ═══════════════════════════════════════════════════════════════════
# Reason Codes (hierarchical loss reasons)
# ═══════════════════════════════════════════════════════════════════


@router.get("/reasons")
async def list_reasons(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """List all active reason codes (flat list; client assembles tree)."""
    reasons = await ReasonService.list_reasons(session)
    return success_response(
        [ReasonRead.model_validate(r).model_dump() for r in reasons],
    )


@router.post("/reasons", status_code=201)
async def create_reason(
    body: ReasonCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """Create a new reason code."""
    reason = await ReasonService.create_reason(session, **body.model_dump())
    await session.commit()
    return success_response(ReasonRead.model_validate(reason).model_dump())


@router.get("/reasons/{reason_id}")
async def get_reason(
    reason_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """Get a single reason code by ID."""
    reason = await ReasonService.get_reason(session, reason_id)
    return success_response(ReasonRead.model_validate(reason).model_dump())


@router.put("/reasons/{reason_id}")
async def update_reason(
    reason_id: UUID,
    body: ReasonUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """Update an existing reason code."""
    reason = await ReasonService.update_reason(
        session, reason_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(ReasonRead.model_validate(reason).model_dump())


@router.delete("/reasons/{reason_id}", status_code=204)
async def delete_reason(
    reason_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """Soft-delete a reason code."""
    await ReasonService.delete_reason(session, reason_id)
    await session.commit()


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


@router.post("/equipment/{equip_id}/simulate-opcua-state", status_code=201)
async def simulate_opcua_state(
    equip_id: UUID,
    body: SimulateOpcuaStateRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """
    Simulate an OPC-UA data-change event on a PackML CurrentState tag.

    Accepts an integer value (OPC 40083 enum) or a state name string.
    Maps the value to a PackML state name and triggers a transition
    through the EquipmentStateEngine — the same path as a real
    OPC-UA subscription callback.
    """
    # OPC 40083 \u00a76 integer-to-state mapping
    packml_int_to_state: dict[int, str] = {
        0: "Undefined", 1: "Clearing", 2: "Stopped", 3: "Starting",
        4: "Idle", 5: "Suspended", 6: "Execute", 7: "Stopping",
        8: "Aborting", 9: "Aborted", 10: "Holding", 11: "Held",
        12: "Unholding", 13: "Suspending", 14: "Unsuspending",
        15: "Resetting", 16: "Completing", 17: "Complete",
    }

    if body.value is not None:
        state_name = packml_int_to_state.get(body.value)
        if state_name is None:
            from mes.framework.api.exceptions import ValidationException

            raise ValidationException(
                f"Unknown PackML integer state: {body.value}. "
                f"Valid values: {sorted(packml_int_to_state.keys())}",
            )
    elif body.state:
        state_name = body.state
    else:
        from mes.framework.api.exceptions import ValidationException

        raise ValidationException("Either 'value' (integer) or 'state' (string) is required.")

    log = await EquipmentStateEngine.transition_equipment(
        session,
        equipment_id=equip_id,
        new_state=state_name,
        notes=f"Simulated OPC-UA tag {body.tag} value={body.value if body.value is not None else state_name}",
    )
    await session.commit()
    return success_response(EquipmentStateLogRead.model_validate(log).model_dump())


@router.post("/equipment/{equip_id}/simulate-mqtt-state", status_code=201)
async def simulate_mqtt_state(
    equip_id: UUID,
    body: SimulateMqttStateRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """
    Simulate an MQTT message carrying a PackML state and optional reason code.

    Mimics a JSON payload arriving on an MQTT topic like
    ``mes/equipment/{equipment_id}/state`` with body
    ``{"state": <int>, "reason_code": "<string>"}``.

    The integer is mapped via the OPC 40083 enum and the transition is
    processed through ``EquipmentStateEngine.transition_equipment()``.
    """
    packml_int_to_state: dict[int, str] = {
        0: "Undefined", 1: "Clearing", 2: "Stopped", 3: "Starting",
        4: "Idle", 5: "Suspended", 6: "Execute", 7: "Stopping",
        8: "Aborting", 9: "Aborted", 10: "Holding", 11: "Held",
        12: "Unholding", 13: "Suspending", 14: "Unsuspending",
        15: "Resetting", 16: "Completing", 17: "Complete",
    }

    state_name = packml_int_to_state.get(body.state)
    if state_name is None:
        from mes.framework.api.exceptions import ValidationException

        raise ValidationException(
            f"Unknown PackML integer state: {body.state}. "
            f"Valid values: {sorted(packml_int_to_state.keys())}",
        )

    topic = body.topic.replace("{equipment_id}", str(equip_id))
    log = await EquipmentStateEngine.transition_equipment(
        session,
        equipment_id=equip_id,
        new_state=state_name,
        reason_code=body.reason_code,
        notes=f"Simulated MQTT topic={topic} payload={{\"state\": {body.state}, \"reason_code\": {body.reason_code!r}}}",
    )
    await session.commit()
    return success_response(EquipmentStateLogRead.model_validate(log).model_dump())


@router.post("/equipment/{equip_id}/simulate-mqtt-counts", status_code=201)
async def simulate_mqtt_counts(
    equip_id: UUID,
    body: SimulateMqttCountRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """
    Simulate an MQTT message carrying PackML production counts.

    Mimics a JSON payload arriving on an MQTT topic like
    ``mes/equipment/{equipment_id}/counts`` with body
    ``{"processed_count": <int>, "defective_count": <int>, "rework_count": <int>}``.

    Maps to the PackML PackTag nodes ``Admin.ProdProcessedCount`` (good)
    and ``Admin.ProdDefectiveCount`` (rejected).  Counts are atomically
    incremented on today's shift counter.
    """
    if body.processed_count == 0 and body.defective_count == 0 and body.rework_count == 0:
        from mes.framework.api.exceptions import ValidationException

        raise ValidationException(
            "At least one count (processed_count, defective_count, rework_count) must be > 0.",
        )

    topic = body.topic.replace("{equipment_id}", str(equip_id))
    counter = await ProductionCounterService.increment_counter(
        session,
        equipment_id=equip_id,
        good_delta=body.processed_count,
        reject_delta=body.defective_count,
        rework_delta=body.rework_count,
        source_plugin="mqtt-counter-simulator",
    )
    await session.commit()

    import logging
    logging.getLogger(__name__).info(
        "Simulated MQTT count message: topic=%s equip=%s processed=+%d defective=+%d rework=+%d",
        topic, equip_id, body.processed_count, body.defective_count, body.rework_count,
    )

    return success_response(ProductionCounterRead.model_validate(counter).model_dump())


@router.post("/equipment/{equip_id}/manual-transition", status_code=201)
async def manual_transition_equipment(
    equip_id: UUID,
    body: ManualTransitionRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """
    Manually transition equipment using a reason code.

    The reason's OEE bucket determines the availability classification.
    A state-change record is created with a synthetic state name derived
    from the reason code and the canonical OEE bucket mapping.
    """
    from datetime import timezone as tz

    reason = await ReasonService.get_reason(session, body.reason_id)

    # Map the oee_bucket to a dispatch category
    oee_to_dispatch = {
        "downtime_planned": "unavailable_planned",
        "downtime_unplanned": "unavailable_unplanned",
        "uptime_non_value": "available",
        "uptime_value_add": "busy",
        "excluded": "unavailable_planned",
    }
    dispatch_category = oee_to_dispatch.get(reason.oee_bucket, "available")

    log = await EquipmentStateService.record_state_change(
        session,
        equipment_id=equip_id,
        state_model="manual",
        state=reason.name,
        sub_state=None,
        dispatch_category=dispatch_category,
        oee_bucket=reason.oee_bucket,
        started_at=datetime.now(tz.utc),
        reason_code=reason.code,
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


@router.post("/counters/increment", status_code=201)
async def increment_counter(
    body: CounterIncrementRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    """
    Atomically increment production counters for today's shift (delta-based).

    Used by data collection plugins (OPC-UA PackTags, MQTT, manual entry)
    to report good, rejected, and rework counts as they occur.
    """
    counter = await ProductionCounterService.increment_counter(
        session,
        equipment_id=body.equipment_id,
        good_delta=body.good_delta,
        reject_delta=body.reject_delta,
        rework_delta=body.rework_delta,
        order_id=body.order_id,
        source_plugin=body.source,
    )
    await session.commit()
    return success_response(ProductionCounterRead.model_validate(counter).model_dump())
