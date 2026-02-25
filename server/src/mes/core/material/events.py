"""
MAT-MGMT: Event definitions for the Material Management domain.
"""

from mes.framework.events import MESEvent


def material_consumed(
    material_lot_id: str, unit_id: str | None, quantity: float,
) -> MESEvent:
    """Create an event when material is consumed by a WIP unit or lot."""
    return MESEvent(
        event_type="material.consumed",
        source="material",
        payload={
            "material_lot_id": material_lot_id,
            "unit_id": unit_id,
            "quantity": quantity,
        },
    )


def material_lot_created(
    material_lot_id: str, material_id: str, lot_number: str, quantity: float,
) -> MESEvent:
    """Create an event when a new material lot is received into inventory."""
    return MESEvent(
        event_type="material.lot.created",
        source="material",
        payload={
            "material_lot_id": material_lot_id,
            "material_id": material_id,
            "lot_number": lot_number,
            "quantity": quantity,
        },
    )


def material_lot_expired(material_lot_id: str, lot_number: str) -> MESEvent:
    """Create an event when a material lot reaches its expiry date."""
    return MESEvent(
        event_type="material.lot.expired",
        source="material",
        payload={
            "material_lot_id": material_lot_id,
            "lot_number": lot_number,
        },
    )
