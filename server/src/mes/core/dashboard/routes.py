"""
DASHBOARD: REST API routes for pre-aggregated dashboard views.

Endpoints:
- GET /api/v1/dashboard/order-progress   Active order rollup with WIP counts
- GET /api/v1/dashboard/line-status      Production line & equipment status
- GET /api/v1/dashboard/shift-summary    Production totals for a time window
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.api.responses import success_response
from mes.framework.db import get_db_session

from .schemas import (
    AlertRead,
    AlertRuleCreate,
    AlertRuleRead,
    AlertRuleUpdate,
    AlertTestRequest,
    AlertTestResult,
)
from .service import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/order-progress")
async def order_progress(
    status: str | None = Query(None, description="Filter by order status"),
    include_inactive: bool = Query(False, description="Include deactivated orders"),
    created_within_hours: int | None = Query(None, ge=1, le=2160, description="Only orders created in the last N hours"),
    session: AsyncSession = Depends(get_db_session),
):
    """Rollup of active production orders with completion % and WIP bucket counts."""
    data = await DashboardService.order_progress(
        session, status_filter=status, include_inactive=include_inactive,
        created_within_hours=created_within_hours,
    )
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
    hours: int = Query(8, ge=1, le=2160, description="Look-back window in hours"),
    equipment_id: UUID | None = Query(None, description="Scope to a single equipment"),
    order_id: UUID | None = Query(None, description="Scope to a single order"),
    session: AsyncSession = Depends(get_db_session),
):
    """Aggregated production counts for the past N hours."""
    data = await DashboardService.shift_summary(
        session, hours=hours, equipment_id=equipment_id, order_id=order_id,
    )
    return success_response(data)


@router.get("/production-trends")
async def production_trends(
    days: int = Query(30, ge=1, le=90),
    equipment_id: UUID | None = Query(None),
    order_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    """Daily production counts; select equipment to include its daily OEE."""
    data = await DashboardService.production_trends(
        session, days=days, equipment_id=equipment_id, order_id=order_id,
    )
    return success_response(data)


@router.get("/loss-breakdown")
async def loss_breakdown(
    days: int = Query(7, ge=1, le=90),
    equipment_id: UUID | None = Query(None),
    order_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    """Loss drill-down by reason, order, and production date."""
    data = await DashboardService.loss_breakdown(
        session, days=days, equipment_id=equipment_id, order_id=order_id,
    )
    return success_response(data)


@router.get("/alert-rules")
async def list_alert_rules(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    rules = await DashboardService.list_alert_rules(session)
    return success_response([AlertRuleRead.model_validate(rule) for rule in rules])


@router.post("/alert-rules", status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    body: AlertRuleCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.create")),
):
    rule = await DashboardService.create_alert_rule(session, body)
    await session.commit()
    return success_response(AlertRuleRead.model_validate(rule))


@router.patch("/alert-rules/{rule_id}")
async def update_alert_rule(
    rule_id: UUID,
    body: AlertRuleUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.update")),
):
    rule = await DashboardService.update_alert_rule(session, rule_id, body)
    await session.commit()
    return success_response(AlertRuleRead.model_validate(rule))


@router.put("/alert-rules/{rule_id}")
async def replace_alert_rule(
    rule_id: UUID,
    body: AlertRuleCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.update")),
):
    """Edit a rule's name, metric, threshold, window and equipment."""
    rule = await DashboardService.update_alert_rule_definition(session, rule_id, body)
    await session.commit()
    return success_response(AlertRuleRead.model_validate(rule))


@router.post("/alert-rules/{rule_id}/test")
async def test_alert_rule(
    rule_id: UUID,
    body: AlertTestRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """Dry-run a rule against sample data; nothing is stored and no alert is raised."""
    result = await DashboardService.test_alert_rule(session, rule_id, body)
    return success_response(AlertTestResult.model_validate(result))


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.delete")),
):
    await DashboardService.delete_alert_rule(session, rule_id)
    await session.commit()


@router.get("/alerts")
async def get_active_alerts(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("performance.read")),
):
    """Evaluate configured rules and return alerts that are currently active."""
    alerts = await DashboardService.evaluate_alerts(session)
    return success_response([AlertRead.model_validate(alert) for alert in alerts])
