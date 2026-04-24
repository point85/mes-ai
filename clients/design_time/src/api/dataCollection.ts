/**
 * Data Collection API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  DataDefinition,
  DataDefinitionCreate,
  DataDefinitionUpdate,
  DataPoint,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Data Definitions ─────────────────────────────────────────────────

export async function fetchDataDefinitions(
  dataType?: string,
  source?: string,
  opts?: { stepId?: string; unassigned?: boolean },
): Promise<ApiListResponse<DataDefinition>> {
  const params: Record<string, string> = { limit: "200" };
  if (dataType) params.data_type = dataType;
  if (source) params.source = source;
  if (opts?.stepId) params.step_id = opts.stepId;
  if (opts?.unassigned) params.unassigned = "true";
  const { data } = await api.get<ApiListResponse<DataDefinition>>(
    "/data/definitions",
    { params },
  );
  return data;
}

export async function fetchDataDefinition(id: string): Promise<DataDefinition> {
  const { data } = await api.get<ApiResponse<DataDefinition>>(
    `/data/definitions/${id}`,
  );
  return data.data;
}

export async function createDataDefinition(
  body: DataDefinitionCreate,
): Promise<DataDefinition> {
  const { data } = await api.post<ApiResponse<DataDefinition>>(
    "/data/definitions",
    body,
  );
  return data.data;
}

export async function updateDataDefinition(
  id: string,
  body: DataDefinitionUpdate,
): Promise<DataDefinition> {
  const { data } = await api.patch<ApiResponse<DataDefinition>>(
    `/data/definitions/${id}`,
    body,
  );
  return data.data;
}

export async function deleteDataDefinition(id: string): Promise<void> {
  await api.delete(`/data/definitions/${id}`);
}

// ─── Data Points (read-only in design-time) ───────────────────────────

export async function fetchDataPoints(
  definitionId?: string,
  unitId?: string,
): Promise<ApiListResponse<DataPoint>> {
  const params: Record<string, string> = { limit: "200" };
  if (definitionId) params.definition_id = definitionId;
  if (unitId) params.unit_id = unitId;
  const { data } = await api.get<ApiListResponse<DataPoint>>("/data/points", {
    params,
  });
  return data;
}
