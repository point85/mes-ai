/**
 * Inventory Management API — thin wrappers around axios calls.
 * Follows the wip_client pattern with unwrap helpers.
 */

import api from "./client";
import type {
  StorageLocation,
  StorageLocationCreate,
  StorageLocationUpdate,
  MaterialLot,
  MaterialLotCreate,
  MaterialLotUpdate,
  Material,
  InventoryBalance,
  InventoryTransaction,
  ReceivePayload,
  PutawayPayload,
  PickPayload,
  TransferPayload,
  ConsumePayload,
  AdjustPayload,
  InventoryBalanceQuery,
  InventoryTransactionQuery,
  StorageLocationQuery,
  TrackingMethod,
} from "../types";

// Unwrap { status, data } envelope
function unwrap<T>(res: { data: { data: T } }): T {
  return res.data.data;
}

function unwrapList<T>(res: { data: { data: T[] } }): T[] {
  return res.data.data;
}

// Shared error extraction helper
export function apiErrorMessage(err: unknown): string {
  return (
    (err as { response?: { data?: { error?: { message?: string } } } })?.response
      ?.data?.error?.message ?? "Request failed"
  );
}

// ── Storage Locations ────────────────────────────────────────────────

export const fetchStorageLocations = (params?: StorageLocationQuery) =>
  api
    .get("/storage-locations", { params: { limit: 200, ...params } })
    .then(unwrapList<StorageLocation>);

export const fetchStorageLocation = (id: string) =>
  api.get(`/storage-locations/${id}`).then(unwrap<StorageLocation>);

export const createStorageLocation = (body: StorageLocationCreate) =>
  api.post("/storage-locations", body).then(unwrap<StorageLocation>);

export const updateStorageLocation = (id: string, body: StorageLocationUpdate) =>
  api.patch(`/storage-locations/${id}`, body).then(unwrap<StorageLocation>);

export const deleteStorageLocation = (id: string) =>
  api.delete(`/storage-locations/${id}`);

// ── Material Lots ────────────────────────────────────────────────────

export const fetchMaterialLots = (params?: {
  material_id?: string;
  tracking_method?: TrackingMethod;
  status?: string;
  limit?: number;
}) =>
  api
    .get("/material-lots", { params: { limit: 200, ...params } })
    .then(unwrapList<MaterialLot>);

export const fetchMaterialLot = (id: string) =>
  api.get(`/material-lots/${id}`).then(unwrap<MaterialLot>);

export const fetchMaterialLotByNumber = (lotNumber: string) =>
  api.get(`/material-lots/by-number/${encodeURIComponent(lotNumber)}`).then(unwrap<MaterialLot>);

export const fetchMaterialLotBySerial = (serial: string) =>
  api.get(`/material-lots/by-serial/${encodeURIComponent(serial)}`).then(unwrap<MaterialLot>);

export const createMaterialLot = (body: MaterialLotCreate) =>
  api.post("/material-lots", body).then(unwrap<MaterialLot>);

export const updateMaterialLot = (id: string, body: MaterialLotUpdate) =>
  api.patch(`/material-lots/${id}`, body).then(unwrap<MaterialLot>);

export const deleteMaterialLot = (id: string) =>
  api.delete(`/material-lots/${id}`);

// ── Inventory Balances ───────────────────────────────────────────────

export const fetchInventoryBalances = (params?: InventoryBalanceQuery) =>
  api
    .get("/inventory/balances", { params: { limit: 200, ...params } })
    .then(unwrapList<InventoryBalance>);

export const fetchInventoryBalance = (id: string) =>
  api.get(`/inventory/balances/${id}`).then(unwrap<InventoryBalance>);

// ── Inventory Transactions ───────────────────────────────────────────

export const fetchInventoryTransactions = (params?: InventoryTransactionQuery) =>
  api
    .get("/inventory/transactions", { params: { limit: 200, ...params } })
    .then(unwrapList<InventoryTransaction>);

export const fetchInventoryTransaction = (id: string) =>
  api.get(`/inventory/transactions/${id}`).then(unwrap<InventoryTransaction>);

// ── Core Inventory Operations ────────────────────────────────────────

/**
 * Receive inventory into a location (typically receiving dock).
 * Creates an inventory balance if one doesn't exist.
 */
export const receiveInventory = (payload: ReceivePayload) =>
  api.post("/inventory/receive", payload).then(unwrap<InventoryTransaction>);

/**
 * Put-away inventory from a receiving/staging location to a storage location.
 */
export const putawayInventory = (payload: PutawayPayload) =>
  api.post("/inventory/putaway", payload).then(unwrap<InventoryTransaction>);

/**
 * Pick inventory from a storage location to a staging/shipping location.
 */
export const pickInventory = (payload: PickPayload) =>
  api.post("/inventory/pick", payload).then(unwrap<InventoryTransaction>);

/**
 * Transfer inventory between any two locations.
 * General-purpose move that can be used for any location-to-location transfer.
 */
export const transferInventory = (payload: TransferPayload) =>
  api.post("/inventory/transfer", payload).then(unwrap<InventoryTransaction>);

/**
 * Move inventory (alias for transfer, kept for compatibility).
 */
export const moveInventory = (payload: TransferPayload) =>
  api.post("/inventory/move", payload).then(unwrap<InventoryTransaction>);

/**
 * Consume inventory from a location (e.g., for production consumption).
 */
export const consumeInventory = (payload: ConsumePayload) =>
  api.post("/inventory/consume", payload).then(unwrap<InventoryTransaction>);

/**
 * Adjust inventory quantity at a location (cycle count, damage, etc.).
 */
export const adjustInventory = (payload: AdjustPayload) =>
  api.post("/inventory/adjust", payload).then(unwrap<InventoryTransaction>);

// ── Materials (reference data) ───────────────────────────────────────

export const fetchMaterials = () =>
  api.get("/materials", { params: { limit: 200 } }).then(unwrapList<Material>);