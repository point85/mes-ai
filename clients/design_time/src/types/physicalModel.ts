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
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkCellCreate {
  name: string;
  code: string;
  description?: string | null;
}

export interface WorkCellUpdate {
  name?: string;
  code?: string;
  description?: string | null;
}

// ─── Equipment ────────────────────────────────────────────────────────

export interface Equipment {
  id: string;
  name: string;
  code: string;
  description: string | null;
  work_cell_id: string;
  equipment_type: string | null;
  capabilities: Record<string, unknown> | null;
  equipment_class_id: string | null;
  state_model_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EquipmentCreate {
  name: string;
  code: string;
  description?: string | null;
  equipment_type?: string | null;
  capabilities?: Record<string, unknown> | null;
  equipment_class_id?: string | null;
  state_model_id?: string | null;
}

export interface EquipmentUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  equipment_type?: string | null;
  capabilities?: Record<string, unknown> | null;
  equipment_class_id?: string | null;
  state_model_id?: string | null;
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

// ─── Equipment Class (ISA-95 Part 2) ─────────────────────────────────

export interface EquipmentClass {
  id: string;
  name: string;
  code: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EquipmentClassDetail extends EquipmentClass {
  properties: EquipmentClassProperty[];
  member_count: number;
}

export interface EquipmentClassProperty {
  id: string;
  equipment_class_id: string;
  name: string;
  description: string | null;
  data_type: string;
  uom_id: string | null;
  default_value: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EquipmentClassCreate {
  name: string;
  code: string;
  description?: string | null;
}

export interface EquipmentClassUpdate {
  name?: string;
  code?: string;
  description?: string | null;
}

export interface EquipmentClassPropertyCreate {
  name: string;
  description?: string | null;
  data_type?: string;
  uom_id?: string | null;
  default_value?: string | null;
}

export interface EquipmentClassPropertyUpdate {
  name?: string;
  description?: string | null;
  data_type?: string;
  uom_id?: string | null;
  default_value?: string | null;
}

// ─── Equipment Capability (ISA-95 Part 2) ────────────────────────────

export interface EquipmentCapabilityPropertyCreate {
  class_property_id: string;
  value: string;
}

export interface EquipmentCapabilityPropertyRead {
  id: string;
  capability_id: string;
  class_property_id: string;
  property_name: string | null;
  value: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EquipmentCapabilityCreate {
  equipment_class_id?: string | null;
  capability_type?: string;
  reason?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  properties?: EquipmentCapabilityPropertyCreate[];
}

export interface EquipmentCapabilityRead {
  id: string;
  equipment_id: string;
  equipment_class_id: string | null;
  capability_type: string;
  reason: string | null;
  start_time: string | null;
  end_time: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  properties: EquipmentCapabilityPropertyRead[];
}
