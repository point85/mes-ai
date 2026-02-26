/**
 * Genealogy / Traceability API — thin wrappers around axios calls.
 */

import api from "./client";
import type { GenealogyRecord, ApiResponse } from "../types";

export async function fetchUnitGenealogy(
  unitId: string,
): Promise<GenealogyRecord> {
  const { data } = await api.get<ApiResponse<GenealogyRecord>>(
    `/units/${unitId}/genealogy`,
  );
  return data.data;
}

export async function fetchLotGenealogy(
  lotId: string,
): Promise<GenealogyRecord> {
  const { data } = await api.get<ApiResponse<GenealogyRecord>>(
    `/lots/${lotId}/genealogy`,
  );
  return data.data;
}
