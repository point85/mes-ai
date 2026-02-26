"""
PERF-ANALYSIS: REST API routes for performance analysis.

Endpoints:
- GET  /api/v1/performance/oee                Calculate OEE for equipment + time range
- GET  /api/v1/performance/equipment-states    Query equipment state history
- POST /api/v1/performance/equipment-states    Record equipment state change
- GET  /api/v1/performance/counters            Query production counters
- POST /api/v1/performance/counters            Record/update production counter
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

from .schemas import (
    CounterCreateUpdate,
    EquipmentStateLogRead,
    OEEResult,
    ProductionCounterRead,
    StateChangeRequest,
)
from .service import EquipmentStateService, OEEService, ProductionCounterService

router = APIRouter(prefix="/api/v1/performance", tags=["Performance Analysis"])


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
