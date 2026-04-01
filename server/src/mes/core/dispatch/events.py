"""
DISPATCH: Event definitions for the Dispatching Engine.
"""

from mes.framework.events import MESEvent


def dispatch_evaluated(
    unit_id: str | None,
    strategy: str,
    recommendation: str | None,
    lot_id: str | None = None,
) -> MESEvent:
    """Create an event when dispatch is evaluated."""
    return MESEvent(
        event_type="dispatch.evaluated",
        source="dispatch",
        payload={
            "unit_id": unit_id,
            "lot_id": lot_id,
            "strategy": strategy,
            "recommendation": recommendation,
        },
    )


def dispatch_executed(
    unit_id: str | None,
    destination_step_id: str,
    lot_id: str | None = None,
    destination_equipment_id: str | None = None,
) -> MESEvent:
    """Create an event when dispatch is executed."""
    return MESEvent(
        event_type="dispatch.executed",
        source="dispatch",
        payload={
            "unit_id": unit_id,
            "lot_id": lot_id,
            "destination_step_id": destination_step_id,
            "destination_equipment_id": destination_equipment_id,
        },
    )


def dispatch_blocked(
    unit_id: str | None = None,
    lot_id: str | None = None,
    reason: str = "",
) -> MESEvent:
    """Create an event when a unit/lot cannot be dispatched (all queues full or no capable equipment)."""
    return MESEvent(
        event_type="dispatch.blocked",
        source="dispatch",
        payload={
            "unit_id": unit_id,
            "lot_id": lot_id,
            "reason": reason,
        },
    )


def equipment_starved(equipment_id: str) -> MESEvent:
    """Create an event when an available equipment has an empty queue (starved)."""
    return MESEvent(
        event_type="dispatch.equipment.starved",
        source="dispatch",
        payload={"equipment_id": equipment_id},
    )
