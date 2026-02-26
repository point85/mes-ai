"""
DISPATCH: Event definitions for the Dispatching Engine.
"""

from mes.framework.events import MESEvent


def dispatch_evaluated(
    unit_id: str | None, strategy: str, recommendation: str | None,
) -> MESEvent:
    """Create an event when dispatch is evaluated."""
    return MESEvent(
        event_type="dispatch.evaluated",
        source="dispatch",
        payload={
            "unit_id": unit_id,
            "strategy": strategy,
            "recommendation": recommendation,
        },
    )


def dispatch_executed(
    unit_id: str | None, destination_step_id: str,
) -> MESEvent:
    """Create an event when dispatch is executed."""
    return MESEvent(
        event_type="dispatch.executed",
        source="dispatch",
        payload={
            "unit_id": unit_id,
            "destination_step_id": destination_step_id,
        },
    )
