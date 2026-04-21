"""
Unit tests for the WIP generator background task.

Covers:
- process_released_orders: discrete product → creates units
- process_released_orders: process product → creates lot
- process_released_orders: no released orders → returns 0
- process_released_orders: missing product → skips order
- process_released_orders: error on one order doesn't block others
- wip_generator_loop: cancellation
"""

from __future__ import annotations

import asyncio
import types
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mes.core.operations.wip_generator import (
    WIP_GENERATOR_INTERVAL_SEC,
    _generate_wip_for_order,
    process_released_orders,
    wip_generator_loop,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_order(**overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "order_number": "ORD-001",
        "product_id": uuid.uuid4(),
        "route_id": None,
        "quantity_ordered": 5,
        "status": "released",
        "priority": 0,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_product(product_type: str = "discrete", **overrides) -> types.SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "code": "PROD-001",
        "name": "Test Product",
        "product_type": product_type,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═══════════════════════════════════════════════════════════════════
# 1. MODULE CONSTANTS
# ═══════════════════════════════════════════════════════════════════


class TestWipGeneratorConstants:
    def test_default_interval(self):
        assert WIP_GENERATOR_INTERVAL_SEC == 5


# ═══════════════════════════════════════════════════════════════════
# 2. _generate_wip_for_order
# ═══════════════════════════════════════════════════════════════════


class TestGenerateWipForOrder:
    """Test WIP creation for a single order."""

    @pytest.mark.asyncio
    async def test_discrete_product_creates_units(self):
        """Discrete product → one unit per piece in quantity_ordered."""
        order = _make_order(quantity_ordered=3)
        product = _make_product("discrete", id=order.product_id)

        session = AsyncMock()
        session.get = AsyncMock(return_value=product)

        serial_counter = 0

        async def fake_generate(sess, oid, **kw):
            nonlocal serial_counter
            serial_counter += 1
            return f"SN-{serial_counter:05d}"

        fake_unit = _make_product()  # just needs to be truthy

        with (
            patch(
                "mes.core.operations.wip_generator.SerialNumberService.generate_serial_number",
                side_effect=fake_generate,
            ),
            patch(
                "mes.core.operations.wip_generator.UnitService.create_unit",
                new_callable=AsyncMock,
                return_value=fake_unit,
            ) as mock_create,
        ):
            result = await _generate_wip_for_order(session, order)

        assert result == 3
        assert mock_create.call_count == 3
        # Verify each call got a unique serial
        serials = [c.kwargs["serial_number"] for c in mock_create.call_args_list]
        assert len(set(serials)) == 3

    @pytest.mark.asyncio
    async def test_process_product_creates_lot(self):
        """Process product → one lot with full quantity."""
        order = _make_order(quantity_ordered=100)
        product = _make_product("process", id=order.product_id)

        session = AsyncMock()
        session.get = AsyncMock(return_value=product)

        fake_lot = _make_product()

        with (
            patch(
                "mes.core.operations.wip_generator.SerialNumberService.generate_lot_number",
                new_callable=AsyncMock,
                return_value="LOT-0001",
            ),
            patch(
                "mes.core.operations.wip_generator.LotService.create_lot",
                new_callable=AsyncMock,
                return_value=fake_lot,
            ) as mock_create,
        ):
            result = await _generate_wip_for_order(session, order)

        assert result == 1
        mock_create.assert_called_once()
        call_kw = mock_create.call_args.kwargs
        assert call_kw["quantity"] == 100
        assert call_kw["lot_number"] == "LOT-0001"

    @pytest.mark.asyncio
    async def test_missing_product_returns_zero(self):
        """Order with missing product → skip, return 0."""
        order = _make_order()
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        result = await _generate_wip_for_order(session, order)
        assert result == 0


# ═══════════════════════════════════════════════════════════════════
# 3. process_released_orders
# ═══════════════════════════════════════════════════════════════════


class TestProcessReleasedOrders:

    @pytest.mark.asyncio
    async def test_no_released_orders_returns_zero(self):
        """No released orders → 0."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await process_released_orders(session)
        assert result == 0

    @pytest.mark.asyncio
    async def test_processes_multiple_orders(self):
        """Multiple released orders → processes each."""
        o1 = _make_order(order_number="ORD-001", quantity_ordered=2)
        o2 = _make_order(order_number="ORD-002", quantity_ordered=3)

        session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [o1, o2]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "mes.core.operations.wip_generator._generate_wip_for_order",
            new_callable=AsyncMock,
            side_effect=[2, 3],
        ) as mock_gen:
            result = await process_released_orders(session)

        assert result == 5
        assert mock_gen.call_count == 2

    @pytest.mark.asyncio
    async def test_error_on_one_order_continues(self):
        """Error on one order doesn't block the rest."""
        o1 = _make_order(order_number="ORD-FAIL")
        o2 = _make_order(order_number="ORD-OK")

        session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [o1, o2]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "mes.core.operations.wip_generator._generate_wip_for_order",
            new_callable=AsyncMock,
            side_effect=[RuntimeError("boom"), 4],
        ):
            result = await process_released_orders(session)

        assert result == 4  # only second order counted


# ═══════════════════════════════════════════════════════════════════
# 4. wip_generator_loop
# ═══════════════════════════════════════════════════════════════════


class TestWipGeneratorLoop:

    @pytest.mark.asyncio
    async def test_loop_cancels_cleanly(self):
        """The loop should raise CancelledError when cancelled."""
        with patch(
            "mes.core.operations.wip_generator.asyncio.sleep",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError,
        ):
            with pytest.raises(asyncio.CancelledError):
                await wip_generator_loop(interval=1)

    @pytest.mark.asyncio
    async def test_loop_processes_and_commits(self):
        """The loop calls process_released_orders and commits."""
        call_count = 0

        async def fake_sleep(n):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError

        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "mes.core.operations.wip_generator.asyncio.sleep",
                side_effect=fake_sleep,
            ),
            patch(
                "mes.framework.db.async_session_factory",
                return_value=mock_session_ctx,
            ),
            patch(
                "mes.core.operations.wip_generator.process_released_orders",
                new_callable=AsyncMock,
                return_value=2,
            ) as mock_process,
        ):
            with pytest.raises(asyncio.CancelledError):
                await wip_generator_loop(interval=1)

        mock_process.assert_called_once_with(mock_session)
        mock_session.commit.assert_called_once()
