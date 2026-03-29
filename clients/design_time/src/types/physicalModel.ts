/**
 * Physical Model: TypeScript types mirroring server Pydantic schemas.
 * Hierarchy: Site → Area → ProductionLine → WorkCell → Equipment
 */

// ─── Site ──────────────────────────────────────────────────────────────

export interface Site {
  id: string;
  name: string;
  code: string;
  description: string | null;
  timezone: string | null;
  address: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SiteCreate {
  name: string;
  code: string;
  description?: string | null;
  timezone?: string | null;
  address?: string | null;
}

export interface SiteUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  timezone?: string | null;
  address?: string | null;
}

// ─── Area ──────────────────────────────────────────────────────────────

export interface Area {
  id: string;
  name: string;
  code: string;
  description: string | null;
  site_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AreaCreate {
  name: string;
  code: string;
  description?: string | null;
}

export interface AreaUpdate {
  name?: string;
  code?: string;
  description?: string | null;
}

// ─── Production Line ──────────────────────────────────────────────────

export interface ProductionLine {
  id: string;
  name: string;
  code: string;
  description: string | null;
  area_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductionLineCreate {
  name: string;
  code: string;
  description?: string | null;
}

export interface ProductionLineUpdate {
  name?: string;
  code?: string;
  description?: string | null;
}

// ─── Work Cell ───────────────────────────────────────────────────────

export interface WorkCell {
  id: string;
  name: string;
  code: string;
  description: string | null;
  line_id: string;
  wc_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkCellCreate {
  name: string;
  code: string;
  description?: string | null;
  wc_type?: string;
}

export interface WorkCellUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  wc_type?: string;
}

// ─── Equipment ────────────────────────────────────────────────────────

export interface Equipment {
  id: string;
  name: string;
  code: string;
  description: string | null;
  work_cell_id: string;
  equipment_type: string | null;
  status: string;
  capabilities: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EquipmentCreate {
  name: string;
  code: string;
  description?: string | null;
  equipment_type?: string | null;
  status?: string;
  capabilities?: Record<string, unknown> | null;
}

export interface EquipmentUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  equipment_type?: string | null;
  capabilities?: Record<string, unknown> | null;
}

// ─── Equipment–Material Setup ────────────────────────────────────────

export interface EquipmentMaterial {
  id: string;
  equipment_id: string;
  material_id: string;
  design_speed: number;
  design_speed_uom: string;
  reject_uom: string;
  target_oee: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EquipmentMaterialCreate {
  material_id: string;
  design_speed: number;
  design_speed_uom: string;
  reject_uom: string;
  target_oee: number;
}

export interface EquipmentMaterialUpdate {
  design_speed?: number;
  design_speed_uom?: string;
  reject_uom?: string;
  target_oee?: number;
}
