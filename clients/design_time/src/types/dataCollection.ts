/**
 * Data Collection: TypeScript types mirroring server Pydantic schemas.
 */

// ─── Data Definition ──────────────────────────────────────────────────

export interface DataDefinition {
  id: string;
  name: string;
  code: string;
  description: string | null;
  data_type: string;
  uom_id: string | null;
  uom_symbol: string | null;
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

export interface DataDefinitionCreate {
  name: string;
  code: string;
  description?: string | null;
  data_type?: string;
  uom_id?: string | null;
  step_id?: string | null;
  source?: string;
  is_required?: boolean;
  enum_values?: string | null;
  lower_limit?: number | null;
  upper_limit?: number | null;
}

export interface DataDefinitionUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  data_type?: string;
  uom_id?: string | null;
  step_id?: string | null;
  source?: string;
  is_required?: boolean;
  enum_values?: string | null;
  lower_limit?: number | null;
  upper_limit?: number | null;
}

// ─── Data Point ───────────────────────────────────────────────────────

export interface DataPoint {
  id: string;
  definition_id: string;
  unit_id: string | null;
  lot_id: string | null;
  value_numeric: number | null;
  value_string: string | null;
  value_boolean: boolean | null;
  collected_at: string;
  source_equipment_id: string | null;
  operator_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
