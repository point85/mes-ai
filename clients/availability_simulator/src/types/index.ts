/* Shared type definitions matching the MES REST API schemas. */

export interface Site {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  is_active: boolean;
}

export interface Area {
  id: string;
  name: string;
  code: string;
  site_id: string;
  description?: string | null;
  is_active: boolean;
}

export interface ProductionLine {
  id: string;
  name: string;
  code: string;
  area_id: string;
  description?: string | null;
  is_active: boolean;
}

export interface WorkCell {
  id: string;
  name: string;
  code: string;
  line_id: string;
  description?: string | null;
  is_active: boolean;
}

export interface Equipment {
  id: string;
  name: string;
  code: string;
  work_cell_id: string;
  equipment_type?: string | null;
  state_model_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StateDefinition {
  name: string;
  display_name?: string | null;
  dispatch_category: string;
  oee_bucket: string;
}

export interface TransitionDefinition {
  from_state: string;
  to_state: string;
  trigger?: string | null;
}

export interface StateModel {
  id: string;
  model_id: string;
  name: string;
  description?: string | null;
  initial_state: string;
  states: StateDefinition[];
  transitions: TransitionDefinition[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EquipmentCurrentState {
  equipment_id: string;
  state_model: string;
  state: string;
  dispatch_category: string;
  oee_bucket: string;
  started_at?: string | null;
  valid_transitions: TransitionDefinition[];
}

export interface EquipmentStateLog {
  id: string;
  equipment_id: string;
  state_model: string;
  state: string;
  sub_state?: string | null;
  dispatch_category: string;
  oee_bucket: string;
  reason_code?: string | null;
  notes?: string | null;
  started_at: string;
  ended_at?: string | null;
}

export interface Reason {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  oee_bucket: string;
  parent_id?: string | null;
  is_active: boolean;
}

/** Standard MES API envelope. */
export interface ApiResponse<T> {
  data: T;
  meta?: Record<string, unknown>;
}

/** List envelope with pagination metadata. */
export interface ListResponse<T> {
  data: T[];
  meta: {
    cursor?: string | null;
    limit: number;
    has_more: boolean;
  };
}
