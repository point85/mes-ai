"""
INVENTORY: REST API routes for inventory management.

Endpoints:
- GET    /api/v1/storage-locations                              List storage locations
- POST   /api/v1/storage-locations                              Create a storage location
- GET    /api/v1/storage-locations/{location_id}                Get a storage location
- PATCH  /api/v1/storage-locations/{location_id}                Update a storage location
- DELETE /api/v1/storage-locations/{location_id}                Soft-delete a storage location

- GET    /api/v1/inventory/balances                             List inventory balances
- GET    /api/v1/inventory/transactions                         List inventory transactions

- POST   /api/v1/inventory/receive                              Receive material into inventory
- POST   /api/v1/inventory/putaway                              Put away to storage location
- POST   /api/v1/inventory/pick                                 Pick from storage
- POST   /api/v1/inventory/move                                 Move between locations
- POST   /api/v1/inventory/consume                              Consume for WIP
- POST   /api/v1/inventory/adjust                               Manual adjustment
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.pagination import PaginationParams, get_pagination_params
from mes.framework.api.responses import list_response, success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .schemas import (
    AdjustRequest,
    ConsumeInventoryRequest,
    InventoryBalanceRead,
    InventoryTransactionRead,
    MoveRequest,
    PickRequest,
    PutawayRequest,
    ReceiveRequest,
    StorageLocationCreate,
    StorageLocationRead,
    StorageLocationUpdate,
)
from .service import (
    InventoryBalanceService,
    InventoryTransactionService,
    StorageLocationService,
)

router = APIRouter(prefix="/api/v1", tags=["Inventory Management"])
loc_svc = StorageLocationService
bal_svc = InventoryBalanceService
txn_svc = InventoryTransactionService


# ═══════════════════════════════════════════════════════════════════
# StorageLocation endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/storage-locations")
async def list_storage_locations(
    location_type: str | None = Query(None, description="Filter by type: receiving, storage, rip, staging, shipping"),
    site_id: UUID | None = Query(None, description="Filter by site ID"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.read")),
):
    """List active storage locations with optional filters."""
    items, cursor, has_more = await loc_svc.list_locations(
        session, params, location_type=location_type, site_id=site_id,
    )
    return list_response(
        [StorageLocationRead.model_validate(loc).model_dump() for loc in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


@router.get("/storage-locations/{location_id}")
async def get_storage_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.read")),
):
    """Get a storage location by ID."""
    location = await loc_svc.get_location(session, location_id)
    return success_response(StorageLocationRead.model_validate(location).model_dump())


@router.post("/storage-locations", status_code=201)
async def create_storage_location(
    body: StorageLocationCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.create")),
):
    """Create a new storage location."""
    location = await loc_svc.create_location(session, **body.model_dump())
    await session.commit()
    return success_response(StorageLocationRead.model_validate(location).model_dump())


@router.patch("/storage-locations/{location_id}")
async def update_storage_location(
    location_id: UUID,
    body: StorageLocationUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.update")),
):
    """Update a storage location."""
    location = await loc_svc.update_location(
        session, location_id, **body.model_dump(exclude_unset=True),
    )
    await session.commit()
    return success_response(StorageLocationRead.model_validate(location).model_dump())


@router.delete("/storage-locations/{location_id}", status_code=204)
async def delete_storage_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.delete")),
):
    """Soft-delete a storage location."""
    await loc_svc.delete_location(session, location_id)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════
# InventoryBalance endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/inventory/balances")
async def list_inventory_balances(
    material_lot_id: UUID | None = Query(None, description="Filter by material lot ID"),
    location_id: UUID | None = Query(None, description="Filter by location ID"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.read")),
):
    """List inventory balances with optional filters."""
    items, cursor, has_more = await bal_svc.list_balances(
        session, params, material_lot_id=material_lot_id, location_id=location_id,
    )
    return list_response(
        [InventoryBalanceRead.model_validate(b).model_dump() for b in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


# ═══════════════════════════════════════════════════════════════════
# InventoryTransaction endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/inventory/transactions")
async def list_inventory_transactions(
    material_lot_id: UUID | None = Query(None, description="Filter by material lot ID"),
    location_id: UUID | None = Query(None, description="Filter by location ID (source or destination)"),
    transaction_type: str | None = Query(None, description="Filter by type: receive, putaway, pick, move, consume, adjust"),
    params: PaginationParams = Depends(get_pagination_params),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.read")),
):
    """List inventory transactions with optional filters."""
    items, cursor, has_more = await txn_svc.list_transactions(
        session, params,
        material_lot_id=material_lot_id,
        location_id=location_id,
        transaction_type=transaction_type,
    )
    return list_response(
        [InventoryTransactionRead.model_validate(t).model_dump() for t in items],
        cursor=cursor,
        limit=params.limit,
        has_more=has_more,
    )


# ═══════════════════════════════════════════════════════════════════
# Inventory operation endpoints
# ═══════════════════════════════════════════════════════════════════


@router.post("/inventory/receive", status_code=201)
async def receive_inventory(
    body: ReceiveRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.create")),
):
    """Receive material into a location (goods receipt)."""
    txn = await txn_svc.receive(
        session,
        material_lot_id=body.material_lot_id,
        to_location_id=body.to_location_id,
        quantity=body.quantity,
        reason=body.reason,
        reference_id=body.reference_id,
        reference_type=body.reference_type,
    )
    await session.commit()
    return success_response(InventoryTransactionRead.model_validate(txn).model_dump())


@router.post("/inventory/putaway", status_code=201)
async def putaway_inventory(
    body: PutawayRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.create")),
):
    """Put away material from receiving to a storage location (aisle/bay/tier)."""
    txn = await txn_svc.putaway(
        session,
        material_lot_id=body.material_lot_id,
        from_location_id=body.from_location_id,
        to_location_id=body.to_location_id,
        quantity=body.quantity,
        reason=body.reason,
    )
    await session.commit()
    return success_response(InventoryTransactionRead.model_validate(txn).model_dump())


@router.post("/inventory/pick", status_code=201)
async def pick_inventory(
    body: PickRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.create")),
):
    """Pick material from a storage location for production use."""
    txn = await txn_svc.pick(
        session,
        material_lot_id=body.material_lot_id,
        from_location_id=body.from_location_id,
        to_location_id=body.to_location_id,
        quantity=body.quantity,
        reason=body.reason,
        reference_id=body.reference_id,
        reference_type=body.reference_type,
    )
    await session.commit()
    return success_response(InventoryTransactionRead.model_validate(txn).model_dump())


@router.post("/inventory/move", status_code=201)
async def move_inventory(
    body: MoveRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.create")),
):
    """Move material between any two locations."""
    txn = await txn_svc.move(
        session,
        material_lot_id=body.material_lot_id,
        from_location_id=body.from_location_id,
        to_location_id=body.to_location_id,
        quantity=body.quantity,
        reason=body.reason,
        reference_id=body.reference_id,
        reference_type=body.reference_type,
    )
    await session.commit()
    return success_response(InventoryTransactionRead.model_validate(txn).model_dump())


@router.post("/inventory/consume", status_code=201)
async def consume_inventory(
    body: ConsumeInventoryRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.consume")),
):
    """Consume inventory from a location for WIP."""
    txn = await txn_svc.consume(
        session,
        material_lot_id=body.material_lot_id,
        from_location_id=body.from_location_id,
        quantity=body.quantity,
        reason=body.reason,
        reference_id=body.reference_id,
        reference_type=body.reference_type,
        step_id=body.step_id,
    )
    await session.commit()
    return success_response(InventoryTransactionRead.model_validate(txn).model_dump())


@router.post("/inventory/adjust", status_code=201)
async def adjust_inventory(
    body: AdjustRequest,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("inventory.adjust")),
):
    """Manual inventory adjustment (cycle count correction)."""
    txn = await txn_svc.adjust(
        session,
        material_lot_id=body.material_lot_id,
        location_id=body.location_id,
        quantity=body.quantity,
        reason=body.reason,
    )
    await session.commit()
    return success_response(InventoryTransactionRead.model_validate(txn).model_dump())
