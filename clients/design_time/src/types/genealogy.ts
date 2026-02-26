/**
 * Genealogy / Traceability: TypeScript types mirroring server Pydantic schemas.
 */

export interface GenealogyStepRecord {
  step_id: string | null;
  step_name: string | null;
  entered_at: string | null;
  exited_at: string | null;
  result: string | null;
  equipment_id: string | null;
  data_snapshot: Record<string, unknown> | null;
}

export interface GenealogyMaterialRecord {
  material_lot_id: string;
  material_code: string | null;
  material_name: string | null;
  lot_number: string | null;
  quantity_consumed: number;
  consumed_at: string;
  step_id: string | null;
}

export interface GenealogyTestRecord {
  result_id: string;
  test_code: string | null;
  test_name: string | null;
  result: string;
  measured_values: Record<string, unknown> | null;
  tested_at: string;
  equipment_id: string | null;
}

export interface GenealogyDataRecord {
  data_point_id: string;
  definition_code: string | null;
  definition_name: string | null;
  value_numeric: number | null;
  value_string: string | null;
  value_boolean: boolean | null;
  collected_at: string;
}

export interface GenealogyRecord {
  unit_id: string | null;
  lot_id: string | null;
  serial_number: string | null;
  lot_number: string | null;
  order_id: string | null;
  product_id: string | null;
  status: string | null;
  steps: GenealogyStepRecord[];
  materials: GenealogyMaterialRecord[];
  test_results: GenealogyTestRecord[];
  data_points: GenealogyDataRecord[];
}
