import api from "./client";
import type {
  ApiResponse,
  Area,
  Equipment,
  EquipmentCurrentState,
  EquipmentStateLog,
  ListResponse,
  ProductionLine,
  Site,
  StateModel,
  WorkCell,
} from "../types";

// ── Physical Model ───────────────────────────────────────────────

export async function fetchSites(): Promise<Site[]> {
  const res = await api.get<ListResponse<Site>>("/sites", { params: { limit: 200 } });
  return res.data.data;
}

export async function fetchAreas(siteId: string): Promise<Area[]> {
  const res = await api.get<ListResponse<Area>>(`/sites/${siteId}/areas`, { params: { limit: 200 } });
  return res.data.data;
}

export async function fetchLines(areaId: string): Promise<ProductionLine[]> {
  const res = await api.get<ListResponse<ProductionLine>>(`/areas/${areaId}/lines`, { params: { limit: 200 } });
  return res.data.data;
}

export async function fetchWorkCells(lineId: string): Promise<WorkCell[]> {
  const res = await api.get<ListResponse<WorkCell>>(`/lines/${lineId}/work-cells`, { params: { limit: 200 } });
  return res.data.data;
}

export async function fetchEquipmentInWorkCell(wcId: string): Promise<Equipment[]> {
  const res = await api.get<ListResponse<Equipment>>(`/work-cells/${wcId}/equipment`, { params: { limit: 200 } });
  return res.data.data;
}

// ── Performance / State Models ───────────────────────────────────

export async function fetchStateModels(): Promise<StateModel[]> {
  const res = await api.get<ApiResponse<StateModel[]>>("/performance/state-models");
  return res.data.data;
}

export async function fetchStateModel(modelId: string): Promise<StateModel> {
  const res = await api.get<ApiResponse<StateModel>>(`/performance/state-models/${modelId}`);
  return res.data.data;
}

// ── Equipment State ──────────────────────────────────────────────

export async function fetchCurrentState(equipId: string): Promise<EquipmentCurrentState> {
  const res = await api.get<ApiResponse<EquipmentCurrentState>>(`/performance/equipment/${equipId}/current-state`);
  return res.data.data;
}

export async function transitionEquipment(
  equipId: string,
  newState: string,
  reasonCode?: string,
  notes?: string,
): Promise<EquipmentStateLog> {
  const res = await api.post<ApiResponse<EquipmentStateLog>>(
    `/performance/equipment/${equipId}/transition`,
    { new_state: newState, reason_code: reasonCode ?? null, notes: notes ?? null },
  );
  return res.data.data;
}

export async function fetchStateHistory(
  equipId: string,
  limit = 50,
): Promise<EquipmentStateLog[]> {
  const res = await api.get<ListResponse<EquipmentStateLog>>("/performance/equipment-states", {
    params: { equipment_id: equipId, limit },
  });
  return res.data.data;
}
