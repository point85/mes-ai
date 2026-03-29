"""
PERF-ANALYSIS: Equipment state machine engine.

Provides transition validation, canonical mapping, and state model
registration for equipment availability plugins.

When no state model is assigned to an equipment, the equipment is
assumed to be running with 100 % availability.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException

from .exceptions import InvalidStateTransitionException
from .models import EquipmentStateLog, EquipmentStateModel
from .service import EquipmentStateService

logger = logging.getLogger("mes.performance.engine")

# Default canonical mappings when no state model is configured
DEFAULT_STATE = "running"
DEFAULT_DISPATCH_CATEGORY = "available"
DEFAULT_OEE_BUCKET = "uptime_value_add"


class EquipmentStateEngine:
    """
    Core engine for equipment state machine management.

    Responsibilities:
    - Register / update state model definitions (called by plugins at startup)
    - Validate state transitions against the assigned model
    - Map plugin-specific states to canonical dispatch_category + oee_bucket
    - Record state changes through EquipmentStateService
    """

    # ─── State Model Registration ────────────────────────────────────

    @staticmethod
    async def register_state_model(
        session: AsyncSession,
        model_id: str,
        name: str,
        description: str,
        initial_state: str,
        states: list[dict[str, str]],
        transitions: list[dict[str, str]],
    ) -> EquipmentStateModel:
        """
        Register or update a state model definition.

        Called by availability plugins during ``initialize()``.
        Idempotent — if model_id already exists the definition is updated.
        """
        stmt = select(EquipmentStateModel).where(
            EquipmentStateModel.model_id == model_id,
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = EquipmentStateModel(
                model_id=model_id,
                name=name,
                description=description,
                initial_state=initial_state,
                states=states,
                transitions=transitions,
            )
            session.add(model)
            logger.info("Registered new state model: %s (%s)", model_id, name)
        else:
            model.name = name
            model.description = description
            model.initial_state = initial_state
            model.states = states
            model.transitions = transitions
            logger.info("Updated state model: %s (%s)", model_id, name)

        await session.flush()
        return model

    # ─── State Model Queries ─────────────────────────────────────────

    @staticmethod
    async def get_state_model(
        session: AsyncSession, model_id: str,
    ) -> EquipmentStateModel:
        """Look up a state model by its plugin identifier."""
        stmt = select(EquipmentStateModel).where(
            EquipmentStateModel.model_id == model_id,
            EquipmentStateModel.is_active.is_(True),
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise NotFoundException(
                resource="EquipmentStateModel", resource_id=model_id,
            )
        return model

    @staticmethod
    async def list_state_models(
        session: AsyncSession,
    ) -> list[EquipmentStateModel]:
        """Return all active state model definitions."""
        stmt = (
            select(EquipmentStateModel)
            .where(EquipmentStateModel.is_active.is_(True))
            .order_by(EquipmentStateModel.name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ─── Transition Logic ────────────────────────────────────────────

    @staticmethod
    def _find_state_def(
        states: list[dict[str, str]], state_name: str,
    ) -> dict[str, str] | None:
        """Find a state definition by name in the states list."""
        for s in states:
            if s["name"] == state_name:
                return s
        return None

    @staticmethod
    def _is_transition_valid(
        transitions: list[dict[str, str]],
        from_state: str,
        to_state: str,
    ) -> bool:
        """Check whether a transition from→to is allowed."""
        return any(
            t["from_state"] == from_state and t["to_state"] == to_state
            for t in transitions
        )

    @staticmethod
    def get_valid_next_states(
        transitions: list[dict[str, str]], current_state: str,
    ) -> list[dict[str, str]]:
        """Return the list of valid transitions from the current state."""
        return [t for t in transitions if t["from_state"] == current_state]

    @staticmethod
    async def transition_equipment(
        session: AsyncSession,
        equipment_id: UUID,
        new_state: str,
        reason_code: str | None = None,
        notes: str | None = None,
        *,
        state_model_id: str | None = None,
    ) -> EquipmentStateLog:
        """
        Transition equipment to a new state.

        1. Look up the equipment's assigned state model
        2. Determine the current state (from latest open log)
        3. Validate the transition
        4. Map the new state to canonical categories
        5. Record the state change

        If *state_model_id* is provided it overrides the equipment's configured model.
        """
        from mes.core.physical_model.models import Equipment

        # Fetch equipment
        eq_stmt = select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.is_active.is_(True),
        )
        result = await session.execute(eq_stmt)
        equipment = result.scalar_one_or_none()
        if equipment is None:
            raise NotFoundException(
                resource="Equipment", resource_id=str(equipment_id),
            )

        model_id = state_model_id or equipment.state_model_id

        # No state model → default mapping (100 % available)
        if model_id is None:
            return await EquipmentStateService.record_state_change(
                session,
                equipment_id=equipment_id,
                state_model="default",
                state=new_state or DEFAULT_STATE,
                sub_state=None,
                dispatch_category=DEFAULT_DISPATCH_CATEGORY,
                oee_bucket=DEFAULT_OEE_BUCKET,
                started_at=datetime.now(timezone.utc),
                reason_code=reason_code,
                notes=notes,
            )

        # Load state model
        model = await EquipmentStateEngine.get_state_model(session, model_id)
        states: list[dict[str, str]] = model.states  # type: ignore[assignment]
        transitions: list[dict[str, str]] = model.transitions  # type: ignore[assignment]

        # Validate new_state exists in model
        state_def = EquipmentStateEngine._find_state_def(states, new_state)
        if state_def is None:
            raise InvalidStateTransitionException(
                f"State '{new_state}' is not defined in model '{model_id}'",
            )

        # Get current state
        current_log = await EquipmentStateService.get_current_state(
            session, equipment_id,
        )
        current_state = current_log.state if current_log else None

        # If there is a current state, validate the transition
        if current_state is not None:
            if not EquipmentStateEngine._is_transition_valid(
                transitions, current_state, new_state,
            ):
                raise InvalidStateTransitionException(
                    f"Transition '{current_state}' → '{new_state}' is not allowed "
                    f"in model '{model_id}'",
                )

        # Record the change with canonical mappings
        return await EquipmentStateService.record_state_change(
            session,
            equipment_id=equipment_id,
            state_model=model_id,
            state=new_state,
            sub_state=state_def.get("sub_state"),
            dispatch_category=state_def["dispatch_category"],
            oee_bucket=state_def["oee_bucket"],
            started_at=datetime.now(timezone.utc),
            reason_code=reason_code,
            notes=notes,
        )
