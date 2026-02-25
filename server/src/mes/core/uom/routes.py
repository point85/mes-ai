"""
UOM: REST API routes for units of measure.

Endpoints:
- GET    /api/v1/uom                 List units (optional ?type= filter)
- POST   /api/v1/uom                 Create a unit
- GET    /api/v1/uom/{uom_id}        Get a unit by ID
- PATCH  /api/v1/uom/{uom_id}        Update a unit
- DELETE /api/v1/uom/{uom_id}        Soft-delete a unit
- GET    /api/v1/uom/symbol/{symbol}  Get a unit by symbol
- POST   /api/v1/uom/convert         Convert a value between units
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
    ConversionRequest,
    ConversionResult,
    UoMCreate,
    UoMRead,
    UoMUpdate,
)
from .service import UoMService

router = APIRouter(prefix="/api/v1", tags=["Units of Measure"])
svc = UoMService


# ─── List / query ────────────────────────────────────────────────────


@router.get("/uom")
async def list_uoms(
    uom_type: str | None = Query(None, description="Filter by type, e.g. 'mass'"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("uom.read")),
):
    """List active units of measure with optional type filter."""
    items, cursor, has_more = await svc.list_uoms(session, params, uom_type=uom_type)
    return list_response(
        [UoMRead.model_validate(u).model_dump() for u in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.get("/uom/symbol/{symbol}")
async def get_uom_by_symbol(
    symbol: str,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("uom.read")),
):
    """Get a unit of measure by its symbol."""
    uom = await svc.get_by_symbol(session, symbol)
    return success_response(UoMRead.model_validate(uom).model_dump())


@router.get("/uom/{uom_id}")
async def get_uom(
    uom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("uom.read")),
):
    """Get a unit of measure by ID."""
    uom = await svc.get_uom(session, uom_id)
    return success_response(UoMRead.model_validate(uom).model_dump())


# ─── Mutations ───────────────────────────────────────────────────────


@router.post("/uom", status_code=201)
async def create_uom(
    body: UoMCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("uom.create")),
):
    """Create a new unit of measure."""
    uom = await svc.create_uom(session, **body.model_dump())
    await session.commit()
    return success_response(UoMRead.model_validate(uom).model_dump())


@router.patch("/uom/{uom_id}")
async def update_uom(
    uom_id: UUID,
    body: UoMUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("uom.update")),
):
    """Update a unit of measure."""
    uom = await svc.update_uom(session, uom_id, **body.model_dump(exclude_unset=True))
    await session.commit()
    return success_response(UoMRead.model_validate(uom).model_dump())


@router.delete("/uom/{uom_id}", status_code=204)
async def delete_uom(
    uom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("uom.delete")),
):
    """Soft-delete a unit of measure. Built-in units cannot be deleted."""
    await svc.delete_uom(session, uom_id)
    await session.commit()


# ─── Conversion ──────────────────────────────────────────────────────


@router.post("/uom/convert")
async def convert_uom(
    body: ConversionRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("uom.read")),
):
    """Convert a value from one unit to another (must share the same type)."""
    converted, from_uom, to_uom = await svc.convert_by_symbol(
        session, body.value, body.from_symbol, body.to_symbol,
    )
    result = ConversionResult(
        original_value=body.value,
        from_symbol=from_uom.symbol,
        from_name=from_uom.name,
        converted_value=round(converted, 10),
        to_symbol=to_uom.symbol,
        to_name=to_uom.name,
    )
    return success_response(result.model_dump())
