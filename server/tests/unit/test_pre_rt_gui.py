"""
Unit tests for the 4 pre-RT-GUI server-side features:

1. WebSocket event gateway (_ConnectionManager, topic matching)
2. Serial number auto-generation (template formatting)
3. Lot hold / scrap / release-hold (events + schemas)
4. Dashboard aggregation (route registration, service class)
"""

from __future__ import annotations

import asyncio
import types
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.framework.events.schema import MESEvent


# ═════════════════════════════════════════════════════════════════════
# 1. WEBSOCKET EVENT GATEWAY
# ═════════════════════════════════════════════════════════════════════


class TestConnectionManagerMatching:
    """Test the static topic-matching logic in _ConnectionManager."""

    @staticmethod
    def _matches_any(patterns: set[str], event_type: str) -> bool:
        """Mirror the gateway's matching logic for isolated unit testing."""
        import fnmatch

        for p in patterns:
            if p == "*":
                return True
            parts = p.split(".")
            event_parts = event_type.split(".")
            if parts[-1] == "*":
                prefix = parts[:-1]
                if len(event_parts) >= len(prefix) and event_parts[: len(prefix)] == prefix:
                    return True
            elif fnmatch.fnmatch(event_type, p):
                return True
        return False

    def test_wildcard_star_matches_everything(self):
        assert self._matches_any({"*"}, "wip.unit.created")
        assert self._matches_any({"*"}, "dispatch.assigned")

    def test_prefix_wildcard_matches(self):
        assert self._matches_any({"wip.*"}, "wip.unit.created")
        assert self._matches_any({"wip.unit.*"}, "wip.unit.created")

    def test_prefix_wildcard_no_match(self):
        assert not self._matches_any({"dispatch.*"}, "wip.unit.created")

    def test_exact_match(self):
        assert self._matches_any({"wip.unit.created"}, "wip.unit.created")

    def test_exact_no_match(self):
        assert not self._matches_any({"wip.unit.moved"}, "wip.unit.created")

    def test_empty_patterns_matches_nothing(self):
        # Empty set means "all events" in the gateway, but _matches_any itself
        # is not called when patterns is empty — this tests the function in isolation
        assert not self._matches_any(set(), "wip.unit.created")

    def test_multiple_patterns_any_match(self):
        patterns = {"wip.unit.*", "dispatch.*"}
        assert self._matches_any(patterns, "wip.unit.started")
        assert self._matches_any(patterns, "dispatch.assigned")
        assert not self._matches_any(patterns, "quality.alert")


class TestConnectionManagerImport:
    """Verify the gateway module and manager are importable."""

    def test_import_gateway_module(self):
        from mes.framework.events.gateway import router, get_connection_manager
        assert router is not None
        assert callable(get_connection_manager)

    def test_manager_initial_count(self):
        from mes.framework.events.gateway import _ConnectionManager
        mgr = _ConnectionManager()
        assert mgr.active_count == 0


class TestGatewayRouterRegistered:
    """Verify the events router is included in the app."""

    def test_events_ws_route_in_app(self):
        from mes.main import create_app
        app = create_app()
        ws_routes = [
            r.path for r in app.routes
            if hasattr(r, "path") and "events" in r.path
        ]
        assert "/api/v1/events/ws" in ws_routes


# ═════════════════════════════════════════════════════════════════════
# 2. SERIAL NUMBER AUTO-GENERATION
# ═════════════════════════════════════════════════════════════════════


