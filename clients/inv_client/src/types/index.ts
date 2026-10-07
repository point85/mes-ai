/* INV-CLIENT TypeScript types — mirrors server Pydantic schemas for inventory management.
   Follows the patterns from wip_client (trimmed types) and dt_client (storage locations).
   Supports tracking by lot number or serial number. */

// ── Tracking Methods ────────────────────────────────────────────────

export const TRACKING_METHODS = ["lot", "serial"] as const;
export type TrackingMethod = (typeof TRACKING_METHODS)[number];

// ── Storage Location (from dt-client) ────────────────────────────────

export const LOCATION_TYPES = [
  "receiving",
  "storage",
  "rip",
  "staging",
  "shipping",
] as const;

export type LocationType = (typeof LOCATION_TYPES)[number];

export interface StorageLocation {
  id: string;
  name: string;
  code: string;
  description: string | null;
  location_type: LocationType;
  aisle: string | null;
  bay: string | null;
  tier: string | null;
  site_id: string | null;
  capacity: number | null;
  capacity_uom_id: string | null;
  capacity_uom_symbol: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StorageLocationCreate {
  name: string;
  code: string;
  description?: string | null;
  location_type?: string;
  aisle?: string | null;
  bay?: string | null;
  tier?: string | null;
  site_id?: string | null;
  capacity?: number | null;
  capacity_uom_id?: string | null;
}

export interface StorageLocationUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  location_type?: string;
  aisle?: string | null;
  bay?: string | null;
  tier?: string | null;
  site_id?: string | null;
  capacity?: number | null;
  capacity_uom_id?: string | null;
}

// ── Material & Material Lot ─────────────────────────────────────────

export interface Material {
  id: string;
  name: string;
  code: string;
  description: string | null;
  material_type: string;
  uom_id: string;
  uom_symbol: string | null;
  revision: string | null;
  shelf_life_days: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialLot {
  id: string;
  material_id: string;
  material_code: string | null;
  material_name: string | null;
  lot_number: string;
  tracking_method: TrackingMethod;
  serial_number: string | null;
  quantity_on_hand: number;
  quantity_reserved: number;
  status: string;
  received_date: string | null;
  expiry_date: string | null;
  supplier: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialLotCreate {
  material_id: string;
  lot_number: string;
  tracking_method: TrackingMethod;
  serial_number?: string | null;
  quantity_on_hand: number;
  received_date?: string | null;
  expiry_date?: string | null;
  supplier?: string | null;
}

export interface MaterialLotUpdate {
  material_id?: string;
  lot_number?: string;
  tracking_method?: TrackingMethod;
  serial_number?: string | null;
  quantity_on_hand?: number;
  received_date?: string | null;
  expiry_date?: string | null;
  supplier?: string | null;
  status?: string;
}

// ── Inventory Balance ────────────────────────────────────────────────

export interface InventoryBalance {
  id: string;
  material_lot_id: string;
  material_lot_code: string | null;
  material_lot_tracking_method: TrackingMethod | null;
  location_id: string;
  location_code: string | null;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Inventory Transaction ────────────────────────────────────────────

export const TRANSACTION_TYPES = [
  "receive",
  "putaway",
  "pick",
  "move",
  "transfer",
  "consume",
  "adjust",
] as const;

export type TransactionType = (typeof TRANSACTION_TYPES)[number];

export interface InventoryTransaction {
  id: string;
  transaction_type: TransactionType;
  material_lot_id: string;
  material_lot_code: string | null;
  material_lot_tracking_method: TrackingMethod | null;
  from_location_id: string | null;
  from_location_code: string | null;
  to_location_id: string | null;
  to_location_code: string | null;
  quantity: number;
  reference_id: string | null;
  reference_type: string | null;
  reason: string | null;
  performed_at: string;
  performed_at_utc: string | null;
  created_at: string;
}

// ── API Payloads ────────────────────────────────────────────────────

export interface ReceivePayload {
  material_lot_id: string;
  to_location_id: string;
  quantity: number;
  reason?: string;
  reference_id?: string;
  reference_type?: string;
}

export interface PutawayPayload {
  material_lot_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  reason?: string;
}

export interface PickPayload {
  material_lot_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  reason?: string;
  reference_id?: string;
  reference_type?: string;
}

export interface TransferPayload {
  material_lot_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  reason?: string;
}

export interface ConsumePayload {
  material_lot_id: string;
  from_location_id: string;
  quantity: number;
  reason?: string;
  reference_id?: string;
  reference_type?: string;
  step_id?: string;
}

export interface AdjustPayload {
  material_lot_id: string;
  location_id: string;
  quantity: number;
  reason: string;
}

// ── Query Parameters ────────────────────────────────────────────────

export interface InventoryBalanceQuery {
  material_lot_id?: string;
  location_id?: string;
  tracking_method?: TrackingMethod;
  limit?: number;
}

export interface InventoryTransactionQuery {
  material_lot_id?: string;
  location_id?: string;
  transaction_type?: TransactionType;
  tracking_method?: TrackingMethod;
  limit?: number;
}

export interface StorageLocationQuery {
  location_type?: LocationType;
  site_id?: string;
  limit?: number;
}