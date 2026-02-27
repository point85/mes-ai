"""
DISPATCH: REST API routes for the dispatching engine.

Endpoints:
- POST /api/v1/dispatch/evaluate              Evaluate dispatch for a unit/lot
- POST /api/v1/dispatch/execute               Execute a dispatch decision
- GET  /api/v1/dispatch/strategies             List available dispatch strategies
- GET  /api/v1/dispatch/queue/{work_cell_id} Get dispatch queue for a work cell
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import list_response, success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .schemas import (
    DispatchEvaluateRequest,
    DispatchExecuteRequest,
    DispatchQueueItem,
    DispatchStrategyInfo,
)
from .service import DispatchService

router = APIRouter(prefix="/api/v1/dispatch", tags=["Dispatching"])


@router.post("/evaluate")
async def evaluate_dispatch(
    body: DispatchEvaluateRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("dispatch.read")),
):
    """Evaluate dispatch options for a unit or lot using the specified strategy."""
    result = await DispatchService.evaluate(
        session,
        unit_id=body.unit_id,
        lot_id=body.lot_id,
        strategy=body.strategy,
    )
    return success_response(result.model_dump())


@router.post("/execute")
async def execute_dispatch(
    body: DispatchExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("dispatch.execute")),
):
    """Execute a dispatch decision — move a unit/lot to the destination."""
    result = await DispatchService.execute(
        session,
        unit_id=body.unit_id,
        lot_id=body.lot_id,
        destination_equipment_id=body.destination_equipment_id,
        destination_step_id=body.destination_step_id,
    )
    await session.commit()
    return success_response(result.model_dump())


@router.get("/strategies")
async def list_strategies(
    _user: User = Depends(require_permission("dispatch.read")),
):
    """List all available dispatch strategies."""
    strategies = DispatchService.list_strategies()
    return success_response(
        [s.model_dump() for s in strategies],
    )


@router.get("/queue/{work_cell_id}")
async def get_queue(
    work_cell_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("dispatch.read")),
):
    """Get the dispatch queue for a work cell."""
    queue = await DispatchService.get_queue(session, work_cell_id)
    return success_response(
        [item.model_dump() for item in queue],
    )