class TestFormatTemplate:
    """Test the _format_template helper in isolation."""

    def test_default_serial_template(self):
        from mes.core.wip.serial import _format_template

        order = types.SimpleNamespace(order_number="WO-001")
        product = types.SimpleNamespace(code="WIDGET")
        now = datetime(2026, 4, 2, 10, 30, 0, tzinfo=timezone.utc)

        result = _format_template("SN-{order}-{seq:05d}", order, product, 1, now)
        assert result == "SN-WO-001-00001"

    def test_default_lot_template(self):
        from mes.core.wip.serial import _format_template

        order = types.SimpleNamespace(order_number="WO-001")
        product = types.SimpleNamespace(code="WIDGET")
        now = datetime(2026, 4, 2, 10, 30, 0, tzinfo=timezone.utc)

        result = _format_template("LOT-{order}-{seq:04d}", order, product, 7, now)
        assert result == "LOT-WO-001-0007"

    def test_date_variables(self):
        from mes.core.wip.serial import _format_template

        order = types.SimpleNamespace(order_number="WO-X")
        product = types.SimpleNamespace(code="P1")
        now = datetime(2026, 12, 25, 0, 0, 0, tzinfo=timezone.utc)

        result = _format_template("{date}-{year}-{month}-{day}", order, product, 1, now)
        assert result == "20261225-2026-12-25"

    def test_product_variable(self):
        from mes.core.wip.serial import _format_template

        order = types.SimpleNamespace(order_number="WO-1")
        product = types.SimpleNamespace(code="GIZMO")
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)

        result = _format_template("{product}-{seq}", order, product, 42, now)
        assert result == "GIZMO-42"

    def test_product_none_fallback(self):
        from mes.core.wip.serial import _format_template

        order = types.SimpleNamespace(order_number="WO-1")
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)

        result = _format_template("{product}-{seq}", order, None, 1, now)
        assert result == "UNKNOWN-1"

    def test_seq_formatting_zero_padded(self):
        from mes.core.wip.serial import _format_template

        order = types.SimpleNamespace(order_number="X")
        product = None
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)

        result = _format_template("{seq:08d}", order, product, 3, now)
        assert result == "00000003"


class TestSerialNumberServiceImport:
    """Verify SerialNumberService and default templates are accessible."""

    def test_import_service(self):
        from mes.core.wip.serial import SerialNumberService
        assert hasattr(SerialNumberService, "generate_serial_number")
        assert hasattr(SerialNumberService, "generate_lot_number")

    def test_default_templates(self):
        from mes.core.wip.serial import DEFAULT_SERIAL_TEMPLATE, DEFAULT_LOT_TEMPLATE
        assert "{seq" in DEFAULT_SERIAL_TEMPLATE
        assert "{seq" in DEFAULT_LOT_TEMPLATE
        assert "{order}" in DEFAULT_SERIAL_TEMPLATE


