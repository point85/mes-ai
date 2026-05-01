"""
Unit tests for the RT-CLIENT server endpoints added to WIP-TRACK.

Covers:
- UnitService.get_unit_by_serial  (service layer)
- LotService.get_lot_by_number    (service layer)
- build_step_context              (composite builder)
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mes.framework.api.exceptions import NotFoundException
from mes.core.wip.service import UnitService, LotService
from mes.core.wip.step_context import build_step_context


# ─── Helpers ──────────────────────────────────────────────────────────

def _make_unit(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "serial_number": "SN-001",
        "order_id": uuid.uuid4(),
        "product_id": uuid.uuid4(),
        "route_id": uuid.uuid4(),
        "current_step_id": uuid.uuid4(),
        "status": "queued",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_lot(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "lot_number": "LOT-001",
        "order_id": uuid.uuid4(),
        "product_id": uuid.uuid4(),
        "route_id": uuid.uuid4(),
        "current_step_id": uuid.uuid4(),
        "quantity": 100,
        "good_quantity": 100,
        "status": "queued",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _mock_session_returning(value):
    """Create an AsyncMock session whose execute returns a scalar result."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ─── UnitService.get_unit_by_serial ──────────────────────────────────

class TestGetUnitBySerial:
    @pytest.mark.asyncio
    async def test_returns_unit_when_found(self):
        unit = _make_unit(serial_number="SN-ABC")
        session = _mock_session_returning(unit)

        result = await UnitService.get_unit_by_serial(session, "SN-ABC")

        assert result is unit
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_not_found_when_missing(self):
        session = _mock_session_returning(None)

        with pytest.raises(NotFoundException) as exc_info:
            await UnitService.get_unit_by_serial(session, "SN-MISSING")

        assert "Unit" in str(exc_info.value)
        assert "SN-MISSING" in str(exc_info.value)


# ─── LotService.get_lot_by_number ────────────────────────────────────

class TestGetLotByNumber:
    @pytest.mark.asyncio
    async def test_returns_lot_when_found(self):
        lot = _make_lot(lot_number="LOT-XYZ")
        session = _mock_session_returning(lot)

        result = await LotService.get_lot_by_number(session, "LOT-XYZ")

        assert result is lot
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_not_found_when_missing(self):
        session = _mock_session_returning(None)

        with pytest.raises(NotFoundException) as exc_info:
            await LotService.get_lot_by_number(session, "LOT-MISSING")

        assert "Lot" in str(exc_info.value)
        assert "LOT-MISSING" in str(exc_info.value)


# ─── build_step_context ──────────────────────────────────────────────

