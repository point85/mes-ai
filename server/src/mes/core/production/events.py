"""
PROD-ORDER: Event definitions for the Production Order domain.
"""

from mes.framework.events import MESEvent


def order_created(order_id: str, order_number: str, product_id: str) -> MESEvent:
    """Create an event when a new production order is created."""
    return MESEvent(
        event_type="production.order.created",
        source="production",
        payload={
            "order_id": order_id,
            "order_number": order_number,
            "product_id": product_id,
        },
    )


def order_released(order_id: str, product_id: str, quantity: int) -> MESEvent:
    """Create an event when a production order is released for production."""
    return MESEvent(
        event_type="production.order.released",
        source="production",
        payload={
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
        },
    )


def order_started(order_id: str) -> MESEvent:
    """Create an event when a production order begins processing."""
    return MESEvent(
        event_type="production.order.started",
        source="production",
        payload={"order_id": order_id},
    )


def order_completed(order_id: str, quantity_completed: int) -> MESEvent:
    """Create an event when a production order is marked as completed."""
    return MESEvent(
        event_type="production.order.completed",
        source="production",
        payload={
            "order_id": order_id,
            "quantity_completed": quantity_completed,
        },
    )
