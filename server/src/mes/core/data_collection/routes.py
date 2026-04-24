"""
DATA-COLLECT: REST API routes for data collection.

Endpoints:
- GET    /api/v1/data/definitions                  List data definitions
- POST   /api/v1/data/definitions                  Create a data definition
- GET    /api/v1/data/definitions/{definition_id}   Get a data definition
- PATCH  /api/v1/data/definitions/{definition_id}   Update a data definition
- DELETE /api/v1/data/definitions/{definition_id}   Soft-delete a data definition
- POST   /api/v1/data/collect                       Collect a single data point
- POST   /api/v1/data/collect-batch                 Collect multiple data points
- GET    /api/v1/data/points                        Query data points (with filters)
- GET    /api/v1/data/points/{point_id}             Get a single data point
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
    CollectBatchRequest,
    CollectRequest,
    DataDefinitionCreate,
    DataDefinitionRead,
    DataDefinitionUpdate,
    DataPointRead,
)
from .service import DataDefinitionService, DataPointService

router = APIRouter(prefix="/api/v1/data", tags=["Data Collection"])
defn_svc = DataDefinitionService
point_svc = DataPointService


# ═══════════════════════════════════════════════════════════════════
# DataDefinition endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/definitions")
async def list_definitions(
    step_id: UUID | None = Query(None, description="Filter by route step"),
    data_type: str | None = Query(None, description="Filter by data type"),
    source: str | None = Query(None, description="Filter by source"),
    unassigned: bool = Query(
        False,
        description="If true and step_id is not set, return only definitions with no step assignment",
    ),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.read")),
):
    """List active data definitions with optional filters."""
    items, cursor, has_more = await defn_svc.list_definitions(
        session, params,
        step_id=step_id, data_type=data_type, source=source,
        unassigned=unassigned,
    )
    return list_response(
        [DataDefinitionRead.model_validate(d).model_dump() for d in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.get("/definitions/{definition_id}")
async def get_definition(
    definition_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.read")),
):
    """Get a data definition by ID."""
    defn = await defn_svc.get_definition(session, definition_id)
    return success_response(DataDefinitionRead.model_validate(defn).model_dump())


@router.post("/definitions", status_code=201)
async def create_definition(
    body: DataDefinitionCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.create")),
):
    """Create a new data definition."""
    defn = await defn_svc.create_definition(session, **body.model_dump())
    await session.commit()
    return success_response(DataDefinitionRead.model_validate(defn).model_dump())


@router.patch("/definitions/{definition_id}")
async def update_definition(
    definition_id: UUID,
    body: DataDefinitionUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.update")),
):
    """Update a data definition."""
    defn = await defn_svc.update_definition(
        session, definition_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(DataDefinitionRead.model_validate(defn).model_dump())


@router.delete("/definitions/{definition_id}", status_code=204)
async def delete_definition(
    definition_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.delete")),
):
    """Soft-delete a data definition."""
    await defn_svc.delete_definition(session, definition_id)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════
# DataPoint endpoints
# ═══════════════════════════════════════════════════════════════════


@router.post("/collect", status_code=201)
async def collect_data_point(
    body: CollectRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.collect")),
):
    """Collect a single data point."""
    defn = await defn_svc.get_definition(session, body.definition_id)
    point = await point_svc.collect(
        session,
        defn,
        unit_id=body.unit_id,
        lot_id=body.lot_id,
        value_numeric=body.value_numeric,
        value_string=body.value_string,
        value_boolean=body.value_boolean,
        source_equipment_id=body.source_equipment_id,
        operator_id=body.operator_id,
    )
    await session.commit()
    return success_response(DataPointRead.model_validate(point).model_dump())


@router.post("/collect-batch", status_code=201)
async def collect_batch(
    body: CollectBatchRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.collect")),
):
    """Collect multiple data points in a single call."""
    items = [item.model_dump() for item in body.items]
    points = await point_svc.collect_batch(session, items)
    await session.commit()
    return success_response(
        [DataPointRead.model_validate(p).model_dump() for p in points],
    )


@router.get("/points")
async def list_data_points(
    definition_id: UUID | None = Query(None, description="Filter by definition"),
    unit_id: UUID | None = Query(None, description="Filter by unit"),
    lot_id: UUID | None = Query(None, description="Filter by lot"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.read")),
):
    """Query data points with optional filters."""
    items, cursor, has_more = await point_svc.list_points(
        session, params, definition_id=definition_id, unit_id=unit_id, lot_id=lot_id,
    )
    return list_response(
        [DataPointRead.model_validate(p).model_dump() for p in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.get("/points/{point_id}")
async def get_data_point(
    point_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("data.read")),
):
    """Get a single data point by ID."""
    point = await point_svc.get_point(session, point_id)
    return success_response(DataPointRead.model_validate(point).model_dump())
