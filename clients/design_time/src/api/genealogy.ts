/**
 * Genealogy / Traceability API — thin wrappers around axios calls.
 */

import api from "./client";
import type { GenealogyRecord, ApiResponse } from "../types";

/** Resolve a serial number → unit UUID via the barcode-scan endpoint. */
async function resolveUnitId(serial: string): Promise<string> {
  const { data } = await api.get<ApiResponse<{ id: string }>>(
    `/units/by-serial/${encodeURIComponent(serial)}`,
  );
  return data.data.id;
}

/** Resolve a lot number → lot UUID via the barcode-scan endpoint. */
async function resolveLotId(lotNumber: string): Promise<string> {
  const { data } = await api.get<ApiResponse<{ id: string }>>(
    `/lots/by-number/${encodeURIComponent(lotNumber)}`,
  );
  return data.data.id;
}

export async function fetchUnitGenealogy(
  serial: string,
): Promise<GenealogyRecord> {
  const unitId = await resolveUnitId(serial);
  const { data } = await api.get<ApiResponse<GenealogyRecord>>(
    `/units/${unitId}/genealogy`,
  );
  return data.data;
}

export async function fetchLotGenealogy(
  lotNumber: string,
): Promise<GenealogyRecord> {
  const lotId = await resolveLotId(lotNumber);
  const { data } = await api.get<ApiResponse<GenealogyRecord>>(
    `/lots/${lotId}/genealogy`,
  );
  return data.data;
}
