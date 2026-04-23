"""
QUAL-MGMT: Business logic service for quality management.

Provides CRUD for quality test definitions, test result recording,
and non-conformance lifecycle management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import (
    quality_nc_created,
    quality_nc_resolved,
    quality_test_failed,
    quality_test_passed,
)
from .exceptions import (
    DispositionRequiredException,
    DuplicateTestCodeException,
    InvalidNCTransitionException,
)
from .models import NonConformance, QualityTest, TestResult
from .schemas import NC_TRANSITIONS

logger = logging.getLogger("mes.quality")


class QualityTestService:
    """Service class for quality test definition CRUD."""

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_tests(
        session: AsyncSession,
        params: PaginationParams,
        test_type: str | None = None,
    ) -> tuple[Sequence[QualityTest], str | None, bool]:
        """List active quality test definitions with optional type filter."""
        stmt = select(QualityTest).where(
            QualityTest.is_active.is_(True),
        )
        if test_type is not None:
            stmt = stmt.where(QualityTest.test_type == test_type)
        return await paginate_query(session, stmt, QualityTest, params)

    @staticmethod
    async def get_test(
        session: AsyncSession, test_id: UUID,
    ) -> QualityTest:
        """Get a quality test by ID. Raises NotFoundException if missing."""
        stmt = select(QualityTest).where(
            QualityTest.id == test_id,
            QualityTest.is_active.is_(True),
        )
        result = await session.execute(stmt)
        test = result.scalar_one_or_none()
        if test is None:
            raise NotFoundException(
                resource="QualityTest", resource_id=str(test_id),
            )
        return test

    # ─── Mutations ───────────────────────────────────────────────────

    @staticmethod
    async def create_test(
        session: AsyncSession, **kwargs: Any,
    ) -> QualityTest:
        """Create a new quality test. Raises DuplicateTestCodeException if code exists."""
        existing = await session.execute(
            select(QualityTest).where(
                QualityTest.code == kwargs["code"],
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateTestCodeException(kwargs["code"])

        test = QualityTest(**kwargs)
        session.add(test)
        await session.flush()
        return test

    @staticmethod
    async def update_test(
        session: AsyncSession, test_id: UUID, **kwargs: Any,
    ) -> QualityTest:
        """Update a quality test. Validates code uniqueness if changed."""
        test = await QualityTestService.get_test(session, test_id)
        updates = {k: v for k, v in kwargs.items() if v is not None}

        if "code" in updates and updates["code"] != test.code:
            existing = await session.execute(
                select(QualityTest).where(
                    QualityTest.code == updates["code"],
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateTestCodeException(updates["code"])

        for key, value in updates.items():
            setattr(test, key, value)
        await session.flush()
        return test

    @staticmethod
    async def delete_test(
        session: AsyncSession, test_id: UUID,
    ) -> None:
        """Soft-delete a quality test definition."""
        test = await QualityTestService.get_test(session, test_id)
        test.is_active = False
        await session.flush()
        logger.info("Soft-deleted quality test %s", test_id)


class TestResultService:
    """Service class for recording and querying quality test results."""

    @staticmethod
    async def record_result(
        session: AsyncSession, **kwargs: Any,
    ) -> TestResult:
        """Record a quality test result and emit the appropriate event."""
        if "tested_at" in kwargs:
            kwargs.setdefault("tested_at_utc", kwargs["tested_at"].replace(tzinfo=None))
        result_obj = TestResult(**kwargs)
        session.add(result_obj)
        await session.flush()

        # Emit pass/fail event
        result_str = kwargs["result"]
        event_fn = quality_test_passed if result_str == "pass" else quality_test_failed
        await event_bus.publish(event_fn(
            test_id=str(kwargs["test_id"]),
            unit_id=str(kwargs.get("unit_id")) if kwargs.get("unit_id") else None,
            result_id=str(result_obj.id),
        ))

        logger.info(
            "Test result recorded: test=%s result=%s", kwargs["test_id"], result_str,
        )
        return result_obj

    @staticmethod
    async def get_result(
        session: AsyncSession, result_id: UUID,
    ) -> TestResult:
        """Get a test result by ID."""
        stmt = select(TestResult).where(TestResult.id == result_id)
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(
                resource="TestResult", resource_id=str(result_id),
            )
        return obj

    @staticmethod
    async def list_results(
        session: AsyncSession,
        params: PaginationParams,
        test_id: UUID | None = None,
        unit_id: UUID | None = None,
        lot_id: UUID | None = None,
        result_filter: str | None = None,
    ) -> tuple[Sequence[TestResult], str | None, bool]:
        """List test results with optional filters."""
        stmt = select(TestResult)
        if test_id is not None:
            stmt = stmt.where(TestResult.test_id == test_id)
        if unit_id is not None:
            stmt = stmt.where(TestResult.unit_id == unit_id)
        if lot_id is not None:
            stmt = stmt.where(TestResult.lot_id == lot_id)
        if result_filter is not None:
            stmt = stmt.where(TestResult.result == result_filter)
        return await paginate_query(session, stmt, TestResult, params)


class NonConformanceService:
    """Service class for non-conformance lifecycle management."""

    @staticmethod
    async def create_nc(
        session: AsyncSession, **kwargs: Any,
    ) -> NonConformance:
        """Create a non-conformance record and emit event."""
        nc = NonConformance(**kwargs)
        session.add(nc)
        await session.flush()

        await event_bus.publish(quality_nc_created(
            nc_id=str(nc.id),
            unit_id=str(kwargs.get("unit_id")) if kwargs.get("unit_id") else None,
            nc_type=kwargs["nc_type"],
        ))

        logger.info("Non-conformance created: id=%s type=%s", nc.id, kwargs["nc_type"])
        return nc

    @staticmethod
    async def get_nc(
        session: AsyncSession, nc_id: UUID,
    ) -> NonConformance:
        """Get a non-conformance by ID."""
        stmt = select(NonConformance).where(
            NonConformance.id == nc_id,
            NonConformance.is_active.is_(True),
        )
        result = await session.execute(stmt)
        nc = result.scalar_one_or_none()
        if nc is None:
            raise NotFoundException(
                resource="NonConformance", resource_id=str(nc_id),
            )
        return nc

    @staticmethod
    async def list_ncs(
        session: AsyncSession,
        params: PaginationParams,
        status: str | None = None,
        nc_type: str | None = None,
        unit_id: UUID | None = None,
    ) -> tuple[Sequence[NonConformance], str | None, bool]:
        """List non-conformances with optional filters."""
        stmt = select(NonConformance).where(NonConformance.is_active.is_(True))
        if status is not None:
            stmt = stmt.where(NonConformance.status == status)
        if nc_type is not None:
            stmt = stmt.where(NonConformance.nc_type == nc_type)
        if unit_id is not None:
            stmt = stmt.where(NonConformance.unit_id == unit_id)
        return await paginate_query(session, stmt, NonConformance, params)

    @staticmethod
    async def update_nc(
        session: AsyncSession, nc_id: UUID, **kwargs: Any,
    ) -> NonConformance:
        """
        Update a non-conformance. Enforces status transition rules and
        requires disposition when resolving.
        """
        nc = await NonConformanceService.get_nc(session, nc_id)
        updates = {k: v for k, v in kwargs.items() if v is not None}

        # Validate status transition if status is changing
        if "status" in updates and updates["status"] != nc.status:
            new_status = updates["status"]
            allowed = NC_TRANSITIONS.get(nc.status, set())
            if new_status not in allowed:
                raise InvalidNCTransitionException(nc.status, new_status)

            # Require disposition when resolving
            if new_status == "resolved":
                disposition = updates.get("disposition") or nc.disposition
                if disposition is None:
                    raise DispositionRequiredException()
                now = datetime.now(timezone.utc)
                nc.resolved_at = now
                nc.resolved_at_utc = now.replace(tzinfo=None)

            nc.status = new_status

        # Apply other fields
        for key in ("disposition", "resolved_by_id", "description"):
            if key in updates:
                setattr(nc, key, updates[key])

        await session.flush()

        # Emit resolved event if just resolved
        if nc.status == "resolved" and "status" in updates:
            await event_bus.publish(quality_nc_resolved(
                nc_id=str(nc.id),
                disposition=nc.disposition or "",
            ))

        return nc

    @staticmethod
    async def delete_nc(
        session: AsyncSession, nc_id: UUID,
    ) -> None:
        """Soft-delete a non-conformance record."""
        nc = await NonConformanceService.get_nc(session, nc_id)
        nc.is_active = False
        await session.flush()
        logger.info("Soft-deleted non-conformance %s", nc_id)


class QualityTestExecutionService:
    """
    Executes a defined `QualityTest` against the configured `test_equipment`
    adapter plugin and records the resulting `TestResult`.

    The adapter is resolved at call time via the running `PluginManager`, so
    swapping `mock-test-equipment` for a real adapter (e.g. an OPC-UA tester)
    requires no change to this service.
    """

    @staticmethod
    async def execute(
        session: AsyncSession,
        *,
        test_id: UUID,
        unit_id: UUID | None = None,
        lot_id: UUID | None = None,
        operator_id: UUID | None = None,
        equipment_id: UUID | None = None,
        notes: str | None = None,
    ) -> TestResult:
        """Run the quality test on the live test_equipment adapter and persist the result."""
        # 1. Verify the test definition exists and is active.
        test = await QualityTestService.get_test(session, test_id)

        # 2. Resolve the running test_equipment adapter plugin.
        from mes.framework.api.exceptions import ServiceUnavailableException
        from mes.main import plugin_manager

        adapter = plugin_manager.get_adapter_by_type("test_equipment")
        if adapter is None:
            raise ServiceUnavailableException(
                message=(
                    "No test_equipment adapter is running. Install and enable a "
                    "test_equipment plugin (e.g. mock-test-equipment)."
                ),
                details={"error_code": "TEST_EQUIPMENT_ADAPTER_UNAVAILABLE"},
            )

        # 3. Ask the adapter for a measurement. Adapters return a TestResultDTO.
        dto = await adapter.get_test_result(str(test.id))

        # 4. Persist as a TestResult row (emits pass/fail event via record_result).
        return await TestResultService.record_result(
            session,
            test_id=test.id,
            unit_id=unit_id,
            lot_id=lot_id,
            result=dto.result if dto.result in {"pass", "fail"} else "fail",
            measured_values=dict(dto.measured_values) if dto.measured_values else None,
            operator_id=operator_id,
            equipment_id=equipment_id,
            tested_at=dto.timestamp,
            notes=notes,
        )
