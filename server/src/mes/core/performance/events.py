"""
PERF-ANALYSIS: Event definitions for the Performance Analysis domain.
"""

from mes.framework.events import MESEvent


def equipment_state_changed(
    equipment_id: str, state: str, dispatch_category: str,
) -> MESEvent:
    """Create an event when equipment changes state."""
    return MESEvent(
        event_type="equipment.state.changed",
        source="performance",
        payload={
            "equipment_id": equipment_id,
            "state": state,
            "dispatch_category": dispatch_category,
        },
    )


def oee_calculated(
    equipment_id: str, oee: float,
) -> MESEvent:
    """Create an event when OEE is calculated."""
    return MESEvent(
        event_type="performance.oee.calculated",
        source="performance",
        payload={
            "equipment_id": equipment_id,
            "oee": oee,
        },
    )
