"""
PROD-DEF: Event definitions for the product definition domain.
"""

from mes.framework.events import MESEvent


def product_created(product_id: str, code: str, version: str) -> MESEvent:
    """Create an event for new product definition creation."""
    return MESEvent(
        event_type="product_def.product.created",
        source="product_def",
        payload={"product_id": product_id, "code": code, "version": version},
    )


def route_created(route_id: str, product_id: str, name: str) -> MESEvent:
    """Create an event for new process route creation."""
    return MESEvent(
        event_type="product_def.route.created",
        source="product_def",
        payload={"route_id": route_id, "product_id": product_id, "name": name},
    )


def bom_created(bom_id: str, product_id: str, version: str) -> MESEvent:
    """Create an event for new BOM creation."""
    return MESEvent(
        event_type="product_def.bom.created",
        source="product_def",
        payload={"bom_id": bom_id, "product_id": product_id, "version": version},
    )
