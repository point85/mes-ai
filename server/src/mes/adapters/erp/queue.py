"""
ERP Adapter: Outbound queue model, service, and event definitions.

Failed outbound reports are queued with exponential backoff retry.
Admin REST endpoints allow viewing and retrying failed items.

Per ARCHITECTURE.md §9.2.7.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from mes.framework.db import BaseModel
from mes.framework.events import MESEvent

logger = logging.getLogger("mes.adapters.erp.queue")


# ── SQLAlchemy Model ───────────────────────────────────────────────────────

class ERPOutboundQueueItem(BaseModel):
    """
    Persistent queue for ERP outbound reports.
    Failed reports are retried with exponential backoff.
    """

    __tablename__ = "erp_outbound_queue"

    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Report type: completion | consumption | scrap | labor | downtime | quality_result",
    )
    payload: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="JSON-serialized report data",
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False,
        comment="Queue status: pending | sent | failed | retry",
    )
    attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Number of send attempts so far",
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False,
        comment="Maximum retry attempts before marking as failed",
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Next retry timestamp (exponential backoff)",
    )
    next_retry_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Next retry timestamp in UTC (exponential backoff)",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Error message from last failed attempt",
    )
    erp_doc_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="ERP document number if successfully sent",
    )


# ── Pydantic Schemas ──────────────────────────────────────────────────────

QUEUE_STATUSES = ("pending", "sent", "failed", "retry")

REPORT_TYPES = (
    "completion", "consumption", "scrap",
    "labor", "downtime", "quality_result",
)


class QueueItemRead(PydanticBaseModel):
    """Schema for reading a queue item."""

    id: str
    report_type: str
    payload: dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: datetime | None = None
    next_retry_at_utc: datetime | None = None
    last_error: str | None = None
    erp_doc_number: str | None = None
    created_at: datetime
    created_at_utc: datetime | None = None
    updated_at: datetime
    updated_at_utc: datetime | None = None


class QueueItemCreate(PydanticBaseModel):
    """Schema for creating a queue item (internal use)."""

    report_type: str
    payload: dict[str, Any]
    max_attempts: int = Field(default=5, ge=1, le=20)


class QueueStats(PydanticBaseModel):
    """Summary statistics for the outbound queue."""

    pending: int = 0
    sent: int = 0
    failed: int = 0
    retry: int = 0
    total: int = 0


# ── Event Definitions ─────────────────────────────────────────────────────

def erp_outbound_sent(report_type: str, erp_doc_number: str) -> MESEvent:
    """Event emitted when an outbound report is successfully sent."""
    return MESEvent(
        event_type="erp.outbound.sent",
        source="erp_adapter",
        payload={"report_type": report_type, "erp_doc_number": erp_doc_number},
    )


def erp_outbound_failed(
    queue_item_id: str, report_type: str, error: str, attempts: int,
) -> MESEvent:
    """Event emitted when an outbound report exhausts all retries."""
    return MESEvent(
        event_type="erp.outbound.failed",
        source="erp_adapter",
        payload={
            "queue_item_id": queue_item_id,
            "report_type": report_type,
            "error": error,
            "attempts": attempts,
        },
    )


# ── Service ───────────────────────────────────────────────────────────────

class ERPOutboundQueueService:
    """
    Manages the ERP outbound retry queue.

    Usage:
        service = ERPOutboundQueueService()
        item_id = await service.enqueue(db, "completion", {...})
        processed = await service.process_queue(db, outbound_adapter)
    """

    BACKOFF_BASE_SEC = 30  # Base interval for exponential backoff

    @staticmethod
    async def enqueue(
        db: Any,
        report_type: str,
        payload: dict[str, Any],
        max_attempts: int = 5,
    ) -> str:
        """
        Add a report to the outbound queue.

        Args:
            db: SQLAlchemy AsyncSession.
            report_type: One of REPORT_TYPES.
            payload: Report data dictionary.
            max_attempts: Max retry count.

        Returns:
            Queue item ID (UUID string).
        """
        item = ERPOutboundQueueItem(
            report_type=report_type,
            payload=json.dumps(payload, default=str),
            status="pending",
            max_attempts=max_attempts,
        )
        db.add(item)
        await db.flush()
        logger.info("Enqueued ERP outbound %s (id=%s)", report_type, item.id)
        return str(item.id)

    @staticmethod
    async def process_queue(
        db: Any,
        outbound_adapter: Any,
        batch_size: int = 10,
    ) -> int:
        """
        Process pending/retry items in the queue.

        Calls the appropriate outbound adapter method for each item.
        On success, marks as 'sent'. On failure, increments attempt count
        with exponential backoff, or marks 'failed' if max retries exhausted.

        Args:
            db: SQLAlchemy AsyncSession.
            outbound_adapter: ERPOutboundAdapter instance.
            batch_size: Max items to process in one batch.

        Returns:
            Number of items processed.
        """
        from sqlalchemy import select, or_

        now = datetime.now(timezone.utc)
        stmt = (
            select(ERPOutboundQueueItem)
            .where(
                or_(
                    ERPOutboundQueueItem.status == "pending",
                    (ERPOutboundQueueItem.status == "retry") &
                    (ERPOutboundQueueItem.next_retry_at <= now),
                ),
                ERPOutboundQueueItem.is_active == True,  # noqa: E712
            )
            .order_by(ERPOutboundQueueItem.created_at)
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        processed = 0
        for item in items:
            payload = json.loads(item.payload)
            try:
                confirmation = await _dispatch_report(outbound_adapter, item.report_type, payload)
                item.status = "sent"
                item.erp_doc_number = confirmation.erp_doc_number
                item.attempts += 1
                processed += 1

                from mes.framework.events import event_bus
                await event_bus.publish(erp_outbound_sent(
                    item.report_type, confirmation.erp_doc_number or "",
                ))

            except Exception as exc:
                item.attempts += 1
                item.last_error = str(exc)

                if item.attempts >= item.max_attempts:
                    item.status = "failed"
                    logger.error(
                        "ERP outbound %s (id=%s) failed after %d attempts: %s",
                        item.report_type, item.id, item.attempts, exc,
                    )
                    from mes.framework.events import event_bus
                    await event_bus.publish(erp_outbound_failed(
                        str(item.id), item.report_type, str(exc), item.attempts,
                    ))
                else:
                    item.status = "retry"
                    backoff = ERPOutboundQueueService.BACKOFF_BASE_SEC * (2 ** (item.attempts - 1))
                    item.next_retry_at = datetime.fromtimestamp(
                        now.timestamp() + backoff, tz=timezone.utc,
                    )
                    item.next_retry_at_utc = item.next_retry_at
                    logger.warning(
                        "ERP outbound %s (id=%s) retry %d/%d in %ds",
                        item.report_type, item.id, item.attempts, item.max_attempts, backoff,
                    )

                processed += 1

        await db.flush()
        return processed

    @staticmethod
    async def list_failed(db: Any) -> list[ERPOutboundQueueItem]:
        """Return all failed queue items."""
        from sqlalchemy import select

        stmt = (
            select(ERPOutboundQueueItem)
            .where(
                ERPOutboundQueueItem.status == "failed",
                ERPOutboundQueueItem.is_active == True,  # noqa: E712
            )
            .order_by(ERPOutboundQueueItem.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def retry_item(db: Any, item_id: str) -> bool:
        """Reset a failed item to pending for re-processing."""
        from sqlalchemy import select

        stmt = select(ERPOutboundQueueItem).where(
            ERPOutboundQueueItem.id == uuid.UUID(item_id),
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item or item.status != "failed":
            return False

        item.status = "pending"
        item.attempts = 0
        item.next_retry_at = None
        item.next_retry_at_utc = None
        item.last_error = None
        await db.flush()
        logger.info("Reset ERP outbound item %s to pending", item_id)
        return True

    @staticmethod
    async def get_stats(db: Any) -> QueueStats:
        """Get queue statistics by status."""
        from sqlalchemy import func, select

        stmt = (
            select(
                ERPOutboundQueueItem.status,
                func.count().label("count"),
            )
            .where(ERPOutboundQueueItem.is_active == True)  # noqa: E712
            .group_by(ERPOutboundQueueItem.status)
        )
        result = await db.execute(stmt)
        counts = {row[0]: row[1] for row in result.all()}

        return QueueStats(
            pending=counts.get("pending", 0),
            sent=counts.get("sent", 0),
            failed=counts.get("failed", 0),
            retry=counts.get("retry", 0),
            total=sum(counts.values()),
        )


async def _dispatch_report(adapter: Any, report_type: str, payload: dict) -> Any:
    """Route a queue item to the correct outbound adapter method."""
    if report_type == "completion":
        return await adapter.report_completion(
            order_id=payload["order_id"],
            qty_good=payload["qty_good"],
            qty_reject=payload.get("qty_reject", 0),
            step_id=payload.get("step_id"),
        )
    elif report_type == "consumption":
        from .dtos import MaterialConsumptionDTO
        materials = [MaterialConsumptionDTO(**m) for m in payload["materials"]]
        return await adapter.report_consumption(
            order_id=payload["order_id"],
            materials=materials,
        )
    elif report_type == "scrap":
        return await adapter.report_scrap(
            order_id=payload["order_id"],
            qty_scrapped=payload["qty_scrapped"],
            reason_code=payload["reason_code"],
        )
    elif report_type == "labor":
        return await adapter.report_labor(
            order_id=payload["order_id"],
            operator_id=payload["operator_id"],
            duration_minutes=payload["duration_minutes"],
        )
    elif report_type == "downtime":
        return await adapter.report_downtime(
            equipment_id=payload["equipment_id"],
            duration_minutes=payload["duration_minutes"],
            reason_code=payload["reason_code"],
            started_at=datetime.fromisoformat(payload["started_at"]),
        )
    elif report_type == "quality_result":
        return await adapter.report_quality_result(
            order_id=payload["order_id"],
            test_id=payload["test_id"],
            result=payload["result"],
            details=payload.get("details", {}),
        )
    else:
        raise ValueError(f"Unknown report type: {report_type}")