class TestBuildStepContext:
    @pytest.mark.asyncio
    async def test_raises_on_no_arguments(self):
        session = AsyncMock()
        with pytest.raises(ValueError, match="unit_id or lot_id required"):
            await build_step_context(session)

    @pytest.mark.asyncio
    async def test_unit_with_no_current_step(self):
        unit_id = uuid.uuid4()
        order_id = uuid.uuid4()
        unit = _make_unit(
            id=unit_id,
            order_id=order_id,
            current_step_id=None,
        )

        with (
            patch.object(UnitService, "get_unit", new_callable=AsyncMock, return_value=unit),
            patch("mes.core.wip.step_context.RoutingEngineService") as mock_routing,
        ):
            mock_routing.get_process_segments = AsyncMock(return_value=[])
            session = AsyncMock()
            ctx = await build_step_context(session, unit_id=unit_id)

        assert ctx["wip_type"] == "unit"
        assert ctx["wip"]["serial_number"] == "SN-001"
        assert ctx["step"] is None
        assert ctx["step_parameters"] == []
        assert ctx["data_definitions"] == []
        assert ctx["quality_tests"] == []
        assert ctx["dispositions"] == []
        assert ctx["route_steps"] == []

    @pytest.mark.asyncio
    async def test_lot_with_no_current_step(self):
        lot_id = uuid.uuid4()
        order_id = uuid.uuid4()
        lot = _make_lot(
            id=lot_id,
            order_id=order_id,
            current_step_id=None,
        )

        with (
            patch.object(LotService, "get_lot", new_callable=AsyncMock, return_value=lot),
            patch("mes.core.wip.step_context.RoutingEngineService") as mock_routing,
        ):
            mock_routing.get_process_segments = AsyncMock(return_value=[])
            session = AsyncMock()
            ctx = await build_step_context(session, lot_id=lot_id)

        assert ctx["wip_type"] == "lot"
        assert ctx["wip"]["lot_number"] == "LOT-001"
        assert ctx["step"] is None
        assert ctx["dispositions"] == []

    @pytest.mark.asyncio
    async def test_unit_with_current_step_loads_all_data(self):
        unit_id = uuid.uuid4()
        step_id = uuid.uuid4()
        route_id = uuid.uuid4()
        order_id = uuid.uuid4()

        unit = _make_unit(
            id=unit_id,
            order_id=order_id,
            route_id=route_id,
            current_step_id=step_id,
        )

        step_obj = types.SimpleNamespace(
            id=step_id,
            route_id=route_id,
            name="Assembly",
            step_type="standard",
            sequence=1,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            erp_operation_number=None,
            equipment_class_id=None,
            expected_cycle_time_sec=None,
            is_initial_step=False,
            input_dispositions=[],
            output_dispositions=[],
        )

        # Track which selects are called
        execute_results = []

        async def fake_execute(stmt):
            mock_result = MagicMock()
            idx = len(execute_results)
            execute_results.append(idx)
            if idx == 0:
                # step lookup
                mock_result.scalar_one_or_none.return_value = step_obj
            elif idx == 1:
                # step parameters
                mock_result.scalars.return_value.all.return_value = []
            elif idx == 2:
                # data definitions
                mock_result.scalars.return_value.all.return_value = []
            elif idx == 3:
                # quality tests
                mock_result.scalars.return_value.all.return_value = []
            elif idx == 4:
                # eager-load route steps with disposition lists
                mock_result.scalars.return_value.all.return_value = [step_obj]
            return mock_result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=fake_execute)

        with (
            patch.object(UnitService, "get_unit", new_callable=AsyncMock, return_value=unit),
            patch("mes.core.wip.step_context.RoutingEngineService") as mock_routing,
        ):
            mock_routing.get_available_dispositions = AsyncMock(return_value=[])
            mock_routing.get_process_segments = AsyncMock(return_value=[step_obj])

            ctx = await build_step_context(session, unit_id=unit_id)

        assert ctx["wip_type"] == "unit"
        assert ctx["step"]["name"] == "Assembly"
        assert ctx["step"]["step_type"] == "standard"
        assert ctx["dispositions"] == []
        assert len(ctx["route_steps"]) == 1
        assert ctx["route_steps"][0]["name"] == "Assembly"
        # Verify all 5 session.execute calls happened
        # (step, params, defs, tests, route_steps eager-load)
        assert len(execute_results) == 5
    @pytest.mark.asyncio
    async def test_process_segments_empty_on_exception(self):
        """If RoutingEngineService.get_process_segments raises, route_steps is []."""
        unit_id = uuid.uuid4()
        unit = _make_unit(id=unit_id, current_step_id=None)

        with (
            patch.object(UnitService, "get_unit", new_callable=AsyncMock, return_value=unit),
            patch("mes.core.wip.step_context.RoutingEngineService") as mock_routing,
        ):
            mock_routing.get_process_segments = AsyncMock(side_effect=RuntimeError("boom"))
            session = AsyncMock()
            ctx = await build_step_context(session, unit_id=unit_id)

        assert ctx["route_steps"] == []

    @pytest.mark.asyncio
    async def test_step_with_dispositions(self):
        unit_id = uuid.uuid4()
        step_id = uuid.uuid4()
        route_id = uuid.uuid4()
        order_id = uuid.uuid4()

        unit = _make_unit(
            id=unit_id,
            order_id=order_id,
            route_id=route_id,
            current_step_id=step_id,
        )

        step_obj = types.SimpleNamespace(
            id=step_id,
            route_id=route_id,
            name="MRB Review",
            step_type="mrb",
            sequence=3,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            erp_operation_number=None,
            equipment_class_id=None,
            expected_cycle_time_sec=None,
            is_initial_step=False,
            input_dispositions=[],
            output_dispositions=[],
        )

        disposition_data = [
            {"label": "Rework", "to_step_id": str(uuid.uuid4())},
            {"label": "Scrap", "to_step_id": None},
        ]

        call_count = 0

        async def fake_execute(stmt):
            nonlocal call_count
            mock_result = MagicMock()
            if call_count == 0:
                mock_result.scalar_one_or_none.return_value = step_obj
            else:
                mock_result.scalars.return_value.all.return_value = []
            call_count += 1
            return mock_result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=fake_execute)

        with (
            patch.object(UnitService, "get_unit", new_callable=AsyncMock, return_value=unit),
            patch("mes.core.wip.step_context.RoutingEngineService") as mock_routing,
        ):
            mock_routing.get_available_dispositions = AsyncMock(return_value=disposition_data)
            mock_routing.get_process_segments = AsyncMock(return_value=[])

            ctx = await build_step_context(session, unit_id=unit_id)

        assert len(ctx["dispositions"]) == 2
        assert ctx["dispositions"][0]["label"] == "Rework"
        assert ctx["dispositions"][1]["label"] == "Scrap"
