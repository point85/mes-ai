"""
QUAL-MGMT: Business logic service for quality management.
"""

from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.events import event_bus

from .events import quality_test_passed, quality_test_failed
from .models import NonConformance, QualityTest, TestResult


class QualityTestService:
    """Service for managing quality test definitions."""

    @staticmethod
    async def list_tests(session: AsyncSession) -> Sequence[QualityTest]:
        stmt = select(QualityTest).where(QualityTest.is_active.is_(True)).order_by(QualityTest.code)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_test(session: AsyncSession, test_id: UUID) -> QualityTest:
        stmt = select(QualityTest).where(
            QualityTest.id == test_id,
            QualityTest.is_active.is_(True),
        )
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(resource="QualityTest", resource_id=str(test_id))
        return obj

    @staticmethod
    async def create_test(session: AsyncSession, **kwargs: Any) -> QualityTest:
        obj = QualityTest(**kwargs)
        session.add(obj)
        await session.flush()
        return obj

    @staticmethod
    async def update_test(
        session: AsyncSession, test_id: UUID, **kwargs: Any,
    ) -> QualityTest:
        obj = await QualityTestService.get_test(session, test_id)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await session.flush()
        return obj


class TestResultService:
    """Service for recording and querying test results."""

    @staticmethod
    async def record_result(session: AsyncSession, **kwargs: Any) -> TestResult:
        obj = TestResult(**kwargs)
        session.add(obj)
        await session.flush()
        result_val = kwargs.get("result", "")
        test_id = str(kwargs.get("test_id", ""))
        unit_id = str(kwargs.get("unit_id") or kwargs.get("lot_id", ""))
        if result_val == "pass":
            await event_bus.publish(quality_test_passed(test_id, unit_id, str(obj.id)))
        else:
            await event_bus.publish(quality_test_failed(test_id, unit_id, str(obj.id)))
        return obj

    @staticmethod
    async def get_result(session: AsyncSession, result_id: UUID) -> TestResult:
        stmt = select(TestResult).where(
            TestResult.id == result_id,
            TestResult.is_active.is_(True),
        )
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(resource="TestResult", resource_id=str(result_id))
        return obj

    @staticmethod
    async def list_results(session: AsyncSession) -> Sequence[TestResult]:
        stmt = (
            select(TestResult)
            .where(TestResult.is_active.is_(True))
            .order_by(TestResult.tested_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


class NonConformanceService:
    """Service for managing non-conformance reports."""

    @staticmethod
    async def create_nc(session: AsyncSession, **kwargs: Any) -> NonConformance:
        obj = NonConformance(**kwargs)
        session.add(obj)
        await session.flush()
        return obj

    @staticmethod
    async def get_nc(session: AsyncSession, nc_id: UUID) -> NonConformance:
        stmt = select(NonConformance).where(
            NonConformance.id == nc_id,
            NonConformance.is_active.is_(True),
        )
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(resource="NonConformance", resource_id=str(nc_id))
        return obj

    @staticmethod
    async def list_ncs(session: AsyncSession) -> Sequence[NonConformance]:
        stmt = (
            select(NonConformance)
            .where(NonConformance.is_active.is_(True))
            .order_by(NonConformance.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_nc(
        session: AsyncSession, nc_id: UUID, **kwargs: Any,
    ) -> NonConformance:
        obj = await NonConformanceService.get_nc(session, nc_id)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await session.flush()
        return obj
