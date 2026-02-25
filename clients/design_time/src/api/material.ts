/**
 * Material Management API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  Material,
  MaterialCreate,
  MaterialUpdate,
  MaterialLot,
  MaterialLotCreate,
  MaterialLotUpdate,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Material Definitions ─────────────────────────────────────────────

export async function fetchMaterials(
  materialType?: string,
): Promise<ApiListResponse<Material>> {
  const params: Record<string, string> = { limit: "200" };
  if (materialType) params.material_type = materialType;
  const { data } = await api.get<ApiListResponse<Material>>("/materials", { params });
  return data;
}

export async function fetchMaterial(id: string): Promise<Material> {
  const { data } = await api.get<ApiResponse<Material>>(`/materials/${id}`);
  return data.data;
}

export async function createMaterial(body: MaterialCreate): Promise<Material> {
  const { data } = await api.post<ApiResponse<Material>>("/materials", body);
  return data.data;
}

export async function updateMaterial(id: string, body: MaterialUpdate): Promise<Material> {
  const { data } = await api.patch<ApiResponse<Material>>(`/materials/${id}`, body);
  return data.data;
}

export async function deleteMaterial(id: string): Promise<void> {
  await api.delete(`/materials/${id}`);
}

// ─── Material Lots ────────────────────────────────────────────────────

export async function fetchMaterialLots(
  materialId?: string,
  status?: string,
): Promise<ApiListResponse<MaterialLot>> {
  const params: Record<string, string> = { limit: "200" };
  if (materialId) params.material_id = materialId;
  if (status) params.status = status;
  const { data } = await api.get<ApiListResponse<MaterialLot>>("/material-lots", {
    params,
  });
  return data;
}

export async function fetchMaterialLot(id: string): Promise<MaterialLot> {
  const { data } = await api.get<ApiResponse<MaterialLot>>(`/material-lots/${id}`);
  return data.data;
}

export async function createMaterialLot(body: MaterialLotCreate): Promise<MaterialLot> {
  const { data } = await api.post<ApiResponse<MaterialLot>>("/material-lots", body);
  return data.data;
}

export async function updateMaterialLot(
  id: string,
  body: MaterialLotUpdate,
): Promise<MaterialLot> {
  const { data } = await api.patch<ApiResponse<MaterialLot>>(
    `/material-lots/${id}`,
    body,
  );
  return data.data;
}
