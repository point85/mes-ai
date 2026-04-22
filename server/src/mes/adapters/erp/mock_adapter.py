"""
ERP Adapter: Mock implementation for development, testing, and demo.

MockERPInboundAdapter reads from JSON fixture files.
MockERPOutboundAdapter writes reports to JSON files.
Both support configurable latency and failure simulation.

Per ARCHITECTURE.md §9.2.9.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from .dtos import (
    BillOfMaterialDTO,
    ERPConfirmation,
    MaterialConsumptionDTO,
    MaterialDefinitionDTO,
    ProcessRouteDTO,
    ProductDefinitionDTO,
    OperationsRequestDTO,
    WorkCellDTO,
)
from .interfaces import ERPInboundAdapter, ERPOutboundAdapter, ERPTransformLayer

logger = logging.getLogger("mes.adapters.erp.mock")

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockERPTransformLayer(ERPTransformLayer):
    """
    Pass-through transform — mock JSON fixtures already use MES field names.
    """


class MockERPInboundAdapter(ERPInboundAdapter):
    """
    Mock ERP inbound adapter that reads from JSON fixture files.

    Config options (passed to __init__):
        fixture_dir: Path to directory containing JSON fixture files.
            Defaults to the built-in fixtures/ directory.
        latency_ms: Simulated response latency in milliseconds (default 0).
        failure_rate: Probability [0.0, 1.0) of raising an error (default 0.0).
    """

    def __init__(
        self,
        fixture_dir: str | Path | None = None,
        latency_ms: int = 0,
        failure_rate: float = 0.0,
    ) -> None:
        self._fixture_dir = Path(fixture_dir) if fixture_dir else _FIXTURES_DIR
        self._latency_ms = max(0, latency_ms)
        self._failure_rate = max(0.0, min(1.0, failure_rate))
        self._connected = False
        self._transform = MockERPTransformLayer()

    async def connect(self) -> None:
        await self._simulate_latency()
        self._connected = True
        logger.info("MockERPInboundAdapter connected (fixtures: %s)", self._fixture_dir)

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("MockERPInboundAdapter disconnected")

    async def health_check(self) -> bool:
        return self._connected and self._fixture_dir.exists()

    async def sync_operations_requests(
        self, since: datetime | None = None,
    ) -> list[OperationsRequestDTO]:
        data = await self._read_fixture("operations_requests.json")
        return [self._transform.to_operations_request(d) for d in data]

    async def sync_materials(
        self, since: datetime | None = None,
    ) -> list[MaterialDefinitionDTO]:
        data = await self._read_fixture("materials.json")
        return [self._transform.to_material(d) for d in data]

    async def sync_products(
        self, since: datetime | None = None,
    ) -> list[ProductDefinitionDTO]:
        data = await self._read_fixture("products.json")
        return [ProductDefinitionDTO(**d) for d in data]

    async def sync_boms(self, product_id: str) -> list[BillOfMaterialDTO]:
        # Mock: return empty — BOMs not in default fixtures
        await self._simulate_latency()
        self._maybe_fail()
        return []

    async def sync_routings(self, product_id: str) -> list[ProcessRouteDTO]:
        # Mock: return empty — routings not in default fixtures
        await self._simulate_latency()
        self._maybe_fail()
        return []

    async def sync_work_cells(self) -> list[WorkCellDTO]:
        # Mock: return empty — work cells not in default fixtures
        await self._simulate_latency()
        self._maybe_fail()
        return []

    async def _read_fixture(self, filename: str) -> list[dict[str, Any]]:
        """Read and parse a JSON fixture file."""
        await self._simulate_latency()
        self._maybe_fail()
        filepath = self._fixture_dir / filename
        if not filepath.exists():
            logger.warning("Fixture file not found: %s", filepath)
            return []
        text = filepath.read_text(encoding="utf-8")
        return json.loads(text)

    async def _simulate_latency(self) -> None:
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

    def _maybe_fail(self) -> None:
        if self._failure_rate > 0 and random.random() < self._failure_rate:  # noqa: S311
            from .exceptions import ERPSyncError
            raise ERPSyncError(message="Simulated ERP sync failure")


class MockERPOutboundAdapter(ERPOutboundAdapter):
    """
    Mock ERP outbound adapter that writes reports to JSON files.

    Config options (passed to __init__):
        output_dir: Directory to write report JSON files. Defaults to a
            temp directory. If None, reports are stored in-memory only.
        latency_ms: Simulated response latency in milliseconds (default 0).
        failure_rate: Probability [0.0, 1.0) of raising an error (default 0.0).
    """

    def __init__(
        self,
        output_dir: str | Path | None = None,
        latency_ms: int = 0,
        failure_rate: float = 0.0,
    ) -> None:
        self._output_dir = Path(output_dir) if output_dir else None
        self._latency_ms = max(0, latency_ms)
        self._failure_rate = max(0.0, min(1.0, failure_rate))
        self._connected = False
        self._reports: list[dict[str, Any]] = []
        self._doc_counter = 0

    @property
    def reports(self) -> list[dict[str, Any]]:
        """In-memory store of all reports sent (for test assertions)."""
        return list(self._reports)

    async def connect(self) -> None:
        await self._simulate_latency()
        if self._output_dir:
            self._output_dir.mkdir(parents=True, exist_ok=True)
        self._connected = True
        logger.info("MockERPOutboundAdapter connected (output: %s)", self._output_dir or "in-memory")

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("MockERPOutboundAdapter disconnected")

    async def health_check(self) -> bool:
        return self._connected

    async def report_completion(
        self, order_id: str, qty_good: int, qty_reject: int,
        step_id: str | None = None,
    ) -> ERPConfirmation:
        report = {
            "type": "completion",
            "order_id": order_id,
            "qty_good": qty_good,
            "qty_reject": qty_reject,
            "step_id": step_id,
        }
        return await self._send_report(report)

    async def report_consumption(
        self, order_id: str, materials: list[MaterialConsumptionDTO],
    ) -> ERPConfirmation:
        report = {
            "type": "consumption",
            "order_id": order_id,
            "materials": [m.model_dump() for m in materials],
        }
        return await self._send_report(report)

    async def report_scrap(
        self, order_id: str, qty_scrapped: int, reason_code: str,
    ) -> ERPConfirmation:
        report = {
            "type": "scrap",
            "order_id": order_id,
            "qty_scrapped": qty_scrapped,
            "reason_code": reason_code,
        }
        return await self._send_report(report)

    async def report_labor(
        self, order_id: str, operator_id: str, duration_minutes: float,
    ) -> ERPConfirmation:
        report = {
            "type": "labor",
            "order_id": order_id,
            "operator_id": operator_id,
            "duration_minutes": duration_minutes,
        }
        return await self._send_report(report)

    async def report_downtime(
        self, equipment_id: str, duration_minutes: float,
        reason_code: str, started_at: datetime,
    ) -> ERPConfirmation:
        report = {
            "type": "downtime",
            "equipment_id": equipment_id,
            "duration_minutes": duration_minutes,
            "reason_code": reason_code,
            "started_at": started_at.isoformat(),
        }
        return await self._send_report(report)

    async def report_quality_result(
        self, order_id: str, test_id: str, result: str,
        details: dict[str, Any],
    ) -> ERPConfirmation:
        report = {
            "type": "quality_result",
            "order_id": order_id,
            "test_id": test_id,
            "result": result,
            "details": details,
        }
        return await self._send_report(report)

    async def _send_report(self, report: dict[str, Any]) -> ERPConfirmation:
        """Store report in memory and optionally write to file."""
        await self._simulate_latency()
        self._maybe_fail()

        self._doc_counter += 1
        doc_number = f"MOCK-{self._doc_counter:04d}"
        report["erp_doc_number"] = doc_number

        self._reports.append(report)

        if self._output_dir:
            filepath = self._output_dir / f"{report['type']}_{doc_number}.json"
            filepath.write_text(
                json.dumps(report, indent=2, default=str),
                encoding="utf-8",
            )

        return ERPConfirmation(success=True, erp_doc_number=doc_number)

    async def _simulate_latency(self) -> None:
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

    def _maybe_fail(self) -> None:
        if self._failure_rate > 0 and random.random() < self._failure_rate:  # noqa: S311
            from .exceptions import ERPOutboundError
            raise ERPOutboundError(message="Simulated ERP outbound failure")
