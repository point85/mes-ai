/**
 * Physical Model API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  Site,
  SiteCreate,
  SiteUpdate,
  Area,
  AreaCreate,
  AreaUpdate,
  ProductionLine,
  ProductionLineCreate,
  ProductionLineUpdate,
  WorkCenter,
  WorkCenterCreate,
  WorkCenterUpdate,
  Equipment,
  EquipmentCreate,
  EquipmentUpdate,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Sites ────────────────────────────────────────────────────────────

export async function fetchSites(): Promise<ApiListResponse<Site>> {
  const { data } = await api.get<ApiListResponse<Site>>("/sites", {
    params: { limit: "200" },
  });
  return data;
}

export async function fetchSite(id: string): Promise<Site> {
  const { data } = await api.get<ApiResponse<Site>>(`/sites/${id}`);
  return data.data;
}

export async function createSite(body: SiteCreate): Promise<Site> {
  const { data } = await api.post<ApiResponse<Site>>("/sites", body);
  return data.data;
}

export async function updateSite(id: string, body: SiteUpdate): Promise<Site> {
  const { data } = await api.put<ApiResponse<Site>>(`/sites/${id}`, body);
  return data.data;
}

export async function deleteSite(id: string): Promise<void> {
  await api.delete(`/sites/${id}`);
}

// ─── Areas ────────────────────────────────────────────────────────────

export async function fetchAreas(siteId: string): Promise<ApiListResponse<Area>> {
  const { data } = await api.get<ApiListResponse<Area>>(
    `/sites/${siteId}/areas`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function fetchArea(areaId: string): Promise<Area> {
  const { data } = await api.get<ApiResponse<Area>>(`/areas/${areaId}`);
  return data.data;
}

export async function createArea(siteId: string, body: AreaCreate): Promise<Area> {
  const { data } = await api.post<ApiResponse<Area>>(
    `/sites/${siteId}/areas`,
    body,
  );
  return data.data;
}

export async function updateArea(areaId: string, body: AreaUpdate): Promise<Area> {
  const { data } = await api.put<ApiResponse<Area>>(`/areas/${areaId}`, body);
  return data.data;
}

// ─── Production Lines ─────────────────────────────────────────────────

export async function fetchLines(areaId: string): Promise<ApiListResponse<ProductionLine>> {
  const { data } = await api.get<ApiListResponse<ProductionLine>>(
    `/areas/${areaId}/lines`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createLine(
  areaId: string,
  body: ProductionLineCreate,
): Promise<ProductionLine> {
  const { data } = await api.post<ApiResponse<ProductionLine>>(
    `/areas/${areaId}/lines`,
    body,
  );
  return data.data;
}

export async function updateLine(
  lineId: string,
  body: ProductionLineUpdate,
): Promise<ProductionLine> {
  const { data } = await api.put<ApiResponse<ProductionLine>>(
    `/lines/${lineId}`,
    body,
  );
  return data.data;
}

// ─── Work Centers ─────────────────────────────────────────────────────

export async function fetchWorkCenters(
  lineId: string,
): Promise<ApiListResponse<WorkCenter>> {
  const { data } = await api.get<ApiListResponse<WorkCenter>>(
    `/lines/${lineId}/work-centers`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createWorkCenter(
  lineId: string,
  body: WorkCenterCreate,
): Promise<WorkCenter> {
  const { data } = await api.post<ApiResponse<WorkCenter>>(
    `/lines/${lineId}/work-centers`,
    body,
  );
  return data.data;
}

export async function updateWorkCenter(
  wcId: string,
  body: WorkCenterUpdate,
): Promise<WorkCenter> {
  const { data } = await api.put<ApiResponse<WorkCenter>>(
    `/work-centers/${wcId}`,
    body,
  );
  return data.data;
}

// ─── Equipment ────────────────────────────────────────────────────────

export async function fetchEquipment(
  wcId: string,
): Promise<ApiListResponse<Equipment>> {
  const { data } = await api.get<ApiListResponse<Equipment>>(
    `/work-centers/${wcId}/equipment`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createEquipment(
  wcId: string,
  body: EquipmentCreate,
): Promise<Equipment> {
  const { data } = await api.post<ApiResponse<Equipment>>(
    `/work-centers/${wcId}/equipment`,
    body,
  );
  return data.data;
}

export async function updateEquipment(
  equipId: string,
  body: EquipmentUpdate,
): Promise<Equipment> {
  const { data } = await api.put<ApiResponse<Equipment>>(
    `/equipment/${equipId}`,
    body,
  );
  return data.data;
}

export async function updateEquipmentStatus(
  equipId: string,
  status: string,
  reason?: string,
): Promise<Equipment> {
  const { data } = await api.patch<ApiResponse<Equipment>>(
    `/equipment/${equipId}/status`,
    { status, reason },
  );
  return data.data;
}
