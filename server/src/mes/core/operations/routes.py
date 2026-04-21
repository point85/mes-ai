"""
PROD-ORDER: REST API routes for production orders.

Endpoints:
- GET    /api/v1/orders                    List orders (optional filters)
- POST   /api/v1/orders                    Create an order
- GET    /api/v1/orders/{order_id}         Get an order by ID
- PATCH  /api/v1/orders/{order_id}         Update an order
- DELETE /api/v1/orders/{order_id}         Soft-delete an order
- POST   /api/v1/orders/{order_id}/release   Release order for production
- POST   /api/v1/orders/{order_id}/complete  Mark order as completed
- POST   /api/v1/orders/{order_id}/close     Close order
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.pagination import PaginationParams, get_pagination_params
from mes.framework.api.responses import list_response, success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .schemas import (
    OrderCreate,
    OrderRead,
    OrderUpdate,
    OrderReleaseRequest,
    OrderCompleteRequest,
)
from .service import OperationsRequestService

router = APIRouter(prefix="/api/v1", tags=["Production Orders"])
svc = OperationsRequestService


# ─── List / query ────────────────────────────────────────────────────


@router.get("/orders")
async def list_orders(
    status: str | None = Query(None, description="Filter by status"),
    product_id: UUID | None = Query(None, description="Filter by product ID"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("production.read")),
):
    """List active production orders with optional filters."""
    items, cursor, has_more = await svc.list_orders(
        session, params, status=status, product_id=product_id,
    )
    return list_response(
        [OrderRead.model_validate(o).model_dump() for o in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.get("/orders/{order_id}")
async def get_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("production.read")),
):
    """Get a production order by ID."""
    order = await svc.get_order(session, order_id)
    return success_response(OrderRead.model_validate(order).model_dump())


# ─── Mutations ───────────────────────────────────────────────────────


@router.post("/orders", status_code=201)
async def create_order(
    body: OrderCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("production.create")),
):
    """Create a new production order."""
    order = await svc.create_order(session, **body.model_dump())
    await session.commit()
    return success_response(OrderRead.model_validate(order).model_dump())


@router.patch("/orders/{order_id}")
async def update_order(
    order_id: UUID,
    body: OrderUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("production.update")),
):
    """Update a production order."""
    order = await svc.update_order(session, order_id, **body.model_dump(exclude_unset=True))
    await session.commit()
    return success_response(OrderRead.model_validate(order).model_dump())


@router.delete("/orders/{order_id}", status_code=204)
async def delete_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("production.delete")),
):
    """Soft-delete a production order."""
    await svc.delete_order(session, order_id)
    await session.commit()


# ─── Lifecycle actions ───────────────────────────────────────────────


@router.post("/orders/{order_id}/release")
async def release_order(
    order_id: UUID,
    body: OrderReleaseRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("production.update")),
):
    """Release a production order for production."""
    order = await svc.release_order(session, order_id)
    await session.commit()
    return success_response(OrderRead.model_validate(order).model_dump())


@router.post("/orders/{order_id}/complete")
async def complete_order(
    order_id: UUID,
    body: OrderCompleteRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("production.update")),
):
    """Mark a production order as completed."""
    order = await svc.complete_order(session, order_id)
    await session.commit()
    return success_response(OrderRead.model_validate(order).model_dump())


@router.post("/orders/{order_id}/close")
async def close_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("production.update")),
):
    """Close a production order (final state)."""
    order = await svc.close_order(session, order_id)
    await session.commit()
    return success_response(OrderRead.model_validate(order).model_dump())
