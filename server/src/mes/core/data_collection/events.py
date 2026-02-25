"""
DATA-COLLECT: Event definitions for the Data Collection domain.
"""

from mes.framework.events import MESEvent


def data_collected(
    definition_id: str, unit_id: str | None, value: str | float | bool | None,
) -> MESEvent:
    """Create an event when a data point is collected."""
    return MESEvent(
        event_type="data.collected",
        source="data_collection",
        payload={
            "definition_id": definition_id,
            "unit_id": unit_id,
            "value": value,
        },
    )


def data_definition_created(definition_id: str, code: str, data_type: str) -> MESEvent:
    """Create an event when a new data definition is created."""
    return MESEvent(
        event_type="data.definition.created",
        source="data_collection",
        payload={
            "definition_id": definition_id,
            "code": code,
            "data_type": data_type,
        },
    )
