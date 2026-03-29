"""
SEMI E10-0304 Equipment State Model Plugin.

Registers the six-state SEMI E10 state machine for equipment availability
tracking.  SEMI E10 is widely used in semiconductor and high-tech
manufacturing to classify equipment time into standard categories.

Reference: SEMI E10-0304 — Specification for Definition and Measurement
of Equipment Reliability, Availability, and Maintainability (RAM)
"""

from __future__ import annotations

import logging
from typing import Any

from mes.framework.db import async_session_factory
from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.semi_e10_availability")

MODEL_ID = "semi_e10"
MODEL_NAME = "SEMI E10-0304"
MODEL_DESCRIPTION = (
    "SEMI E10 equipment state model. Six high-level states that classify "
    "equipment time into Productive, Standby, Engineering, Scheduled "
    "Downtime, Unscheduled Downtime, and Non-Scheduled categories."
)

INITIAL_STATE = "Standby"

# ── State definitions ──────────────────────────────────────────────
# SEMI E10 defines six top-level equipment states.  Each maps to a
# canonical dispatch_category and oee_bucket for OEE calculation.

STATES: list[dict[str, str]] = [
    {
        "name": "Productive",
        "dispatch_category": "busy",
        "oee_bucket": "uptime_value_add",
    },
    {
        "name": "Standby",
        "dispatch_category": "available",
        "oee_bucket": "uptime_non_value",
    },
    {
        "name": "Engineering",
        "dispatch_category": "busy",
        "oee_bucket": "uptime_non_value",
    },
    {
        "name": "Scheduled Downtime",
        "dispatch_category": "unavailable_planned",
        "oee_bucket": "downtime_planned",
    },
    {
        "name": "Unscheduled Downtime",
        "dispatch_category": "unavailable_unplanned",
        "oee_bucket": "downtime_unplanned",
    },
    {
        "name": "Non-Scheduled",
        "dispatch_category": "unavailable_planned",
        "oee_bucket": "excluded",
    },
]

# ── Transition definitions ─────────────────────────────────────────
# SEMI E10 allows free transitions between all six states — the standard
# does not prescribe a directed graph.  Transitions are event-driven by
# operator actions or automated signals.

_STATE_NAMES = [s["name"] for s in STATES]

TRANSITIONS: list[dict[str, str]] = [
    {"from_state": src, "to_state": dst}
    for src in _STATE_NAMES
    for dst in _STATE_NAMES
    if src != dst
]


# ── Plugin class ───────────────────────────────────────────────────

class SEMIE10AvailabilityPlugin(MESPlugin):
    """Registers the SEMI E10-0304 state model at startup."""

    async def initialize(self, config: dict[str, Any]) -> None:
        logger.info("SEMI E10 availability plugin initialising …")

    async def start(self) -> None:
        from mes.core.performance.engine import EquipmentStateEngine

        async with async_session_factory() as session:
            await EquipmentStateEngine.register_state_model(
                session,
                model_id=MODEL_ID,
                name=MODEL_NAME,
                description=MODEL_DESCRIPTION,
                initial_state=INITIAL_STATE,
                states=STATES,
                transitions=TRANSITIONS,
            )
            await session.commit()
        logger.info("SEMI E10 state model registered (model_id=%s)", MODEL_ID)

    async def stop(self) -> None:
        pass
