"""
QUAL-MGMT: REST API routes for quality management.

Endpoints:
- GET    /api/v1/quality/tests                      List all quality tests
- POST   /api/v1/quality/tests                      Create a quality test
- GET    /api/v1/quality/tests/{test_id}            Get a quality test
- PUT    /api/v1/quality/tests/{test_id}            Update a quality test
- GET    /api/v1/quality/results                    List all test results
- POST   /api/v1/quality/results                    Record a test result
- GET    /api/v1/quality/results/{result_id}        Get a test result
- GET    /api/v1/quality/non-conformances           List all non-conformances
- POST   /api/v1/quality/non-conformances           Create a non-conformance
- GET    /api/v1/quality/non-conformances/{nc_id}   Get a non-conformance
- PUT    /api/v1/quality/non-conformances/{nc_id}   Update a non-conformance
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import list_response, success_response
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
# Quality Tests
# ═══════════════════════════════════════════════════════════════════


@router.get("/tests")
async def list_tests(session: AsyncSession = Depends(get_db_session)):
    items = await QualityTestService.list_tests(session)
    return list_response([QualityTestRead.model_validate(i) for i in items])


@router.post("/tests")
async def create_test(
    body: QualityTestCreate,
    session: AsyncSession = Depends(get_db_session),
):
    obj = await QualityTestService.create_test(session, **body.model_dump())
    await session.commit()
    return success_response(QualityTestRead.model_validate(obj))


@router.get("/tests/{test_id}")
async def get_test(test_id: UUID, session: AsyncSession = Depends(get_db_session)):
    obj = await QualityTestService.get_test(session, test_id)
    return success_response(QualityTestRead.model_validate(obj))


@router.put("/tests/{test_id}")
async def update_test(
    test_id: UUID,
    body: QualityTestUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await QualityTestService.update_test(session, test_id, **data)
    await session.commit()
    return success_response(QualityTestRead.model_validate(obj))


# ═══════════════════════════════════════════════════════════════════
# Test Results
# ═══════════════════════════════════════════════════════════════════


@router.get("/results")
async def list_results(session: AsyncSession = Depends(get_db_session)):
    items = await TestResultService.list_results(session)
    return list_response([TestResultRead.model_validate(i) for i in items])


@router.post("/results")
async def record_result(
    body: RecordResultRequest,
    session: AsyncSession = Depends(get_db_session),
):
    obj = await TestResultService.record_result(session, **body.model_dump())
    await session.commit()
    return success_response(TestResultRead.model_validate(obj))


@router.get("/results/{result_id}")
async def get_result(result_id: UUID, session: AsyncSession = Depends(get_db_session)):
    obj = await TestResultService.get_result(session, result_id)
    return success_response(TestResultRead.model_validate(obj))


# ═══════════════════════════════════════════════════════════════════
# Non-Conformances
# ═══════════════════════════════════════════════════════════════════


@router.get("/non-conformances")
async def list_ncs(session: AsyncSession = Depends(get_db_session)):
    items = await NonConformanceService.list_ncs(session)
    return list_response([NonConformanceRead.model_validate(i) for i in items])


@router.post("/non-conformances")
async def create_nc(
    body: NonConformanceCreate,
    session: AsyncSession = Depends(get_db_session),
):
    obj = await NonConformanceService.create_nc(session, **body.model_dump())
    await session.commit()
    return success_response(NonConformanceRead.model_validate(obj))


@router.get("/non-conformances/{nc_id}")
async def get_nc(nc_id: UUID, session: AsyncSession = Depends(get_db_session)):
    obj = await NonConformanceService.get_nc(session, nc_id)
    return success_response(NonConformanceRead.model_validate(obj))


@router.put("/non-conformances/{nc_id}")
async def update_nc(
    nc_id: UUID,
    body: NonConformanceUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await NonConformanceService.update_nc(session, nc_id, **data)
    await session.commit()
    return success_response(NonConformanceRead.model_validate(obj))
