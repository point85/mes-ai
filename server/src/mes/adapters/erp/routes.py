"""
ERP Adapter: REST API routes for outbound queue administration.

Endpoints:
- GET    /api/v1/erp/queue          List failed queue items
- GET    /api/v1/erp/queue/stats    Queue statistics
- POST   /api/v1/erp/queue/{id}/retry   Retry a failed item
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import success_response
from mes.framework.db import get_db_session

from .queue import ERPOutboundQueueService, QueueItemRead, QueueStats

router = APIRouter(
    prefix="/api/v1/erp",
    tags=["ERP Integration"],
)


@router.get("/queue", response_model=dict)
async def list_failed_items(
    db: AsyncSession = Depends(get_db_session),
):
    """List all failed ERP outbound queue items."""
    items = await ERPOutboundQueueService.list_failed(db)
    data = [
        QueueItemRead(
            id=str(item.id),
            report_type=item.report_type,
            payload=json.loads(item.payload),
            status=item.status,
            attempts=item.attempts,
            max_attempts=item.max_attempts,
            next_retry_at=item.next_retry_at,
            last_error=item.last_error,
            erp_doc_number=item.erp_doc_number,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ).model_dump()
        for item in items
    ]
    return success_response(data)


@router.get("/queue/stats", response_model=dict)
async def queue_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """Get ERP outbound queue statistics."""
    stats = await ERPOutboundQueueService.get_stats(db)
    return success_response(stats.model_dump())


@router.post("/queue/{item_id}/retry", response_model=dict)
async def retry_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Reset a failed queue item to pending for re-processing."""
    success = await ERPOutboundQueueService.retry_item(db, str(item_id))
    if not success:
        from mes.framework.api.exceptions import NotFoundException
        raise NotFoundException(resource="ERPOutboundQueueItem", resource_id=str(item_id))
    await db.commit()
    return success_response({"retried": True, "item_id": str(item_id)})
