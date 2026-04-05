"""
ERP Adapter: Inbound order queue — model, service, and processor interface.

ERP systems push production orders to the MES via the inbound adapter.
Orders are persisted immediately to the ``erp_inbound_orders`` table so
they survive MES restarts.  A periodic background task (default: every
5 seconds) picks up unprocessed rows and converts them into MES
``ProductionOrder`` entities, then optionally creates Lots or Units
depending on the concrete ``OrderProcessor`` implementation.

Architecture
────────────
1. **Persist** — ``ERPInboundQueueService.enqueue()`` stores the raw
   ``ProductionOrderDTO`` as a JSON payload with status ``pending``.
2. **Process** — ``ERPInboundQueueService.process_queue()`` selects a
   batch of ``pending``/``retry`` rows and delegates each to the active
   ``OrderProcessor``.
3. **OrderProcessor** — Abstract interface with a single
   ``process_order()`` method.  Each demo (CPG, Electronics) ships its
   own implementation.  End users replace or extend these.
4. **Mark** — On success the row moves to ``processed``.  On failure it
   is retried with exponential backoff (default 5 attempts, 30 s base).

Customisation guide
───────────────────
To adapt this for your factory:

1. Create a new file (e.g. ``my_processor.py``) that inherits from
   ``OrderProcessor`` and implements ``process_order()``.
2. Register your processor at startup via
   ``ERPInboundQueueService.set_processor(MyProcessor())``.
3. Inside ``process_order()`` you have full access to the async
   SQLAlchemy session and can call any MES core service.

See ``mes.core.demo.order_processors`` for working examples.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from pydantic import BaseModel as PydanticBaseModel, Field
from sqlalchemy import Integer, String, Text, DateTime, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from mes.framework.db import BaseModel
from mes.framework.events import MESEvent, event_bus

logger = logging.getLogger("mes.adapters.erp.inbound_queue")


# ── SQLAlchemy Model ───────────────────────────────────────────────────────

class ERPInboundOrder(BaseModel):
    """
    Persistent queue row for an inbound ERP production order.

    Statuses:
        pending   — just received, waiting to be processed
        processed — successfully converted into a ProductionOrder (+ WIP)
        failed    — exhausted all retry attempts
        retry     — will be retried after ``next_retry_at``
    """

    __tablename__ = "erp_inbound_orders"

    erp_reference: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        comment="ERP-native order identifier (from ProductionOrderDTO)",
    )
    product_code: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Product code from the ERP order",
    )
    payload: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Full ProductionOrderDTO serialized as JSON",
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True,
        comment="Queue status: pending | processed | failed | retry",
    )

    # ── Processing outcome ──────────────────────────────────────────
    order_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        comment="MES ProductionOrder.id after successful processing",
    )
    wip_ids: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON list of created Lot/Unit IDs",
    )
    processor_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Name of the OrderProcessor that handled this order",
    )

    # ── Retry bookkeeping ───────────────────────────────────────────
    attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Number of processing attempts so far",
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False,
        comment="Maximum retry attempts before marking as failed",
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Next retry timestamp (exponential backoff)",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Error message from the last failed attempt",
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when successfully processed",
    )


# ── Pydantic Schemas ──────────────────────────────────────────────────────

QUEUE_STATUSES = ("pending", "processed", "failed", "retry")


class InboundOrderRead(PydanticBaseModel):
    """Schema for reading an inbound order queue item."""

    id: str
    erp_reference: str
    product_code: str
    payload: dict[str, Any]
    status: str
    order_id: str | None = None
    wip_ids: list[str] | None = None
    processor_name: str | None = None
    attempts: int
    max_attempts: int
    next_retry_at: datetime | None = None
    last_error: str | None = None
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InboundQueueStats(PydanticBaseModel):
    """Summary statistics for the inbound order queue."""

    pending: int = 0
    processed: int = 0
    failed: int = 0
    retry: int = 0
    total: int = 0


# ── Event Definitions ─────────────────────────────────────────────────────

def erp_inbound_processed(
    queue_item_id: str, erp_reference: str, order_id: str,
) -> MESEvent:
    return MESEvent(
        event_type="erp.inbound.processed",
        source="erp_inbound_queue",
        payload={
            "queue_item_id": queue_item_id,
            "erp_reference": erp_reference,
            "order_id": order_id,
        },
    )


def erp_inbound_failed(
    queue_item_id: str, erp_reference: str, error: str, attempts: int,
) -> MESEvent:
    return MESEvent(
        event_type="erp.inbound.failed",
        source="erp_inbound_queue",
        payload={
            "queue_item_id": queue_item_id,
            "erp_reference": erp_reference,
            "error": error,
            "attempts": attempts,
        },
    )


# ── OrderProcessor Interface ─────────────────────────────────────────────

class ProcessorResult:
    """Value object returned by an OrderProcessor."""

    __slots__ = ("order_id", "wip_ids")

    def __init__(self, order_id: str, wip_ids: list[str] | None = None):
        self.order_id = order_id
        self.wip_ids = wip_ids or []


class OrderProcessor(ABC):
    """
    Abstract interface for converting an inbound ERP order into MES entities.

    Implement ``process_order()`` to:
      1. Create a ``ProductionOrder`` (or reuse an existing one).
      2. Optionally create Lots (batch) or Units (discrete).
      3. Optionally release the order so WIP can start immediately.
      4. Return a ``ProcessorResult`` with the created IDs.

    The session is managed by the caller — do NOT commit or close it.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable processor name (e.g. 'cpg-lot-processor')."""
        ...

    @abstractmethod
    async def process_order(
        self,
        session: AsyncSession,
        payload: dict[str, Any],
    ) -> ProcessorResult:
        """
        Convert an ERP order payload into MES entities.

        Args:
            session: Active SQLAlchemy async session (caller manages commit).
            payload: Deserialized ProductionOrderDTO dict.

        Returns:
            ProcessorResult with the created order ID and optional WIP IDs.

        Raises:
            Any exception — the queue service will catch it, increment the
            retry counter, and schedule a backoff.
        """
        ...


# ── Service ───────────────────────────────────────────────────────────────

class ERPInboundQueueService:
    """
    Manages the ERP inbound order queue.

    Usage::

        # At startup — register a processor
        ERPInboundQueueService.set_processor(MyCPGProcessor())

        # When an ERP order arrives
        await ERPInboundQueueService.enqueue(session, dto.model_dump(mode="json"))

        # Periodic background task
        processed = await ERPInboundQueueService.process_queue(session)
    """

    BACKOFF_BASE_SEC = 30
    _processor: OrderProcessor | None = None

    @classmethod
    def set_processor(cls, processor: OrderProcessor) -> None:
        """Register the active order processor."""
        cls._processor = processor
        logger.info("Inbound order processor set: %s", processor.name)

    @classmethod
    def get_processor(cls) -> OrderProcessor | None:
        """Return the currently registered processor (or None)."""
        return cls._processor

    # ── Enqueue ──────────────────────────────────────────────────────

    @staticmethod
    async def enqueue(
        session: AsyncSession,
        payload: dict[str, Any],
        max_attempts: int = 5,
    ) -> str:
        """
        Persist an inbound ERP order for later processing.

        Args:
            session: Active DB session (caller manages commit).
            payload: ProductionOrderDTO dict.
            max_attempts: Max processing attempts.

        Returns:
            Queue item ID (UUID string).
        """
        item = ERPInboundOrder(
            erp_reference=payload["erp_reference"],
            product_code=payload["product_code"],
            payload=json.dumps(payload, default=str),
            status="pending",
            max_attempts=max_attempts,
        )
        session.add(item)
        await session.flush()
        logger.info(
            "Enqueued inbound ERP order %s (erp_ref=%s, product=%s)",
            item.id, item.erp_reference, item.product_code,
        )
        return str(item.id)

    # ── Bulk enqueue from adapter sync ───────────────────────────────

    @staticmethod
    async def enqueue_from_sync(
        session: AsyncSession,
        dtos: list[Any],
        max_attempts: int = 5,
    ) -> list[str]:
        """
        Persist multiple inbound orders from an ERP adapter sync call.

        Skips DTOs whose ``erp_reference`` already exists in ``pending``
        or ``retry`` status to avoid duplicates.

        Returns:
            List of newly created queue item IDs.
        """
        created_ids: list[str] = []
        for dto in dtos:
            payload = dto.model_dump(mode="json") if hasattr(dto, "model_dump") else dto

            # Skip if this erp_reference is already queued
            existing = await session.execute(
                select(ERPInboundOrder.id).where(
                    ERPInboundOrder.erp_reference == payload["erp_reference"],
                    ERPInboundOrder.status.in_(("pending", "retry")),
                    ERPInboundOrder.is_active.is_(True),
                )
            )
            if existing.scalar_one_or_none() is not None:
                logger.debug(
                    "Skipping duplicate inbound order erp_ref=%s",
                    payload["erp_reference"],
                )
                continue

            item_id = await ERPInboundQueueService.enqueue(
                session, payload, max_attempts=max_attempts,
            )
            created_ids.append(item_id)
        return created_ids

    # ── Process ──────────────────────────────────────────────────────

    @classmethod
    async def process_queue(
        cls,
        session: AsyncSession,
        batch_size: int = 10,
    ) -> int:
        """
        Process pending/retryable inbound orders.

        Delegates each to the registered ``OrderProcessor``.  On success
        marks the row ``processed``; on failure applies exponential backoff
        or marks ``failed`` after max attempts.

        Returns:
            Number of items successfully processed.
        """
        if cls._processor is None:
            return 0  # no processor registered — nothing to do

        now = datetime.now(timezone.utc)
        stmt = (
            select(ERPInboundOrder)
            .where(
                or_(
                    ERPInboundOrder.status == "pending",
                    (ERPInboundOrder.status == "retry")
                    & (ERPInboundOrder.next_retry_at <= now),
                ),
                ERPInboundOrder.is_active.is_(True),
            )
            .order_by(ERPInboundOrder.created_at)
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        items: Sequence[ERPInboundOrder] = result.scalars().all()

        processed = 0
        for item in items:
            payload = json.loads(item.payload)
            try:
                proc_result = await cls._processor.process_order(session, payload)
                item.status = "processed"
                item.order_id = proc_result.order_id
                item.wip_ids = json.dumps(proc_result.wip_ids) if proc_result.wip_ids else None
                item.processor_name = cls._processor.name
                item.attempts += 1
                item.processed_at = datetime.now(timezone.utc)
                await session.flush()
                processed += 1

                await event_bus.publish(erp_inbound_processed(
                    str(item.id), item.erp_reference, proc_result.order_id,
                ))
                logger.info(
                    "Processed inbound order %s → MES order %s",
                    item.erp_reference, proc_result.order_id,
                )

            except Exception as exc:
                item.attempts += 1
                item.last_error = str(exc)

                if item.attempts >= item.max_attempts:
                    item.status = "failed"
                    await event_bus.publish(erp_inbound_failed(
                        str(item.id), item.erp_reference,
                        str(exc), item.attempts,
                    ))
                    logger.error(
                        "Inbound order %s FAILED after %d attempts: %s",
                        item.erp_reference, item.attempts, exc,
                    )
                else:
                    item.status = "retry"
                    backoff = cls.BACKOFF_BASE_SEC * (2 ** (item.attempts - 1))
                    item.next_retry_at = now + timedelta(seconds=backoff)
                    logger.warning(
                        "Inbound order %s attempt %d failed, retry at %s: %s",
                        item.erp_reference, item.attempts,
                        item.next_retry_at.isoformat(), exc,
                    )

                await session.flush()

        return processed

    # ── Queries ──────────────────────────────────────────────────────

    @staticmethod
    async def list_items(
        session: AsyncSession,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ERPInboundOrder]:
        """List inbound order queue items, optionally filtered by status."""
        stmt = (
            select(ERPInboundOrder)
            .where(ERPInboundOrder.is_active.is_(True))
            .order_by(ERPInboundOrder.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(ERPInboundOrder.status == status)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_stats(session: AsyncSession) -> InboundQueueStats:
        """Return summary counts by status."""
        from sqlalchemy import func

        stmt = (
            select(ERPInboundOrder.status, func.count())
            .where(ERPInboundOrder.is_active.is_(True))
            .group_by(ERPInboundOrder.status)
        )
        result = await session.execute(stmt)
        counts = {row[0]: row[1] for row in result.all()}

        stats = InboundQueueStats(
            pending=counts.get("pending", 0),
            processed=counts.get("processed", 0),
            failed=counts.get("failed", 0),
            retry=counts.get("retry", 0),
        )
        stats.total = stats.pending + stats.processed + stats.failed + stats.retry
        return stats

    @staticmethod
    async def retry_item(session: AsyncSession, item_id: str) -> ERPInboundOrder:
        """Reset a failed item back to pending for reprocessing."""
        from uuid import UUID

        stmt = select(ERPInboundOrder).where(
            ERPInboundOrder.id == UUID(item_id),
            ERPInboundOrder.is_active.is_(True),
        )
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            from mes.framework.api.exceptions import NotFoundException
            raise NotFoundException(resource="ERPInboundOrder", resource_id=item_id)

        item.status = "pending"
        item.attempts = 0
        item.last_error = None
        item.next_retry_at = None
        await session.flush()
        logger.info("Reset inbound order %s to pending", item_id)
        return item
