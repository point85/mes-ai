/**
 * Inventory Management: TypeScript types mirroring server Pydantic schemas.
 */

// ─── Storage Location ─────────────────────────────────────────────────

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

// ─── Inventory Balance ────────────────────────────────────────────────

export interface InventoryBalance {
  id: string;
  material_lot_id: string;
  location_id: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Inventory Transaction ────────────────────────────────────────────

export const TRANSACTION_TYPES = [
  "receive",
  "putaway",
  "pick",
  "move",
  "consume",
  "adjust",
] as const;

export type TransactionType = (typeof TRANSACTION_TYPES)[number];

export interface InventoryTransaction {
  id: string;
  transaction_type: TransactionType;
  material_lot_id: string;
  from_location_id: string | null;
  to_location_id: string | null;
  quantity: number;
  reference_id: string | null;
  reference_type: string | null;
  reason: string | null;
  performed_at: string;
  performed_at_utc: string | null;
  created_at: string;
}
