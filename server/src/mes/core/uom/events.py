"""
UOM: Event definitions for the Unit of Measure domain.
"""

from mes.framework.events import MESEvent


def uom_created(uom_id: str, symbol: str, uom_type: str) -> MESEvent:
    """Create an event when a new unit of measure is defined."""
    return MESEvent(
        event_type="uom.created",
        source="uom",
        payload={"uom_id": uom_id, "symbol": symbol, "uom_type": uom_type},
    )


def uom_updated(uom_id: str, symbol: str) -> MESEvent:
    """Create an event when a unit of measure is updated."""
    return MESEvent(
        event_type="uom.updated",
        source="uom",
        payload={"uom_id": uom_id, "symbol": symbol},
    )


def uom_deleted(uom_id: str, symbol: str) -> MESEvent:
    """Create an event when a unit of measure is soft-deleted."""
    return MESEvent(
        event_type="uom.deleted",
        source="uom",
        payload={"uom_id": uom_id, "symbol": symbol},
    )
