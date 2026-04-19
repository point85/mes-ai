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
  WorkCell,
  WorkCellCreate,
  WorkCellUpdate,
  Equipment,
  EquipmentCreate,
  EquipmentUpdate,
  EquipmentMaterial,
  EquipmentMaterialCreate,
  EquipmentMaterialUpdate,
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

export async function fetchAllLines(): Promise<ApiListResponse<ProductionLine>> {
  const { data } = await api.get<ApiListResponse<ProductionLine>>(
    "/lines",
    { params: { limit: "500" } },
  );
  return data;
}

export async function fetchLines(areaId: string): Promise<ApiListResponse<ProductionLine>> {
  const { data } = await api.get<ApiListResponse<ProductionLine>>(
    `/areas/${areaId}/lines`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function fetchLine(lineId: string): Promise<ProductionLine> {
  const { data } = await api.get<ApiResponse<ProductionLine>>(`/lines/${lineId}`);
  return data.data;
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

// ─── Work Cells ──────────────────────────────────────────────────────

export async function fetchAllWorkCells(): Promise<ApiListResponse<WorkCell>> {
  const { data } = await api.get<ApiListResponse<WorkCell>>(
    "/work-cells",
    { params: { limit: "500" } },
  );
  return data;
}

export async function fetchWorkCells(
  lineId: string,
): Promise<ApiListResponse<WorkCell>> {
  const { data } = await api.get<ApiListResponse<WorkCell>>(
    `/lines/${lineId}/work-cells`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function fetchWorkCell(wcId: string): Promise<WorkCell> {
  const { data } = await api.get<ApiResponse<WorkCell>>(`/work-cells/${wcId}`);
  return data.data;
}

export async function createWorkCell(
  lineId: string,
  body: WorkCellCreate,
): Promise<WorkCell> {
  const { data } = await api.post<ApiResponse<WorkCell>>(
    `/lines/${lineId}/work-cells`,
    body,
  );
  return data.data;
}

export async function updateWorkCell(
  wcId: string,
  body: WorkCellUpdate,
): Promise<WorkCell> {
  const { data } = await api.put<ApiResponse<WorkCell>>(
    `/work-cells/${wcId}`,
    body,
  );
  return data.data;
}

// ─── Equipment ────────────────────────────────────────────────────────

export async function fetchAllEquipment(): Promise<ApiListResponse<Equipment>> {
  const { data } = await api.get<ApiListResponse<Equipment>>(
    "/equipment",
    { params: { limit: "200" } },
  );
  return data;
}

export async function fetchEquipment(
  wcId: string,
): Promise<ApiListResponse<Equipment>> {
  const { data } = await api.get<ApiListResponse<Equipment>>(
    `/work-cells/${wcId}/equipment`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createEquipment(
  wcId: string,
  body: EquipmentCreate,
): Promise<Equipment> {
  const { data } = await api.post<ApiResponse<Equipment>>(
    `/work-cells/${wcId}/equipment`,
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


// ─── Equipment–Material Setups ─────────────────────────────────────

export async function fetchEquipmentMaterials(
  equipId: string,
): Promise<ApiListResponse<EquipmentMaterial>> {
  const { data } = await api.get<ApiListResponse<EquipmentMaterial>>(
    `/equipment/${equipId}/materials`,
    { params: { limit: "200" } },
  );
  return data;
}

export async function createEquipmentMaterial(
  equipId: string,
  body: EquipmentMaterialCreate,
): Promise<EquipmentMaterial> {
  const { data } = await api.post<ApiResponse<EquipmentMaterial>>(
    `/equipment/${equipId}/materials`,
    body,
  );
  return data.data;
}

export async function updateEquipmentMaterial(
  emId: string,
  body: EquipmentMaterialUpdate,
): Promise<EquipmentMaterial> {
  const { data } = await api.put<ApiResponse<EquipmentMaterial>>(
    `/equipment-materials/${emId}`,
    body,
  );
  return data.data;
}

export async function deleteEquipmentMaterial(emId: string): Promise<void> {
  await api.delete(`/equipment-materials/${emId}`);
}
