from __future__ import annotations

from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError


def test_oee_alert_requires_an_equipment():
    from mes.core.dashboard.schemas import AlertRuleCreate

    with pytest.raises(ValidationError, match="require an equipment_id"):
        AlertRuleCreate(
            name="Low OEE",
            metric="oee_below",
            threshold=0.6,
        )


def test_percent_alert_thresholds_are_bounded():
    from mes.core.dashboard.schemas import AlertRuleCreate

    with pytest.raises(ValidationError, match="between 0 and 1"):
        AlertRuleCreate(
            name="Low OEE",
            metric="oee_below",
            threshold=1.1,
            equipment_id=uuid4(),
        )
    with pytest.raises(ValidationError, match="between 0 and 1"):
        AlertRuleCreate(
            name="High scrap",
            metric="scrap_rate_above",
            threshold=1.1,
        )


def test_dashboard_analytics_routes_and_services_are_registered():
    from mes.core.dashboard.routes import router
    from mes.core.dashboard.service import DashboardService

    routes = {route.path for route in router.routes if hasattr(route, "path")}
    assert {
        "/api/v1/dashboard/production-trends",
        "/api/v1/dashboard/loss-breakdown",
        "/api/v1/dashboard/alerts",
        "/api/v1/dashboard/alert-rules",
        "/api/v1/dashboard/alert-rules/{rule_id}",
    } <= routes
    assert hasattr(DashboardService, "production_trends")
    assert hasattr(DashboardService, "loss_breakdown")
    assert hasattr(DashboardService, "evaluate_alerts")


@pytest.mark.asyncio
async def test_production_trends_returns_daily_zero_filled_series():
    from mes.core.dashboard.service import DashboardService

    today = datetime.now(timezone.utc).date()
    session = AsyncMock()
    result = Mock()
    result.all.return_value = [
        SimpleNamespace(shift_date=today, good=8, reject=1, rework=2, avg_cycle_time=12.0),
    ]
    session.execute.return_value = result

    trends = await DashboardService.production_trends(session, days=7)

    assert len(trends["series"]) == 7
    assert trends["series"][-1] == {
        "date": today.isoformat(),
        "good": 8,
        "reject": 1,
        "rework": 2,
        "oee": None,
    }
    assert trends["series"][0]["good"] == 0
    assert trends["source"] == "counters"


@pytest.mark.asyncio
async def test_production_trends_fall_back_to_wip_when_no_counters():
    from mes.core.dashboard.service import DashboardService

    today = datetime.now(timezone.utc).date()
    now = datetime.now(timezone.utc)

    def make(rows):
        r = Mock()
        r.all.return_value = rows
        return r

    session = AsyncMock()
    session.execute.side_effect = [
        make([]),  # counters
        make([(now, None), (now, None)]),  # completed units
        make([(now, None)]),  # scrapped units
        make([]),  # rework
    ]

    trends = await DashboardService.production_trends(session, days=7)

    assert trends["source"] == "wip"
    assert trends["series"][-1]["date"] == today.isoformat()
    assert trends["series"][-1]["good"] == 2
    assert trends["series"][-1]["reject"] == 1


@pytest.mark.asyncio
async def test_production_trends_source_none_when_no_data():
    from mes.core.dashboard.service import DashboardService

    empty = Mock()
    empty.all.return_value = []
    session = AsyncMock()
    session.execute.return_value = empty

    trends = await DashboardService.production_trends(session, days=7)

    assert trends["source"] == "none"
    assert all(p["good"] == 0 for p in trends["series"])


@pytest.mark.asyncio
async def test_update_alert_rule_definition_changes_fields():
    from mes.core.dashboard.models import DashboardAlertRule
    from mes.core.dashboard.schemas import AlertRuleCreate
    from mes.core.dashboard.service import DashboardService
    from mes.framework.api.exceptions import NotFoundException

    rule = DashboardAlertRule(
        id=uuid4(), name="Old", metric="downtime_minutes_above", threshold=30,
        window_minutes=60, equipment_id=None, is_enabled=True, is_active=True,
    )
    session = AsyncMock()
    session.get.return_value = rule

    updated = await DashboardService.update_alert_rule_definition(
        session, rule.id,
        AlertRuleCreate(name="New", metric="scrap_rate_above", threshold=0.1, window_minutes=120),
    )
    assert (updated.name, updated.metric, updated.threshold, updated.window_minutes) == (
        "New", "scrap_rate_above", 0.1, 120,
    )

    session.get.return_value = None
    with pytest.raises(NotFoundException):
        await DashboardService.update_alert_rule_definition(
            session, uuid4(),
            AlertRuleCreate(name="x", metric="downtime_minutes_above", threshold=1),
        )


