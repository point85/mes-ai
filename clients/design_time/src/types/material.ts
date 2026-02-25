/**
 * Material Management: TypeScript types mirroring server Pydantic schemas.
 */

// ─── Material Definition ──────────────────────────────────────────────

export interface Material {
  id: string;
  name: string;
  code: string;
  description: string | null;
  material_type: string;
  uom: string;
  shelf_life_days: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialCreate {
  name: string;
  code: string;
  description?: string | null;
  material_type?: string;
  uom?: string;
  shelf_life_days?: number | null;
}

export interface MaterialUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  material_type?: string;
  uom?: string;
  shelf_life_days?: number | null;
}

// ─── Material Lot ─────────────────────────────────────────────────────

export interface MaterialLot {
  id: string;
  material_id: string;
  lot_number: string;
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
  quantity_on_hand: number;
  received_date?: string | null;
  expiry_date?: string | null;
  supplier?: string | null;
}

export interface MaterialLotUpdate {
  lot_number?: string;
  quantity_on_hand?: number;
  received_date?: string | null;
  expiry_date?: string | null;
  supplier?: string | null;
  status?: string;
}

// ─── Consumption ──────────────────────────────────────────────────────

export interface Consumption {
  id: string;
  material_lot_id: string;
  unit_id: string | null;
  lot_id: string | null;
  step_id: string | null;
  quantity_consumed: number;
  consumed_at: string;
  created_at: string;
}
