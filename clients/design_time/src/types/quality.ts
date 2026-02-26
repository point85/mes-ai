/**
 * Quality Management: TypeScript types mirroring server Pydantic schemas.
 */

// ─── Quality Test ─────────────────────────────────────────────────────

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

export interface QualityTestCreate {
  name: string;
  code: string;
  description?: string | null;
  test_type?: string;
  step_id?: string | null;
  parameters?: Record<string, unknown> | null;
}

export interface QualityTestUpdate {
  name?: string;
  code?: string;
  description?: string | null;
  test_type?: string;
  step_id?: string | null;
  parameters?: Record<string, unknown> | null;
}

// ─── Test Result ──────────────────────────────────────────────────────

export interface TestResult {
  id: string;
  test_id: string;
  unit_id: string | null;
  lot_id: string | null;
  result: string;
  measured_values: Record<string, unknown> | null;
  operator_id: string | null;
  equipment_id: string | null;
  tested_at: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecordResultRequest {
  test_id: string;
  unit_id?: string | null;
  lot_id?: string | null;
  result: string;
  measured_values?: Record<string, unknown> | null;
  operator_id?: string | null;
  equipment_id?: string | null;
  tested_at: string;
  notes?: string | null;
}

// ─── Non-Conformance ──────────────────────────────────────────────────

export interface NonConformance {
  id: string;
  unit_id: string | null;
  lot_id: string | null;
  step_id: string | null;
  nc_type: string;
  description: string;
  disposition: string | null;
  status: string;
  resolved_at: string | null;
  resolved_by_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface NonConformanceCreate {
  unit_id?: string | null;
  lot_id?: string | null;
  step_id?: string | null;
  nc_type: string;
  description: string;
}

export interface NonConformanceUpdate {
  status?: string;
  disposition?: string;
  resolved_by_id?: string | null;
  description?: string;
}
