import api from "./client";
import type {
  ApiResponse,
  Area,
  Equipment,
  EquipmentCurrentState,
  EquipmentMaterialSetup,
  EquipmentStateLog,
  ListResponse,
  MaterialSetupRead,
  OEEResult,
  ProductionCounterRead,
  ProductionLine,
  Reason,
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

export async function simulateOpcuaState(
  equipId: string,
  value: number,
  tag = "ns=2;s=Equipment1/CurrentState",
): Promise<EquipmentStateLog> {
  const res = await api.post<ApiResponse<EquipmentStateLog>>(
    `/performance/equipment/${equipId}/simulate-opcua-state`,
    { tag, value },
  );
  return res.data.data;
}

export async function simulateMqttState(
  equipId: string,
  state: number,
  reasonCode?: string,
  topic = "mes/equipment/{equipment_id}/state",
): Promise<EquipmentStateLog> {
  const res = await api.post<ApiResponse<EquipmentStateLog>>(
    `/performance/equipment/${equipId}/simulate-mqtt-state`,
    { topic, state, reason_code: reasonCode ?? null },
  );
  return res.data.data;
}

export async function simulateHistorianState(
  equipId: string,
  state: string,
  tagFqn = "Simulated.StateTag",
): Promise<EquipmentStateLog> {
  const res = await api.post<ApiResponse<EquipmentStateLog>>(
    `/performance/equipment/${equipId}/simulate-historian-state`,
    { tag_fqn: tagFqn, state },
  );
  return res.data.data;
}

export async function simulateHistorianCounts(
  equipId: string,
  processedCount: number,
  defectiveCount: number,
  reworkCount = 0,
  tagFqn = "Simulated.CountTag",
): Promise<ProductionCounterRead> {
  const res = await api.post<ApiResponse<ProductionCounterRead>>(
    `/performance/equipment/${equipId}/simulate-historian-counts`,
    { tag_fqn: tagFqn, processed_count: processedCount, defective_count: defectiveCount, rework_count: reworkCount },
  );
  return res.data.data;
}

/**
 * Look up the AVEVA Historian equipment_mappings for a given equipment ID.
 * Returns the matching mapping object or null if not configured.
 */
export async function fetchHistorianMapping(
  equipId: string,
): Promise<{ equipment_id: string; state_tag_fqn: string; state_model_id: string; tag_prefix?: string } | null> {
  try {
    const res = await api.get<ApiResponse<{
      config_values: Record<string, unknown>;
      parameter_values: Record<string, unknown>;
    }>>("/plugins/aveva-historian");
    const detail = res.data.data;
    const raw =
      detail.config_values?.equipment_mappings ??
      detail.parameter_values?.equipment_mappings;
    let mappings: Array<Record<string, string>> = [];
    if (typeof raw === "string") {
      try { mappings = JSON.parse(raw); } catch { /* ignore */ }
    } else if (Array.isArray(raw)) {
      mappings = raw;
    }
    return mappings.find((m) => m.equipment_id === equipId) ?? null;
  } catch {
    return null; // Plugin not installed or not accessible
  }
}

export async function simulateMqttCounts(
  equipId: string,
  processedCount: number,
  defectiveCount: number,
  reworkCount = 0,
  topic = "mes/equipment/{equipment_id}/counts",
): Promise<ProductionCounterRead> {
  const res = await api.post<ApiResponse<ProductionCounterRead>>(
    `/performance/equipment/${equipId}/simulate-mqtt-counts`,
    { topic, processed_count: processedCount, defective_count: defectiveCount, rework_count: reworkCount },
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

// ── Reasons ──────────────────────────────────────────────────────

export async function fetchReasons(): Promise<Reason[]> {
  const res = await api.get<ApiResponse<Reason[]>>("/performance/reasons");
  return res.data.data;
}

// ── OEE Calculation ──────────────────────────────────────────────

export async function fetchOEE(
  equipId: string,
  periodStart: string,
  periodEnd: string,
): Promise<OEEResult> {
  const res = await api.get<ApiResponse<OEEResult>>("/performance/oee", {
    params: { equipment_id: equipId, period_start: periodStart, period_end: periodEnd },
  });
  return res.data.data;
}

// ── Bulk equipment fetch (all in a site) ─────────────────────────

// ── Production Counters ──────────────────────────────────────────

export async function incrementCounter(
  equipmentId: string,
  goodDelta: number,
  rejectDelta: number,
  reworkDelta = 0,
  source = "simulator",
): Promise<ProductionCounterRead> {
  const res = await api.post<ApiResponse<ProductionCounterRead>>(
    "/performance/counters/increment",
    {
      equipment_id: equipmentId,
      good_delta: goodDelta,
      reject_delta: rejectDelta,
      rework_delta: reworkDelta,
      source,
    },
  );
  return res.data.data;
}

export async function fetchCounters(
  equipmentId: string,
): Promise<ProductionCounterRead[]> {
  const res = await api.get<ListResponse<ProductionCounterRead>>(
    "/performance/counters",
    { params: { equipment_id: equipmentId, limit: 10 } },
  );
  return res.data.data;
}

// ── Bulk equipment fetch (all in a site) ─────────────────────────

export async function fetchAllEquipment(): Promise<Equipment[]> {
  // For the simulator, fetch equipment across the whole hierarchy.
  // We walk sites → areas → lines → work-cells → equipment.
  const sites = await fetchSites();
  const allEquipment: Equipment[] = [];
  for (const site of sites) {
    const areas = await fetchAreas(site.id);
    for (const area of areas) {
      const lines = await fetchLines(area.id);
      for (const line of lines) {
        const wcs = await fetchWorkCells(line.id);
        for (const wc of wcs) {
          const eqs = await fetchEquipmentInWorkCell(wc.id);
          allEquipment.push(...eqs);
        }
      }
    }
  }
  return allEquipment;
}

// ── Equipment Material Setups ────────────────────────────────────

export async function fetchEquipmentMaterials(
  equipId: string,
): Promise<EquipmentMaterialSetup[]> {
  const res = await api.get<ListResponse<EquipmentMaterialSetup>>(
    `/equipment/${equipId}/materials`,
    { params: { limit: 200 } },
  );
  return res.data.data;
}

export async function fetchMaterialSetup(
  equipId: string,
): Promise<MaterialSetupRead> {
  const res = await api.get<ApiResponse<MaterialSetupRead>>(
    `/equipment/${equipId}/material-setup`,
  );
  return res.data.data;
}

export async function setMaterialSetup(
  equipId: string,
  equipmentMaterialId: string,
  jobNumber?: string | null,
): Promise<MaterialSetupRead> {
  const res = await api.post<ApiResponse<MaterialSetupRead>>(
    `/equipment/${equipId}/material-setup`,
    { equipment_material_id: equipmentMaterialId, job_number: jobNumber ?? null },
  );
  return res.data.data;
}

export async function clearMaterialSetup(
  equipId: string,
): Promise<void> {
  await api.delete(`/equipment/${equipId}/material-setup`);
}
