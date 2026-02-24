"""
PHYS-MODEL: Event definitions for the physical model domain.

Events emitted when physical-model entities are created, updated, or change state.
"""

from mes.framework.events import MESEvent


def equipment_status_changed(
    equipment_id: str,
    old_status: str,
    new_status: str,
    reason: str | None = None,
) -> MESEvent:
    """Create an event for equipment status change."""
    return MESEvent(
        event_type="equipment.state.changed",
        source="physical_model",
        payload={
            "equipment_id": equipment_id,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
        },
    )


def site_created(site_id: str, code: str) -> MESEvent:
    """Create an event for new site creation."""
    return MESEvent(
        event_type="physical_model.site.created",
        source="physical_model",
        payload={"site_id": site_id, "code": code},
    )


def equipment_created(equipment_id: str, code: str, work_center_id: str) -> MESEvent:
    """Create an event for new equipment creation."""
    return MESEvent(
        event_type="physical_model.equipment.created",
        source="physical_model",
        payload={
            "equipment_id": equipment_id,
            "code": code,
            "work_center_id": work_center_id,
        },
    )
