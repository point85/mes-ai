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


def production_counter_updated(
    equipment_id: str,
    good_delta: int = 0,
    reject_delta: int = 0,
    rework_delta: int = 0,
    source_plugin: str = "manual",
) -> MESEvent:
    """Create an event when production counters are incremented."""
    return MESEvent(
        event_type="production.counter.updated",
        source="performance",
        payload={
            "equipment_id": equipment_id,
            "good_delta": good_delta,
            "reject_delta": reject_delta,
            "rework_delta": rework_delta,
            "source_plugin": source_plugin,
        },
    )
