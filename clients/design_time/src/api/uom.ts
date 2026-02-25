/**
 * UOM API functions — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  UoM,
  UoMCreate,
  UoMUpdate,
  ConversionRequest,
  ConversionResult,
  ApiResponse,
  ApiListResponse,
} from "../types";

export async function fetchUoMs(uomType?: string): Promise<ApiListResponse<UoM>> {
  const params: Record<string, string> = { limit: "200" };
  if (uomType) params.type = uomType;
  const { data } = await api.get<ApiListResponse<UoM>>("/uom", { params });
  return data;
}

export async function fetchUoM(id: string): Promise<UoM> {
  const { data } = await api.get<ApiResponse<UoM>>(`/uom/${id}`);
  return data.data;
}

export async function createUoM(body: UoMCreate): Promise<UoM> {
  const { data } = await api.post<ApiResponse<UoM>>("/uom", body);
  return data.data;
}

export async function updateUoM(id: string, body: UoMUpdate): Promise<UoM> {
  const { data } = await api.patch<ApiResponse<UoM>>(`/uom/${id}`, body);
  return data.data;
}

export async function deleteUoM(id: string): Promise<void> {
  await api.delete(`/uom/${id}`);
}

export async function convertUoM(body: ConversionRequest): Promise<ConversionResult> {
  const { data } = await api.post<ApiResponse<ConversionResult>>("/uom/convert", body);
  return data.data;
}
