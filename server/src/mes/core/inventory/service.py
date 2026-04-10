"""
INVENTORY: Business logic service for inventory management.

Provides CRUD for storage locations, inventory balance queries,
and transactional operations: receive, put-away, pick, move, consume, adjust.
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

from .events import (
    inventory_adjusted,
    inventory_consumed,
    inventory_moved,
    inventory_picked,
    inventory_putaway,
    inventory_received,
)
from .exceptions import (
    DuplicateLocationCodeException,
    InsufficientInventoryException,
    InvalidTransactionException,
)
from .models import InventoryBalance, InventoryTransaction, StorageLocation

logger = logging.getLogger("mes.inventory")


# ═══════════════════════════════════════════════════════════════════
# StorageLocation CRUD
# ═══════════════════════════════════════════════════════════════════


class StorageLocationService:
    """Service class for storage-location CRUD."""

    @staticmethod
    async def list_locations(
        session: AsyncSession,
        params: PaginationParams,
        location_type: str | None = None,
        site_id: UUID | None = None,
    ) -> tuple[Sequence[StorageLocation], str | None, bool]:
        """List active storage locations with optional filters."""
        stmt = select(StorageLocation).where(StorageLocation.is_active.is_(True))
        if location_type is not None:
            stmt = stmt.where(StorageLocation.location_type == location_type)
        if site_id is not None:
            stmt = stmt.where(StorageLocation.site_id == site_id)
        return await paginate_query(session, stmt, StorageLocation, params)

    @staticmethod
    async def get_location(
        session: AsyncSession, location_id: UUID,
    ) -> StorageLocation:
        """Get a storage location by ID. Raises NotFoundException if missing."""
        stmt = select(StorageLocation).where(
            StorageLocation.id == location_id,
            StorageLocation.is_active.is_(True),
        )
        result = await session.execute(stmt)
        location = result.scalar_one_or_none()
        if location is None:
            raise NotFoundException(
                resource="StorageLocation", resource_id=str(location_id),
            )
        return location

    @staticmethod
    async def create_location(
        session: AsyncSession, **kwargs: Any,
    ) -> StorageLocation:
        """Create a new storage location. Raises DuplicateLocationCodeException if code exists."""
        existing = await session.execute(
            select(StorageLocation).where(StorageLocation.code == kwargs["code"]),
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateLocationCodeException(kwargs["code"])

        location = StorageLocation(**kwargs)
        session.add(location)
        await session.flush()
        logger.info("Created storage location %s (%s)", location.id, location.code)
        return location

    @staticmethod
    async def update_location(
        session: AsyncSession, location_id: UUID, **kwargs: Any,
    ) -> StorageLocation:
        """Update a storage location. Only non-None values are applied."""
        location = await StorageLocationService.get_location(session, location_id)

        new_code = kwargs.get("code")
        if new_code is not None and new_code != location.code:
            existing = await session.execute(
                select(StorageLocation).where(
                    StorageLocation.code == new_code,
                    StorageLocation.id != location_id,
                ),
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateLocationCodeException(new_code)

        for key, value in kwargs.items():
            if value is not None:
                setattr(location, key, value)
        await session.flush()
        logger.info("Updated storage location %s (%s)", location.id, location.code)
        return location

    @staticmethod
    async def delete_location(
        session: AsyncSession, location_id: UUID,
    ) -> None:
        """Soft-delete a storage location."""
        location = await StorageLocationService.get_location(session, location_id)
        location.is_active = False
        await session.flush()
        logger.info("Soft-deleted storage location %s (%s)", location.id, location.code)


# ═══════════════════════════════════════════════════════════════════
# InventoryBalance queries
# ═══════════════════════════════════════════════════════════════════


class InventoryBalanceService:
    """Service class for inventory balance queries."""

    @staticmethod
    async def list_balances(
        session: AsyncSession,
        params: PaginationParams,
        material_lot_id: UUID | None = None,
        location_id: UUID | None = None,
    ) -> tuple[Sequence[InventoryBalance], str | None, bool]:
        """List inventory balances with optional filters."""
        stmt = select(InventoryBalance).where(InventoryBalance.is_active.is_(True))
        if material_lot_id is not None:
            stmt = stmt.where(InventoryBalance.material_lot_id == material_lot_id)
        if location_id is not None:
            stmt = stmt.where(InventoryBalance.location_id == location_id)
        return await paginate_query(session, stmt, InventoryBalance, params)

    @staticmethod
    async def get_balance(
        session: AsyncSession,
        material_lot_id: UUID,
        location_id: UUID,
    ) -> InventoryBalance | None:
        """Get the inventory balance for a specific lot at a specific location."""
        stmt = select(InventoryBalance).where(
            InventoryBalance.material_lot_id == material_lot_id,
            InventoryBalance.location_id == location_id,
            InventoryBalance.is_active.is_(True),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_or_create_balance(
        session: AsyncSession,
        material_lot_id: UUID,
        location_id: UUID,
    ) -> InventoryBalance:
        """Get or create an inventory balance record for a lot/location pair."""
        balance = await InventoryBalanceService.get_balance(
            session, material_lot_id, location_id,
        )
        if balance is None:
            balance = InventoryBalance(
                material_lot_id=material_lot_id,
                location_id=location_id,
                quantity_on_hand=0.0,
                quantity_reserved=0.0,
            )
            session.add(balance)
            await session.flush()
        return balance


# ═══════════════════════════════════════════════════════════════════
# Inventory transactions (the core movement operations)
# ═══════════════════════════════════════════════════════════════════


class InventoryTransactionService:
    """Service class for inventory movement operations."""

    @staticmethod
    async def list_transactions(
        session: AsyncSession,
        params: PaginationParams,
        material_lot_id: UUID | None = None,
        location_id: UUID | None = None,
        transaction_type: str | None = None,
    ) -> tuple[Sequence[InventoryTransaction], str | None, bool]:
        """List inventory transactions with optional filters."""
        stmt = select(InventoryTransaction).where(
            InventoryTransaction.is_active.is_(True),
        )
        if material_lot_id is not None:
            stmt = stmt.where(InventoryTransaction.material_lot_id == material_lot_id)
        if location_id is not None:
            stmt = stmt.where(
                (InventoryTransaction.from_location_id == location_id)
                | (InventoryTransaction.to_location_id == location_id),
            )
        if transaction_type is not None:
            stmt = stmt.where(InventoryTransaction.transaction_type == transaction_type)
        stmt = stmt.order_by(InventoryTransaction.performed_at.desc())
        return await paginate_query(session, stmt, InventoryTransaction, params)

    # ─── Receive ─────────────────────────────────────────────────────

    @staticmethod
    async def receive(
        session: AsyncSession,
        *,
        material_lot_id: UUID,
        to_location_id: UUID,
        quantity: float,
        reason: str | None = None,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
    ) -> InventoryTransaction:
        """
        Receive material into a location. Creates or increments the
        InventoryBalance at the destination location.
        """
        # Validate destination exists
        await StorageLocationService.get_location(session, to_location_id)

        # Update balance at destination
        balance = await InventoryBalanceService._get_or_create_balance(
            session, material_lot_id, to_location_id,
        )
        balance.quantity_on_hand += quantity

        # Create transaction record
        now = datetime.now(timezone.utc)
        txn = InventoryTransaction(
            transaction_type="receive",
            material_lot_id=material_lot_id,
            from_location_id=None,
            to_location_id=to_location_id,
            quantity=quantity,
            reference_id=reference_id,
            reference_type=reference_type,
            reason=reason,
            performed_at=now,
            performed_at_utc=now.replace(tzinfo=None),
        )
        session.add(txn)
        await session.flush()

        await event_bus.publish(
            inventory_received(str(material_lot_id), str(to_location_id), quantity),
        )
        logger.info(
            "Received qty=%.3f of lot %s into location %s",
            quantity, material_lot_id, to_location_id,
        )
        return txn

    # ─── Put-away ────────────────────────────────────────────────────

    @staticmethod
    async def putaway(
        session: AsyncSession,
        *,
        material_lot_id: UUID,
        from_location_id: UUID,
        to_location_id: UUID,
        quantity: float,
        reason: str | None = None,
    ) -> InventoryTransaction:
        """
        Put away material from a receiving location to a storage location
        (aisle/bay/tier).
        """
        return await InventoryTransactionService._transfer(
            session,
            transaction_type="putaway",
            material_lot_id=material_lot_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity,
            reason=reason,
            event_fn=inventory_putaway,
        )

    # ─── Pick ────────────────────────────────────────────────────────

    @staticmethod
    async def pick(
        session: AsyncSession,
        *,
        material_lot_id: UUID,
        from_location_id: UUID,
        to_location_id: UUID,
        quantity: float,
        reason: str | None = None,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
    ) -> InventoryTransaction:
        """
        Pick material from a storage location for production use.
        """
        return await InventoryTransactionService._transfer(
            session,
            transaction_type="pick",
            material_lot_id=material_lot_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity,
            reason=reason,
            reference_id=reference_id,
            reference_type=reference_type,
            event_fn=inventory_picked,
        )

    # ─── Move ────────────────────────────────────────────────────────

    @staticmethod
    async def move(
        session: AsyncSession,
        *,
        material_lot_id: UUID,
        from_location_id: UUID,
        to_location_id: UUID,
        quantity: float,
        reason: str | None = None,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
    ) -> InventoryTransaction:
        """
        Move material between any two locations.
        """
        return await InventoryTransactionService._transfer(
            session,
            transaction_type="move",
            material_lot_id=material_lot_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity,
            reason=reason,
            reference_id=reference_id,
            reference_type=reference_type,
            event_fn=inventory_moved,
        )

    # ─── Consume ─────────────────────────────────────────────────────

    @staticmethod
    async def consume(
        session: AsyncSession,
        *,
        material_lot_id: UUID,
        from_location_id: UUID,
        quantity: float,
        reason: str | None = None,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
    ) -> InventoryTransaction:
        """
        Consume inventory from a location (typically RIP) for WIP.
        Decrements the balance at the source location; no destination.
        """
        await StorageLocationService.get_location(session, from_location_id)

        # Decrement source balance
        source_balance = await InventoryBalanceService._get_or_create_balance(
            session, material_lot_id, from_location_id,
        )
        available = source_balance.quantity_on_hand - source_balance.quantity_reserved
        if quantity > available:
            raise InsufficientInventoryException(
                str(from_location_id), quantity, available,
            )
        source_balance.quantity_on_hand -= quantity

        # Create transaction record
        now = datetime.now(timezone.utc)
        txn = InventoryTransaction(
            transaction_type="consume",
            material_lot_id=material_lot_id,
            from_location_id=from_location_id,
            to_location_id=None,
            quantity=quantity,
            reference_id=reference_id,
            reference_type=reference_type,
            reason=reason,
            performed_at=now,
            performed_at_utc=now.replace(tzinfo=None),
        )
        session.add(txn)
        await session.flush()

        await event_bus.publish(
            inventory_consumed(str(material_lot_id), str(from_location_id), quantity),
        )
        logger.info(
            "Consumed qty=%.3f of lot %s from location %s",
            quantity, material_lot_id, from_location_id,
        )
        return txn

    # ─── Adjust ──────────────────────────────────────────────────────

    @staticmethod
    async def adjust(
        session: AsyncSession,
        *,
        material_lot_id: UUID,
        location_id: UUID,
        quantity: float,
        reason: str,
    ) -> InventoryTransaction:
        """
        Manual inventory adjustment. Sets the balance to the given quantity
        and records the delta as a transaction.
        """
        await StorageLocationService.get_location(session, location_id)

        balance = await InventoryBalanceService._get_or_create_balance(
            session, material_lot_id, location_id,
        )
        old_qty = balance.quantity_on_hand
        delta = quantity - old_qty
        balance.quantity_on_hand = quantity

        now = datetime.now(timezone.utc)
        txn = InventoryTransaction(
            transaction_type="adjust",
            material_lot_id=material_lot_id,
            from_location_id=location_id if delta < 0 else None,
            to_location_id=location_id if delta >= 0 else None,
            quantity=abs(delta),
            reason=reason,
            performed_at=now,
            performed_at_utc=now.replace(tzinfo=None),
        )
        session.add(txn)
        await session.flush()

        await event_bus.publish(
            inventory_adjusted(str(material_lot_id), str(location_id), old_qty, quantity),
        )
        logger.info(
            "Adjusted lot %s at location %s: %.3f → %.3f (delta=%.3f, reason=%s)",
            material_lot_id, location_id, old_qty, quantity, delta, reason,
        )
        return txn

    # ─── Internal transfer helper ────────────────────────────────────

    @staticmethod
    async def _transfer(
        session: AsyncSession,
        *,
        transaction_type: str,
        material_lot_id: UUID,
        from_location_id: UUID,
        to_location_id: UUID,
        quantity: float,
        reason: str | None = None,
        reference_id: UUID | None = None,
        reference_type: str | None = None,
        event_fn: Any,
    ) -> InventoryTransaction:
        """
        Internal helper for putaway/pick/move — decrements source,
        increments destination, creates transaction record.
        """
        if from_location_id == to_location_id:
            raise InvalidTransactionException(
                "Source and destination locations must be different",
            )

        # Validate both locations exist
        await StorageLocationService.get_location(session, from_location_id)
        await StorageLocationService.get_location(session, to_location_id)

        # Decrement source
        source_balance = await InventoryBalanceService._get_or_create_balance(
            session, material_lot_id, from_location_id,
        )
        available = source_balance.quantity_on_hand - source_balance.quantity_reserved
        if quantity > available:
            raise InsufficientInventoryException(
                str(from_location_id), quantity, available,
            )
        source_balance.quantity_on_hand -= quantity

        # Increment destination
        dest_balance = await InventoryBalanceService._get_or_create_balance(
            session, material_lot_id, to_location_id,
        )
        dest_balance.quantity_on_hand += quantity

        # Create transaction record
        now = datetime.now(timezone.utc)
        txn = InventoryTransaction(
            transaction_type=transaction_type,
            material_lot_id=material_lot_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity,
            reference_id=reference_id,
            reference_type=reference_type,
            reason=reason,
            performed_at=now,
            performed_at_utc=now.replace(tzinfo=None),
        )
        session.add(txn)
        await session.flush()

        await event_bus.publish(
            event_fn(str(material_lot_id), str(from_location_id), str(to_location_id), quantity),
        )
        logger.info(
            "%s qty=%.3f of lot %s: %s → %s",
            transaction_type.capitalize(), quantity,
            material_lot_id, from_location_id, to_location_id,
        )
        return txn
