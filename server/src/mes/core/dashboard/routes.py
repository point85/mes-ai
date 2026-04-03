"""
DASHBOARD: REST API routes for pre-aggregated dashboard views.

Endpoints:
- GET /api/v1/dashboard/order-progress   Active order rollup with WIP counts
- GET /api/v1/dashboard/line-status      Production line & equipment status
- GET /api/v1/dashboard/shift-summary    Production totals for a time window
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import success_response
from mes.framework.db import get_db_session

from .service import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/order-progress")
async def order_progress(
    status: str | None = Query(None, description="Filter by order status"),
    session: AsyncSession = Depends(get_db_session),
):
    """Rollup of active production orders with completion % and WIP bucket counts."""
    data = await DashboardService.order_progress(session, status_filter=status)
    return success_response(data)


@router.get("/line-status")
async def line_status(
    line_id: UUID | None = Query(None, description="Filter to a single production line"),
    session: AsyncSession = Depends(get_db_session),
):
    """Equipment state and queue depth per production line."""
    data = await DashboardService.line_status(session, line_id=line_id)
    return success_response(data)


@router.get("/shift-summary")
async def shift_summary(
    hours: int = Query(8, ge=1, le=24, description="Look-back window in hours"),
    equipment_id: UUID | None = Query(None, description="Scope to a single equipment"),
    session: AsyncSession = Depends(get_db_session),
):
    """Aggregated production counts for the past N hours."""
    data = await DashboardService.shift_summary(
        session, hours=hours, equipment_id=equipment_id,
    )
    return success_response(data)
