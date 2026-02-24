"""
Unit tests for EVENT-BUS module.

Tests cover:
- Event schema creation and serialization
- Event publishing and subscription
- Wildcard topic matching
- Handler error isolation
- Decorator-based handler registration
"""

from __future__ import annotations

import asyncio

import pytest

from mes.framework.events import EventBus, MESEvent, event_handler
from mes.framework.events.bus import EventBus as EventBusClass
from mes.framework.events.decorators import clear_handler_registry, get_registered_handlers


# --- MESEvent schema tests ---


class TestMESEvent:
    def test_event_creation_with_defaults(self):
        event = MESEvent(event_type="wip.unit.moved", source="WIP-TRACK")
        assert event.event_type == "wip.unit.moved"
        assert event.source == "WIP-TRACK"
        assert event.event_id  # UUID auto-generated
        assert event.timestamp  # UTC timestamp auto-generated
        assert event.correlation_id  # UUID auto-generated
        assert event.payload == {}

    def test_event_creation_with_payload(self):
        event = MESEvent(
            event_type="wip.unit.moved",
            source="WIP-TRACK",
            payload={"unit_id": "abc123", "from_step": "step1", "to_step": "step2"},
        )
        assert event.payload["unit_id"] == "abc123"

    def test_event_serialization(self):
        event = MESEvent(event_type="quality.test.passed", source="QUAL-MGMT")
        data = event.model_dump()
        assert "event_id" in data
        assert data["event_type"] == "quality.test.passed"
        assert data["source"] == "QUAL-MGMT"


# --- EventBus tests ---


class TestEventBus:
    @pytest.fixture(autouse=True)
    def bus(self):
        """Create a fresh event bus for each test."""
        self.bus = EventBusClass()

    @pytest.mark.asyncio
    async def test_exact_topic_subscription(self):
        received = []

        async def handler(event: MESEvent):
            received.append(event)

        self.bus.subscribe("wip.unit.moved", handler)
        await self.bus.publish(MESEvent(event_type="wip.unit.moved", source="test"))

        assert len(received) == 1
        assert received[0].event_type == "wip.unit.moved"

    @pytest.mark.asyncio
    async def test_no_match_no_delivery(self):
        received = []

        async def handler(event: MESEvent):
            received.append(event)

        self.bus.subscribe("wip.unit.moved", handler)
        await self.bus.publish(MESEvent(event_type="quality.test.passed", source="test"))

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_wildcard_star_at_end(self):
        """'wip.unit.*' should match 'wip.unit.moved', 'wip.unit.created', etc."""
        received = []

        async def handler(event: MESEvent):
            received.append(event)

        self.bus.subscribe("wip.unit.*", handler)
        await self.bus.publish(MESEvent(event_type="wip.unit.moved", source="test"))
        await self.bus.publish(MESEvent(event_type="wip.unit.created", source="test"))
        await self.bus.publish(MESEvent(event_type="wip.lot.moved", source="test"))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_wildcard_deep_match(self):
        """'wip.*' should match 'wip.unit.moved', 'wip.lot.created', etc."""
        received = []

        async def handler(event: MESEvent):
            received.append(event)

        self.bus.subscribe("wip.*", handler)
        await self.bus.publish(MESEvent(event_type="wip.unit.moved", source="test"))
        await self.bus.publish(MESEvent(event_type="wip.lot.created", source="test"))
        await self.bus.publish(MESEvent(event_type="quality.test.passed", source="test"))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_global_wildcard(self):
        """'*' should match all events."""
        received = []

        async def handler(event: MESEvent):
            received.append(event)

        self.bus.subscribe("*", handler)
        await self.bus.publish(MESEvent(event_type="wip.unit.moved", source="test"))
        await self.bus.publish(MESEvent(event_type="quality.test.passed", source="test"))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        received_a = []
        received_b = []

        async def handler_a(event: MESEvent):
            received_a.append(event)

        async def handler_b(event: MESEvent):
            received_b.append(event)

        self.bus.subscribe("wip.unit.moved", handler_a)
        self.bus.subscribe("wip.unit.moved", handler_b)
        await self.bus.publish(MESEvent(event_type="wip.unit.moved", source="test"))

        assert len(received_a) == 1
        assert len(received_b) == 1

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self):
        """A failing handler should not prevent other handlers from running."""
        received = []

        async def bad_handler(event: MESEvent):
            raise ValueError("Handler error")

        async def good_handler(event: MESEvent):
            received.append(event)

        self.bus.subscribe("test.event", bad_handler)
        self.bus.subscribe("test.event", good_handler)

        # Should not raise — errors are isolated
        await self.bus.publish(MESEvent(event_type="test.event", source="test"))

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        received = []

        async def handler(event: MESEvent):
            received.append(event)

        self.bus.subscribe("test.event", handler)
        self.bus.unsubscribe("test.event", handler)
        await self.bus.publish(MESEvent(event_type="test.event", source="test"))

        assert len(received) == 0

    def test_subscription_count(self):
        async def handler(event: MESEvent):
            pass

        self.bus.subscribe("topic.a", handler)
        self.bus.subscribe("topic.b", handler)
        assert self.bus.subscription_count == 2

    def test_clear(self):
        async def handler(event: MESEvent):
            pass

        self.bus.subscribe("topic.a", handler)
        self.bus.clear()
        assert self.bus.subscription_count == 0


# --- Decorator tests ---


class TestEventHandlerDecorator:
    @pytest.fixture(autouse=True)
    def clean_registry(self):
        clear_handler_registry()
        yield
        clear_handler_registry()

    def test_decorator_registers_handler(self):
        @event_handler("wip.unit.completed")
        async def on_completed(event: MESEvent):
            pass

        handlers = get_registered_handlers()
        assert len(handlers) == 1
        assert handlers[0][0] == "wip.unit.completed"
        assert handlers[0][1] is on_completed

    def test_multiple_decorators(self):
        @event_handler("wip.unit.completed")
        async def handler_a(event: MESEvent):
            pass

        @event_handler("quality.*")
        async def handler_b(event: MESEvent):
            pass

        handlers = get_registered_handlers()
        assert len(handlers) == 2
