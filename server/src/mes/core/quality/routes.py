"""
QUAL-MGMT: REST API routes for quality management.

Endpoints:
- GET    /api/v1/quality/tests                       List quality tests
- POST   /api/v1/quality/tests                       Create a quality test
- GET    /api/v1/quality/tests/{test_id}             Get a quality test
- PUT    /api/v1/quality/tests/{test_id}             Update a quality test
- GET    /api/v1/quality/results                     List test results
- POST   /api/v1/quality/results                     Record a test result
- GET    /api/v1/quality/results/{result_id}         Get a test result
- GET    /api/v1/quality/non-conformances            List non-conformances
- POST   /api/v1/quality/non-conformances            Create a non-conformance
- PUT    /api/v1/quality/non-conformances/{nc_id}    Update/resolve non-conformance
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
    NonConformanceCreate,
    NonConformanceRead,
    NonConformanceUpdate,
    QualityTestCreate,
    QualityTestRead,
    QualityTestUpdate,
    RecordResultRequest,
    TestResultRead,
)
from .service import NonConformanceService, QualityTestService, TestResultService

router = APIRouter(prefix="/api/v1/quality", tags=["Quality Management"])


# ═══════════════════════════════════════════════════════════════════
# QualityTest endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/tests")
async def list_tests(
    test_type: str | None = Query(None, description="Filter by type: inline, offline, destructive"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.read")),
):
    """List active quality test definitions."""
    items, cursor, has_more = await QualityTestService.list_tests(
        session, params, test_type=test_type,
    )
    return list_response(
        [QualityTestRead.model_validate(t).model_dump() for t in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.get("/tests/{test_id}")
async def get_test(
    test_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.read")),
):
    """Get a quality test by ID."""
    test = await QualityTestService.get_test(session, test_id)
    return success_response(QualityTestRead.model_validate(test).model_dump())


@router.post("/tests", status_code=201)
async def create_test(
    body: QualityTestCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.create")),
):
    """Create a new quality test definition."""
    test = await QualityTestService.create_test(session, **body.model_dump())
    await session.commit()
    return success_response(QualityTestRead.model_validate(test).model_dump())


@router.put("/tests/{test_id}")
async def update_test(
    test_id: UUID,
    body: QualityTestUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.update")),
):
    """Update a quality test definition."""
    test = await QualityTestService.update_test(session, test_id, **body.model_dump())
    await session.commit()
    return success_response(QualityTestRead.model_validate(test).model_dump())


# ═══════════════════════════════════════════════════════════════════
# TestResult endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/results")
async def list_results(
    test_id: UUID | None = Query(None),
    unit_id: UUID | None = Query(None),
    lot_id: UUID | None = Query(None),
    result: str | None = Query(None, description="Filter by: pass, fail"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.read")),
):
    """List test results with optional filters."""
    items, cursor, has_more = await TestResultService.list_results(
        session, params,
        test_id=test_id,
        unit_id=unit_id,
        lot_id=lot_id,
        result_filter=result,
    )
    return list_response(
        [TestResultRead.model_validate(r).model_dump() for r in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/results", status_code=201)
async def record_result(
    body: RecordResultRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.create")),
):
    """Record a quality test result."""
    result_obj = await TestResultService.record_result(session, **body.model_dump())
    await session.commit()
    return success_response(TestResultRead.model_validate(result_obj).model_dump())


@router.get("/results/{result_id}")
async def get_result(
    result_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.read")),
):
    """Get a test result by ID."""
    result_obj = await TestResultService.get_result(session, result_id)
    return success_response(TestResultRead.model_validate(result_obj).model_dump())


# ═══════════════════════════════════════════════════════════════════
# NonConformance endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/non-conformances")
async def list_non_conformances(
    status: str | None = Query(None, description="Filter by status"),
    nc_type: str | None = Query(None, description="Filter by type"),
    unit_id: UUID | None = Query(None),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.read")),
):
    """List non-conformance records."""
    items, cursor, has_more = await NonConformanceService.list_ncs(
        session, params, status=status, nc_type=nc_type, unit_id=unit_id,
    )
    return list_response(
        [NonConformanceRead.model_validate(nc).model_dump() for nc in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.post("/non-conformances", status_code=201)
async def create_non_conformance(
    body: NonConformanceCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.create")),
):
    """Create a non-conformance record."""
    nc = await NonConformanceService.create_nc(session, **body.model_dump())
    await session.commit()
    return success_response(NonConformanceRead.model_validate(nc).model_dump())


@router.put("/non-conformances/{nc_id}")
async def update_non_conformance(
    nc_id: UUID,
    body: NonConformanceUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("quality.update")),
):
    """Update / resolve a non-conformance."""
    nc = await NonConformanceService.update_nc(session, nc_id, **body.model_dump())
    await session.commit()
    return success_response(NonConformanceRead.model_validate(nc).model_dump())
