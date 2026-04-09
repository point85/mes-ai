/* RT-CLIENT TypeScript types — mirrors server Pydantic schemas */

export interface Unit {
  id: string;
  serial_number: string;
  order_id: string;
  product_id: string;
  material_id: string | null;
  current_step_id: string | null;
  current_step_name: string | null;
  current_equipment_id: string | null;
  status: "queued" | "in_process" | "completed" | "scrapped" | "on_hold";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Lot {
  id: string;
  lot_number: string;
  order_id: string;
  product_id: string;
  quantity: number;
  material_id: string | null;
  current_step_id: string | null;
  current_step_name: string | null;
  current_equipment_id: string | null;
  status: "queued" | "in_process" | "completed" | "scrapped" | "on_hold";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UnitHistory {
  id: string;
  unit_id: string;
  step_id: string;
  equipment_id: string | null;
  entered_at: string;
  exited_at: string | null;
  result: string | null;
  operator_id: string | null;
  data_snapshot: Record<string, unknown> | null;
  created_at: string;
}

export interface LotHistory {
  id: string;
  lot_id: string;
  step_id: string;
  equipment_id: string | null;
  entered_at: string;
  exited_at: string | null;
  quantity_in: number;
  quantity_out: number;
  quantity_scrapped: number;
  operator_id: string | null;
  created_at: string;
}

export interface RouteStep {
  id: string;
  route_id: string;
  name: string;
  code: string;
  description: string | null;
  step_type: string;
  sequence: number;
  erp_operation_number: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StepParameter {
  id: string;
  step_id: string;
  name: string;
  code: string;
  data_type: string;
  uom: string | null;
  lower_limit: number | null;
  upper_limit: number | null;
  target_value: number | null;
  is_required: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DataDefinition {
  id: string;
  name: string;
  code: string;
  description: string | null;
  data_type: string;
  uom: string | null;
  step_id: string | null;
  source: string;
  is_required: boolean;
  enum_values: string | null;
  lower_limit: number | null;
  upper_limit: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QualityTest {
  id: string;
  name: string;
  code: string;
  description: string | null;
  test_type: string;
  step_id: string | null;
  parameters: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Disposition {
  label: string;
  to_step_id: string;
}

export interface StepContext {
  wip_type: "unit" | "lot";
  wip: Unit | Lot;
  step: RouteStep | null;
  step_parameters: StepParameter[];
  data_definitions: DataDefinition[];
  quality_tests: QualityTest[];
  dispositions: Disposition[];
  route_steps: RouteStep[];
}

export interface ProductionOrder {
  id: string;
  order_number: string;
  product_id: string;
  route_id: string | null;
  quantity_ordered: number;
  quantity_completed: number;
  quantity_scrapped: number;
  status: string;
  priority: number;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  erp_reference: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrderProgress {
  order_id: string;
  order_number: string;
  product_id: string;
  status: string;
  quantity_ordered: number;
  quantity_completed: number;
  quantity_scrapped: number;
  units_queued: number;
  units_in_process: number;
  units_completed: number;
  units_on_hold: number;
  units_scrapped: number;
  lots_queued: number;
  lots_in_process: number;
  lots_completed: number;
  lots_on_hold: number;
  lots_scrapped: number;
}

export interface MESEvent {
  event_type: string;
  source: string;
  payload: Record<string, unknown>;
  timestamp: string;
  event_id: string;
}

export interface StepEquipmentStatus {
  equipment_id: string;
  equipment_code: string;
  equipment_name: string | null;
  dispatch_category: string | null;
  state_model: string | null;
  state: string | null;
  queue_depth: number;
  max_queue_depth: number | null;
  has_spare_capacity: boolean;
  material_setup: boolean;
  is_assigned: boolean;
}

// ── Material Management ──────────────────────────────────────────

export interface BOMItem {
  id: string;
  bom_id: string;
  material_code: string;
  quantity: number;
  uom: string;
  position: number;
  route_step_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Material {
  id: string;
  name: string;
  code: string;
  description: string | null;
  material_type: string;
  uom: string;
  revision: string | null;
  shelf_life_days: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

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

export interface MaterialConsumption {
  id: string;
  material_lot_id: string;
  unit_id: string | null;
  lot_id: string | null;
  step_id: string | null;
  quantity_consumed: number;
  consumed_at: string;
  consumed_at_utc: string | null;
  created_at: string;
  created_at_utc: string | null;
}
