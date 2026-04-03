"""
WIP-TRACK: Event definitions for the work-in-process tracking domain.
"""

from mes.framework.events import MESEvent


# ── Unit events ──────────────────────────────────────────────────────


def unit_created(unit_id: str, order_id: str, serial_number: str) -> MESEvent:
    return MESEvent(
        event_type="wip.unit.created",
        source="wip",
        payload={
            "unit_id": unit_id,
            "order_id": order_id,
            "serial_number": serial_number,
        },
    )


def unit_started(unit_id: str, step_id: str, equipment_id: str | None) -> MESEvent:
    return MESEvent(
        event_type="wip.unit.started",
        source="wip",
        payload={
            "unit_id": unit_id,
            "step_id": step_id,
            "equipment_id": equipment_id,
        },
    )


def unit_completed(unit_id: str, step_id: str, result: str) -> MESEvent:
    return MESEvent(
        event_type="wip.unit.completed",
        source="wip",
        payload={
            "unit_id": unit_id,
            "step_id": step_id,
            "result": result,
        },
    )


def unit_moved(unit_id: str, from_step_id: str | None, to_step_id: str | None) -> MESEvent:
    return MESEvent(
        event_type="wip.unit.moved",
        source="wip",
        payload={
            "unit_id": unit_id,
            "from_step_id": from_step_id,
            "to_step_id": to_step_id,
        },
    )


def unit_scrapped(unit_id: str, step_id: str | None, reason: str) -> MESEvent:
    return MESEvent(
        event_type="wip.unit.scrapped",
        source="wip",
        payload={
            "unit_id": unit_id,
            "step_id": step_id,
            "reason": reason,
        },
    )


def unit_held(unit_id: str, reason: str) -> MESEvent:
    return MESEvent(
        event_type="wip.unit.held",
        source="wip",
        payload={
            "unit_id": unit_id,
            "reason": reason,
        },
    )


def unit_released(unit_id: str) -> MESEvent:
    return MESEvent(
        event_type="wip.unit.released",
        source="wip",
        payload={"unit_id": unit_id},
    )


# ── Lot events ───────────────────────────────────────────────────────


def lot_created(lot_id: str, order_id: str, lot_number: str, quantity: int) -> MESEvent:
    return MESEvent(
        event_type="wip.lot.created",
        source="wip",
        payload={
            "lot_id": lot_id,
            "order_id": order_id,
            "lot_number": lot_number,
            "quantity": quantity,
        },
    )


def lot_started(lot_id: str, step_id: str, equipment_id: str | None) -> MESEvent:
    return MESEvent(
        event_type="wip.lot.started",
        source="wip",
        payload={
            "lot_id": lot_id,
            "step_id": step_id,
            "equipment_id": equipment_id,
        },
    )


def lot_completed(
    lot_id: str, step_id: str, quantity_out: int, quantity_scrapped: int,
) -> MESEvent:
    return MESEvent(
        event_type="wip.lot.completed",
        source="wip",
        payload={
            "lot_id": lot_id,
            "step_id": step_id,
            "quantity_out": quantity_out,
            "quantity_scrapped": quantity_scrapped,
        },
    )


def lot_moved(lot_id: str, from_step_id: str | None, to_step_id: str | None) -> MESEvent:
    return MESEvent(
        event_type="wip.lot.moved",
        source="wip",
        payload={
            "lot_id": lot_id,
            "from_step_id": from_step_id,
            "to_step_id": to_step_id,
        },
    )


def lot_held(lot_id: str, reason: str) -> MESEvent:
    return MESEvent(
        event_type="wip.lot.held",
        source="wip",
        payload={
            "lot_id": lot_id,
            "reason": reason,
        },
    )


def lot_released(lot_id: str) -> MESEvent:
    return MESEvent(
        event_type="wip.lot.released",
        source="wip",
        payload={"lot_id": lot_id},
    )


def lot_scrapped(lot_id: str, step_id: str | None, reason: str, quantity: int) -> MESEvent:
    return MESEvent(
        event_type="wip.lot.scrapped",
        source="wip",
        payload={
            "lot_id": lot_id,
            "step_id": step_id,
            "reason": reason,
            "quantity": quantity,
        },
    )
