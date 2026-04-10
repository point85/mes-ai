"""
INVENTORY: Event definitions for the Inventory Management domain.
"""

from mes.framework.events import MESEvent


def inventory_received(
    material_lot_id: str, location_id: str, quantity: float,
) -> MESEvent:
    """Create an event when material is received into inventory."""
    return MESEvent(
        event_type="inventory.received",
        source="inventory",
        payload={
            "material_lot_id": material_lot_id,
            "location_id": location_id,
            "quantity": quantity,
        },
    )


def inventory_putaway(
    material_lot_id: str, from_location_id: str, to_location_id: str, quantity: float,
) -> MESEvent:
    """Create an event when material is put away to a storage location."""
    return MESEvent(
        event_type="inventory.putaway",
        source="inventory",
        payload={
            "material_lot_id": material_lot_id,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "quantity": quantity,
        },
    )


def inventory_picked(
    material_lot_id: str, from_location_id: str, to_location_id: str, quantity: float,
) -> MESEvent:
    """Create an event when material is picked from storage."""
    return MESEvent(
        event_type="inventory.picked",
        source="inventory",
        payload={
            "material_lot_id": material_lot_id,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "quantity": quantity,
        },
    )


def inventory_moved(
    material_lot_id: str, from_location_id: str, to_location_id: str, quantity: float,
) -> MESEvent:
    """Create an event when material is moved between locations."""
    return MESEvent(
        event_type="inventory.moved",
        source="inventory",
        payload={
            "material_lot_id": material_lot_id,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "quantity": quantity,
        },
    )


def inventory_consumed(
    material_lot_id: str, location_id: str, quantity: float,
) -> MESEvent:
    """Create an event when inventory is consumed by WIP."""
    return MESEvent(
        event_type="inventory.consumed",
        source="inventory",
        payload={
            "material_lot_id": material_lot_id,
            "location_id": location_id,
            "quantity": quantity,
        },
    )


def inventory_adjusted(
    material_lot_id: str, location_id: str, old_quantity: float, new_quantity: float,
) -> MESEvent:
    """Create an event when inventory is manually adjusted."""
    return MESEvent(
        event_type="inventory.adjusted",
        source="inventory",
        payload={
            "material_lot_id": material_lot_id,
            "location_id": location_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
        },
    )