@pytest.mark.asyncio
async def test_alert_rule_dry_run_reports_trigger_without_db_writes():
    from mes.core.dashboard.models import DashboardAlertRule
    from mes.core.dashboard.schemas import AlertTestRequest
    from mes.core.dashboard.service import DashboardService
    from mes.framework.api.exceptions import ValidationException

    rule = DashboardAlertRule(
        id=uuid4(), name="Scrap", metric="scrap_rate_above", threshold=0.05,
        window_minutes=60, equipment_id=None, is_enabled=True, is_active=True,
    )
    session = AsyncMock()
    session.get.return_value = rule

    hit = await DashboardService.test_alert_rule(
        session, rule.id, AlertTestRequest(good_count=90, reject_count=8, rework_count=2),
    )
    assert hit["would_trigger"] is True
    assert hit["observed_value"] == pytest.approx(0.1)

    miss = await DashboardService.test_alert_rule(
        session, rule.id, AlertTestRequest(good_count=100, reject_count=0, rework_count=0),
    )
    assert miss["would_trigger"] is False

    with pytest.raises(ValidationException):
        await DashboardService.test_alert_rule(session, rule.id, AlertTestRequest(good_count=1))
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_oee_alert_dry_run_computes_oee_from_sample():
    from mes.core.dashboard.models import DashboardAlertRule
    from mes.core.dashboard.schemas import AlertTestRequest
    from mes.core.dashboard.service import DashboardService

    rule = DashboardAlertRule(
        id=uuid4(), name="OEE", metric="oee_below", threshold=0.6,
        window_minutes=60, equipment_id=uuid4(), is_enabled=True, is_active=True,
    )
    session = AsyncMock()
    session.get.return_value = rule

    result = await DashboardService.test_alert_rule(
        session, rule.id,
        AlertTestRequest(
            run_minutes=30, downtime_minutes=30, ideal_cycle_time_sec=60,
            good_count=20, reject_count=0, rework_count=0,
        ),
    )
    # availability 0.5 * performance (60*20/1800=0.667) * quality 1.0
    assert result["observed_value"] == pytest.approx(0.3333, abs=1e-3)
    assert result["would_trigger"] is True


@pytest.mark.asyncio
async def test_downtime_alert_is_reported_when_rule_threshold_is_exceeded():
    from mes.core.dashboard.models import DashboardAlertRule
    from mes.core.dashboard.service import DashboardService

    now = datetime.now(timezone.utc)
    log = SimpleNamespace(
        started_at=now - timedelta(minutes=45),
        ended_at=None,
        oee_bucket="downtime_unplanned",
    )
    result = Mock()
    result.scalars.return_value.all.return_value = [log]
    session = AsyncMock()
    session.execute.return_value = result
    rule = DashboardAlertRule(
        id=uuid4(),
        name="Long downtime",
        metric="downtime_minutes_above",
        threshold=30,
        window_minutes=60,
        equipment_id=None,
        is_enabled=True,
    )

    alerts = await DashboardService.evaluate_alerts(session, [rule])

    assert len(alerts) == 1
    assert alerts[0]["rule_name"] == "Long downtime"
    assert alerts[0]["observed_value"] == pytest.approx(45, abs=1)
    assert "down since" in alerts[0]["message"]


@pytest.mark.asyncio
async def test_current_downtime_alert_measures_from_state_start():
    from mes.core.dashboard.models import DashboardAlertRule
    from mes.core.dashboard.service import DashboardService

    started = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
    result = Mock()
    result.scalars.return_value.all.return_value = [
        SimpleNamespace(started_at=started, ended_at=None, oee_bucket="downtime_unplanned"),
    ]
    session = AsyncMock()
    session.execute.return_value = result
    rule = DashboardAlertRule(
        id=uuid4(), name="Down", metric="current_downtime_above", threshold=30,
        window_minutes=60, equipment_id=None, is_enabled=True,
    )

    alerts = await DashboardService.evaluate_alerts(session, [rule])

    assert len(alerts) == 1
    assert alerts[0]["observed_value"] > 100_000
    assert alerts[0]["window_start"] == started
    assert "down since 2026-06-01 08:00 UTC" in alerts[0]["message"]

    result.scalars.return_value.all.return_value = []
    assert await DashboardService.evaluate_alerts(session, [rule]) == []


@pytest.mark.asyncio
async def test_loss_breakdown_groups_downtime_and_counter_losses():
    from mes.core.dashboard.service import DashboardService

    now = datetime.now(timezone.utc)
    order_id = uuid4()
    state_log = SimpleNamespace(
        started_at=now - timedelta(minutes=10),
        ended_at=now,
        oee_bucket="downtime_unplanned",
        reason_code="1001",
    )
    state_result = Mock()
    state_result.all.return_value = [(state_log, "Machine fault")]
    counter_result = Mock()
    counter_result.all.return_value = [
        SimpleNamespace(
            shift_date=now.date(),
            order_id=order_id,
            order_number="ORDER-1",
            created_at=now,
            good=10,
            reject=2,
            rework=1,
        ),
    ]
    session = AsyncMock()
    session.execute.side_effect = [state_result, counter_result]

    breakdown = await DashboardService.loss_breakdown(session, days=7)

    assert breakdown["source"] == "counters"
    assert breakdown["by_reason"] == [{
        "reason_code": "1001",
        "reason_name": "Machine fault",
        "loss_type": "downtime_unplanned",
        "minutes": pytest.approx(10, abs=1),
    }]
    assert breakdown["by_order"][0]["order_id"] == str(order_id)
    assert breakdown["by_order"][0]["reject"] == 2
    assert breakdown["by_shift_date"][0]["good"] == 10


@pytest.mark.asyncio
async def test_loss_breakdown_falls_back_to_wip_when_no_counters():
    from mes.core.dashboard.service import DashboardService

    now = datetime.now(timezone.utc)
    order_id = uuid4()

    def make(rows):
        r = Mock()
        r.all.return_value = rows
        return r

    session = AsyncMock()
    session.execute.side_effect = [
        make([]),  # downtime state logs
        make([]),  # counters
        make([(now, order_id), (now, order_id)]),  # completed units
        make([(now, order_id)]),  # scrapped units
        make([]),  # rework
        make([(order_id, "ORDER-9", now)]),  # order numbers
    ]

    breakdown = await DashboardService.loss_breakdown(session, days=7)

    assert breakdown["source"] == "wip"
    assert breakdown["by_order"][0]["order_number"] == "ORDER-9"
    assert breakdown["by_order"][0]["created_at"] == now.isoformat()
    assert breakdown["by_order"][0]["good"] == 2
    assert breakdown["by_order"][0]["reject"] == 1
    assert breakdown["by_shift_date"][0]["good"] == 2
