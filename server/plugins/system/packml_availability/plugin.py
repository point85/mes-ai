"""
PackML (ISA-TR88) Equipment State Model Plugin.

Registers the 17-state PackML state machine for equipment availability
tracking.  Each state maps to a canonical dispatch_category and oee_bucket
used by the OEE calculation engine.

Reference: ISA-TR88.00.02 — Machine and Unit States
"""

from __future__ import annotations

import logging
from typing import Any

from mes.framework.db import async_session_factory
from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.packml_availability")

MODEL_ID = "packml"
MODEL_NAME = "PackML (ISA-TR88)"
MODEL_DESCRIPTION = (
    "ISA-TR88 / PackML state model. 17 states organised around the "
    "Execute production cycle with Hold, Suspend, Stop and Abort branches."
)

INITIAL_STATE = "Stopped"

# ── State definitions ──────────────────────────────────────────────
# Each state carries a canonical dispatch_category and oee_bucket so the
# OEE engine can classify time without any knowledge of the underlying
# state-machine semantics.

STATES: list[dict[str, str]] = [
    # Wait states
    {"name": "Stopped",     "dispatch_category": "unavailable_planned",   "oee_bucket": "downtime_planned"},
    {"name": "Idle",        "dispatch_category": "available",             "oee_bucket": "uptime_non_value"},
    {"name": "Complete",    "dispatch_category": "available",             "oee_bucket": "uptime_non_value"},
    {"name": "Held",        "dispatch_category": "unavailable_unplanned", "oee_bucket": "downtime_unplanned"},
    {"name": "Suspended",   "dispatch_category": "unavailable_planned",   "oee_bucket": "downtime_planned"},
    {"name": "Aborted",     "dispatch_category": "unavailable_unplanned", "oee_bucket": "downtime_unplanned"},
    # Acting states — production path
    {"name": "Resetting",   "dispatch_category": "busy",                  "oee_bucket": "uptime_non_value"},
    {"name": "Starting",    "dispatch_category": "busy",                  "oee_bucket": "uptime_value_add"},
    {"name": "Execute",     "dispatch_category": "busy",                  "oee_bucket": "uptime_value_add"},
    {"name": "Completing",  "dispatch_category": "busy",                  "oee_bucket": "uptime_value_add"},
    # Acting states — hold branch
    {"name": "Holding",     "dispatch_category": "busy",                  "oee_bucket": "downtime_unplanned"},
    {"name": "Unholding",   "dispatch_category": "busy",                  "oee_bucket": "downtime_unplanned"},
    # Acting states — suspend branch
    {"name": "Suspending",  "dispatch_category": "busy",                  "oee_bucket": "downtime_planned"},
    {"name": "Unsuspending","dispatch_category": "busy",                  "oee_bucket": "downtime_planned"},
    # Acting states — stop branch
    {"name": "Stopping",    "dispatch_category": "busy",                  "oee_bucket": "downtime_planned"},
    # Acting states — abort branch
    {"name": "Aborting",    "dispatch_category": "busy",                  "oee_bucket": "downtime_unplanned"},
    {"name": "Clearing",    "dispatch_category": "busy",                  "oee_bucket": "downtime_unplanned"},
]

# ── Transition definitions ─────────────────────────────────────────
# Normal production cycle
_PRODUCTION = [
    {"from_state": "Stopped",      "to_state": "Resetting"},
    {"from_state": "Resetting",    "to_state": "Idle"},
    {"from_state": "Idle",         "to_state": "Starting"},
    {"from_state": "Starting",     "to_state": "Execute"},
    {"from_state": "Execute",      "to_state": "Completing"},
    {"from_state": "Completing",   "to_state": "Complete"},
    {"from_state": "Complete",     "to_state": "Resetting"},
]

# Hold branch
_HOLD = [
    {"from_state": "Execute",   "to_state": "Holding"},
    {"from_state": "Holding",   "to_state": "Held"},
    {"from_state": "Held",      "to_state": "Unholding"},
    {"from_state": "Unholding", "to_state": "Execute"},
]

# Suspend branch
_SUSPEND = [
    {"from_state": "Execute",      "to_state": "Suspending"},
    {"from_state": "Suspending",   "to_state": "Suspended"},
    {"from_state": "Suspended",    "to_state": "Unsuspending"},
    {"from_state": "Unsuspending", "to_state": "Execute"},
]

# Stop — accessible from most states
_STOPPABLE = [
    "Idle", "Starting", "Execute", "Completing", "Complete",
    "Resetting", "Holding", "Held", "Unholding",
    "Suspending", "Suspended", "Unsuspending",
]
_STOP = [
    {"from_state": s, "to_state": "Stopping"} for s in _STOPPABLE
] + [
    {"from_state": "Stopping", "to_state": "Stopped"},
]

# Abort — accessible from all except Aborting, Aborted, Clearing
_ABORTABLE = [
    "Stopped", "Idle", "Starting", "Execute", "Completing", "Complete",
    "Resetting", "Holding", "Held", "Unholding",
    "Suspending", "Suspended", "Unsuspending",
    "Stopping",
]
_ABORT = [
    {"from_state": s, "to_state": "Aborting"} for s in _ABORTABLE
] + [
    {"from_state": "Aborting", "to_state": "Aborted"},
    {"from_state": "Aborted",  "to_state": "Clearing"},
    {"from_state": "Clearing", "to_state": "Stopped"},
]

TRANSITIONS: list[dict[str, str]] = _PRODUCTION + _HOLD + _SUSPEND + _STOP + _ABORT


# ── Plugin class ───────────────────────────────────────────────────

class PackMLAvailabilityPlugin(MESPlugin):
    """Registers the PackML (ISA-TR88) state model at startup."""

    async def initialize(self, config: dict[str, Any]) -> None:
        logger.info("PackML availability plugin initialising …")

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
        logger.info("PackML state model registered (model_id=%s)", MODEL_ID)

    async def stop(self) -> None:
        pass