class TestSerialSchemaOptional:
    """Verify UnitCreate / LotCreate accept None serial/lot numbers."""

    def test_unit_create_serial_none_auto_generate(self):
        from mes.core.wip.schemas import UnitCreate
        data = UnitCreate(
            serial_number=None,
            order_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        assert data.serial_number is None

    def test_unit_create_serial_explicit(self):
        from mes.core.wip.schemas import UnitCreate
        data = UnitCreate(
            serial_number="MY-SN-001",
            order_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        assert data.serial_number == "MY-SN-001"

    def test_unit_create_serial_template(self):
        from mes.core.wip.schemas import UnitCreate
        data = UnitCreate(
            serial_number=None,
            serial_template="{product}-{seq:06d}",
            order_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        assert data.serial_template == "{product}-{seq:06d}"

    def test_lot_create_lot_number_none(self):
        from mes.core.wip.schemas import LotCreate
        data = LotCreate(
            lot_number=None,
            order_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            quantity=50,
        )
        assert data.lot_number is None

    def test_lot_create_lot_template(self):
        from mes.core.wip.schemas import LotCreate
        data = LotCreate(
            lot_number=None,
            lot_template="BATCH-{date}-{seq:03d}",
            order_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            quantity=10,
        )
        assert data.lot_template == "BATCH-{date}-{seq:03d}"


# ═════════════════════════════════════════════════════════════════════
# 3. LOT HOLD / SCRAP / RELEASE-HOLD
# ═════════════════════════════════════════════════════════════════════


class TestLotHoldScrapEvents:
    """Verify the three new lot event factories."""

    def test_lot_held_event(self):
        from mes.core.wip.events import lot_held
        ev = lot_held("lot-1", "suspect contamination")
        assert ev.event_type == "wip.lot.held"
        assert ev.source == "wip"
        assert ev.payload["lot_id"] == "lot-1"
        assert ev.payload["reason"] == "suspect contamination"

    def test_lot_released_event(self):
        from mes.core.wip.events import lot_released
        ev = lot_released("lot-2")
        assert ev.event_type == "wip.lot.released"
        assert ev.payload["lot_id"] == "lot-2"

    def test_lot_scrapped_event(self):
        from mes.core.wip.events import lot_scrapped
        ev = lot_scrapped("lot-3", "step-5", "failed inspection", 25)
        assert ev.event_type == "wip.lot.scrapped"
        assert ev.payload["lot_id"] == "lot-3"
        assert ev.payload["step_id"] == "step-5"
        assert ev.payload["reason"] == "failed inspection"
        assert ev.payload["quantity"] == 25


class TestLotServiceMethods:
    """Verify LotService has hold_lot, release_hold_lot, scrap_lot methods."""

    def test_hold_lot_exists(self):
        from mes.core.wip.service import LotService
        assert hasattr(LotService, "hold_lot")
        assert callable(getattr(LotService, "hold_lot"))

    def test_release_hold_lot_exists(self):
        from mes.core.wip.service import LotService
        assert hasattr(LotService, "release_hold_lot")
        assert callable(getattr(LotService, "release_hold_lot"))

    def test_scrap_lot_exists(self):
        from mes.core.wip.service import LotService
        assert hasattr(LotService, "scrap_lot")
        assert callable(getattr(LotService, "scrap_lot"))


class TestLotEndpointsRegistered:
    """Verify the 3 lot endpoints are registered via the router."""

    def test_lot_hold_route(self):
        from mes.core.wip.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/lots/{lot_id}/hold" in paths

    def test_lot_release_hold_route(self):
        from mes.core.wip.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/lots/{lot_id}/release-hold" in paths

    def test_lot_scrap_route(self):
        from mes.core.wip.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/lots/{lot_id}/scrap" in paths


# ═════════════════════════════════════════════════════════════════════
# 4. DASHBOARD AGGREGATION
# ═════════════════════════════════════════════════════════════════════


class TestDashboardModuleImport:
    """Verify the dashboard module is importable."""

    def test_import_dashboard(self):
        from mes.core.dashboard import router, DashboardService
        assert router is not None
        assert DashboardService is not None

    def test_service_methods(self):
        from mes.core.dashboard.service import DashboardService
        assert hasattr(DashboardService, "order_progress")
        assert hasattr(DashboardService, "line_status")
        assert hasattr(DashboardService, "shift_summary")

    def test_order_progress_is_static(self):
        from mes.core.dashboard.service import DashboardService
        assert isinstance(
            DashboardService.__dict__["order_progress"],
            staticmethod,
        )

    def test_line_status_is_static(self):
        from mes.core.dashboard.service import DashboardService
        assert isinstance(
            DashboardService.__dict__["line_status"],
            staticmethod,
        )

    def test_shift_summary_is_static(self):
        from mes.core.dashboard.service import DashboardService
        assert isinstance(
            DashboardService.__dict__["shift_summary"],
            staticmethod,
        )


class TestDashboardRoutesRegistered:
    """Verify dashboard endpoints are registered."""

    def test_order_progress_route(self):
        from mes.core.dashboard.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/dashboard/order-progress" in paths

    def test_line_status_route(self):
        from mes.core.dashboard.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/dashboard/line-status" in paths

    def test_shift_summary_route(self):
        from mes.core.dashboard.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/dashboard/shift-summary" in paths


class TestDashboardRouterInApp:
    """Verify dashboard router is included in the main app."""

    def test_dashboard_routes_in_app(self):
        from mes.main import create_app
        app = create_app()
        paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/dashboard/order-progress" in paths
        assert "/api/v1/dashboard/line-status" in paths
        assert "/api/v1/dashboard/shift-summary" in paths
