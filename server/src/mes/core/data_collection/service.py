"""
DATA-COLLECT: Business logic service for data collection.

Provides CRUD for data definitions, data-point collection (single and batch),
value validation against definition type/limits, and query operations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import data_collected, data_definition_created
from .exceptions import (
    DuplicateDefinitionCodeException,
    InvalidDataValueException,
    InvalidEnumValueException,
    ValueOutOfLimitsException,
)
from .models import DataDefinition, DataPoint

logger = logging.getLogger("mes.data_collection")


class DataDefinitionService:
    """Service class for data-definition CRUD."""

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_definitions(
        session: AsyncSession,
        params: PaginationParams,
        step_id: UUID | None = None,
        data_type: str | None = None,
        source: str | None = None,
    ) -> tuple[Sequence[DataDefinition], str | None, bool]:
        """List active data definitions with optional filters."""
        stmt = select(DataDefinition).where(
            DataDefinition.is_active.is_(True),
        )
        if step_id is not None:
            stmt = stmt.where(DataDefinition.step_id == step_id)
        if data_type is not None:
            stmt = stmt.where(DataDefinition.data_type == data_type)
        if source is not None:
            stmt = stmt.where(DataDefinition.source == source)
        return await paginate_query(session, stmt, DataDefinition, params)

    @staticmethod
    async def get_definition(
        session: AsyncSession, definition_id: UUID,
    ) -> DataDefinition:
        """Get a data definition by ID. Raises NotFoundException if missing."""
        stmt = select(DataDefinition).where(
            DataDefinition.id == definition_id,
            DataDefinition.is_active.is_(True),
        )
        result = await session.execute(stmt)
        defn = result.scalar_one_or_none()
        if defn is None:
            raise NotFoundException(
                resource="DataDefinition", resource_id=str(definition_id),
            )
        return defn

    # ─── Mutations ───────────────────────────────────────────────────

    @staticmethod
    async def create_definition(
        session: AsyncSession, **kwargs: Any,
    ) -> DataDefinition:
        """Create a new data definition. Raises DuplicateDefinitionCodeException if code exists."""
        existing = await session.execute(
            select(DataDefinition).where(
                DataDefinition.code == kwargs["code"],
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateDefinitionCodeException(kwargs["code"])

        defn = DataDefinition(**kwargs)
        session.add(defn)
        await session.flush()

        await event_bus.publish(
            data_definition_created(str(defn.id), defn.code, defn.data_type)
        )
        logger.info(
            "Created data definition %s (%s, type=%s)",
            defn.id, defn.code, defn.data_type,
        )
        return defn

    @staticmethod
    async def update_definition(
        session: AsyncSession, definition_id: UUID, **kwargs: Any,
    ) -> DataDefinition:
        """Update a data definition. Only non-None values are applied."""
        defn = await DataDefinitionService.get_definition(session, definition_id)

        # Check code uniqueness if changing
        new_code = kwargs.get("code")
        if new_code is not None and new_code != defn.code:
            existing = await session.execute(
                select(DataDefinition).where(
                    DataDefinition.code == new_code,
                    DataDefinition.id != definition_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateDefinitionCodeException(new_code)

        for key, value in kwargs.items():
            if value is not None:
                setattr(defn, key, value)
        await session.flush()

        logger.info("Updated data definition %s (%s)", defn.id, defn.code)
        return defn

    @staticmethod
    async def delete_definition(
        session: AsyncSession, definition_id: UUID,
    ) -> None:
        """Soft-delete a data definition."""
        defn = await DataDefinitionService.get_definition(session, definition_id)
        defn.is_active = False
        await session.flush()
        logger.info("Soft-deleted data definition %s (%s)", defn.id, defn.code)


class DataPointService:
    """Service class for collecting and querying data points."""

    # ─── Validation ──────────────────────────────────────────────────

    @staticmethod
    def _validate_value(
        defn: DataDefinition,
        *,
        value_numeric: float | None,
        value_string: str | None,
        value_boolean: bool | None,
    ) -> None:
        """
        Validate that the provided value matches the definition's data_type
        and respects limits/enum constraints.
        """
        dt = defn.data_type

        if dt == "numeric":
            if value_numeric is None:
                raise InvalidDataValueException(
                    defn.code, dt, "value_numeric is required for numeric type",
                )
            # Check limits
            if defn.lower_limit is not None and value_numeric < defn.lower_limit:
                raise ValueOutOfLimitsException(
                    defn.code, value_numeric, defn.lower_limit, defn.upper_limit,
                )
            if defn.upper_limit is not None and value_numeric > defn.upper_limit:
                raise ValueOutOfLimitsException(
                    defn.code, value_numeric, defn.lower_limit, defn.upper_limit,
                )

        elif dt == "string":
            if value_string is None:
                raise InvalidDataValueException(
                    defn.code, dt, "value_string is required for string type",
                )

        elif dt == "boolean":
            if value_boolean is None:
                raise InvalidDataValueException(
                    defn.code, dt, "value_boolean is required for boolean type",
                )

        elif dt == "enum":
            if value_string is None:
                raise InvalidDataValueException(
                    defn.code, dt, "value_string is required for enum type",
                )
            allowed = [
                v.strip() for v in (defn.enum_values or "").split(",") if v.strip()
            ]
            if allowed and value_string not in allowed:
                raise InvalidEnumValueException(defn.code, value_string, allowed)

    # ─── Collection ──────────────────────────────────────────────────

    @staticmethod
    async def collect(
        session: AsyncSession,
        defn: DataDefinition,
        *,
        unit_id: UUID | None = None,
        lot_id: UUID | None = None,
        value_numeric: float | None = None,
        value_string: str | None = None,
        value_boolean: bool | None = None,
        source_equipment_id: UUID | None = None,
        operator_id: UUID | None = None,
    ) -> DataPoint:
        """
        Collect a single data point.

        Validates the value against the definition, creates the record,
        and publishes a data.collected event.
        """
        DataPointService._validate_value(
            defn,
            value_numeric=value_numeric,
            value_string=value_string,
            value_boolean=value_boolean,
        )

        now = datetime.now(timezone.utc)
        point = DataPoint(
            definition_id=defn.id,
            unit_id=unit_id,
            lot_id=lot_id,
            value_numeric=value_numeric,
            value_string=value_string,
            value_boolean=value_boolean,
            collected_at=now,
            collected_at_utc=now,
            source_equipment_id=source_equipment_id,
            operator_id=operator_id,
        )
        session.add(point)
        await session.flush()

        # Determine the "value" for the event
        event_value = value_numeric if value_numeric is not None else (
            value_string if value_string is not None else value_boolean
        )
        await event_bus.publish(
            data_collected(
                str(defn.id),
                str(unit_id) if unit_id else None,
                event_value,
            )
        )
        logger.info(
            "Collected data point %s for definition %s (%s)",
            point.id, defn.id, defn.code,
        )
        return point

    @staticmethod
    async def collect_batch(
        session: AsyncSession,
        items: list[dict[str, Any]],
    ) -> list[DataPoint]:
        """
        Collect multiple data points in a single call.

        Each item dict must contain definition_id plus the value fields.
        Definitions are fetched once and reused.
        """
        # Pre-fetch all referenced definitions
        definition_ids = {item["definition_id"] for item in items}
        stmt = select(DataDefinition).where(
            DataDefinition.id.in_(definition_ids),
            DataDefinition.is_active.is_(True),
        )
        result = await session.execute(stmt)
        defn_map: dict[UUID, DataDefinition] = {
            d.id: d for d in result.scalars().all()
        }

        # Validate all definitions exist
        for def_id in definition_ids:
            if def_id not in defn_map:
                raise NotFoundException(
                    resource="DataDefinition", resource_id=str(def_id),
                )

        # Collect each point
        points: list[DataPoint] = []
        for item in items:
            defn = defn_map[item["definition_id"]]
            point = await DataPointService.collect(
                session,
                defn,
                unit_id=item.get("unit_id"),
                lot_id=item.get("lot_id"),
                value_numeric=item.get("value_numeric"),
                value_string=item.get("value_string"),
                value_boolean=item.get("value_boolean"),
                source_equipment_id=item.get("source_equipment_id"),
                operator_id=item.get("operator_id"),
            )
            points.append(point)

        return points

    # ─── Queries ─────────────────────────────────────────────────────

    @staticmethod
    async def list_points(
        session: AsyncSession,
        params: PaginationParams,
        definition_id: UUID | None = None,
        unit_id: UUID | None = None,
        lot_id: UUID | None = None,
    ) -> tuple[Sequence[DataPoint], str | None, bool]:
        """Query data points with optional filters."""
        stmt = select(DataPoint).where(DataPoint.is_active.is_(True))
        if definition_id is not None:
            stmt = stmt.where(DataPoint.definition_id == definition_id)
        if unit_id is not None:
            stmt = stmt.where(DataPoint.unit_id == unit_id)
        if lot_id is not None:
            stmt = stmt.where(DataPoint.lot_id == lot_id)
        return await paginate_query(session, stmt, DataPoint, params)

    @staticmethod
    async def get_point(
        session: AsyncSession, point_id: UUID,
    ) -> DataPoint:
        """Get a single data point by ID."""
        stmt = select(DataPoint).where(
            DataPoint.id == point_id,
            DataPoint.is_active.is_(True),
        )
        result = await session.execute(stmt)
        point = result.scalar_one_or_none()
        if point is None:
            raise NotFoundException(
                resource="DataPoint", resource_id=str(point_id),
            )
        return point

    @staticmethod
    async def get_points_for_unit(
        session: AsyncSession, unit_id: UUID,
    ) -> Sequence[DataPoint]:
        """Get all data points collected for a specific WIP unit."""
        stmt = (
            select(DataPoint)
            .where(DataPoint.unit_id == unit_id, DataPoint.is_active.is_(True))
            .order_by(DataPoint.collected_at)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_definitions_for_step(
        session: AsyncSession, step_id: UUID,
    ) -> Sequence[DataDefinition]:
        """Get all active data definitions for a specific route step."""
        stmt = (
            select(DataDefinition)
            .where(
                DataDefinition.step_id == step_id,
                DataDefinition.is_active.is_(True),
            )
            .order_by(DataDefinition.code)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
