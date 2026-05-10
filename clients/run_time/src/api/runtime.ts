import axios from "axios";
import type {
  Unit, Lot, UnitHistory, LotHistory,
  StepContext, ProductionOrder, Product, Disposition, DispositionCatalog,
  StepEquipmentStatus, BOMItem, Material, MaterialLot, MaterialConsumption,
  InventoryTransaction, InventoryBalance, StorageLocation,
  Site, Area, ProductionLine, WorkCell, Equipment, EquipmentCurrentState,
  GenealogyRecord,
  EquipmentStateLog, ProductionCounter, StateChangeRequest, CounterCreateUpdate,
  DispatchStrategyInfo, DispatchEvaluateResponse,
} from "../types";

const api = axios.create({ baseURL: "/api/v1" });

// Unwrap { status, data } envelope
function unwrap<T>(res: { data: { data: T } }): T {
  return res.data.data;
}

function unwrapList<T>(res: { data: { data: T[] } }): T[] {
  return res.data.data;
}

// ── Units ────────────────────────────────────────────────────────

export const fetchUnits = (params?: { status?: string; order_id?: string; equipment_id?: string }) =>
  api.get("/units", { params }).then(unwrapList<Unit>);

export const fetchUnitBySerial = (serial: string) =>
  api.get(`/units/by-serial/${encodeURIComponent(serial)}`).then(unwrap<Unit>);

export const fetchUnit = (id: string) =>
  api.get(`/units/${id}`).then(unwrap<Unit>);

export const fetchUnitStepContext = (id: string) =>
  api.get(`/units/${id}/step-context`).then(unwrap<StepContext>);

export const fetchUnitHistory = (id: string) =>
  api.get(`/units/${id}/history`).then(unwrap<UnitHistory[]>);

export const startUnit = (id: string, equipmentId?: string) =>
  api.post(`/units/${id}/start`, { equipment_id: equipmentId ?? null }).then(unwrap<Unit>);

export const completeUnit = (id: string, result: string, dataSnapshot?: Record<string, unknown>, disposition?: string) =>
  api.post(`/units/${id}/complete`, { result, data_snapshot: dataSnapshot, disposition: disposition ?? null }).then(unwrap<Unit>);

export const moveUnit = (id: string, opts?: { target_step_id?: string; result?: string; disposition?: string }) =>
  api.post(`/units/${id}/move`, opts ?? null).then(unwrap<Unit>);

export const holdUnit = (id: string, reason: string) =>
  api.post(`/units/${id}/hold`, { reason }).then(unwrap<Unit>);

export const releaseHoldUnit = (id: string, reason: string) =>
  api.post(`/units/${id}/release-hold`, { reason }).then(unwrap<Unit>);

export const scrapUnit = (id: string, reason: string) =>
  api.post(`/units/${id}/scrap`, { reason }).then(unwrap<Unit>);

// ── Lots ─────────────────────────────────────────────────────────

export const fetchLots = (params?: { status?: string; order_id?: string; equipment_id?: string }) =>
  api.get("/lots", { params }).then(unwrapList<Lot>);

export const fetchLotByNumber = (lotNumber: string) =>
  api.get(`/lots/by-number/${encodeURIComponent(lotNumber)}`).then(unwrap<Lot>);

export const fetchLot = (id: string) =>
  api.get(`/lots/${id}`).then(unwrap<Lot>);

export const fetchLotStepContext = (id: string) =>
  api.get(`/lots/${id}/step-context`).then(unwrap<StepContext>);

export const fetchLotHistory = (id: string) =>
  api.get(`/lots/${id}/history`).then(unwrap<LotHistory[]>);

export const startLot = (id: string, equipmentId?: string) =>
  api.post(`/lots/${id}/start`, { equipment_id: equipmentId ?? null }).then(unwrap<Lot>);

export const completeLot = (id: string, quantityOut?: number, quantityScrapped?: number, disposition?: string, dataSnapshot?: Record<string, unknown>) =>
  api.post(`/lots/${id}/complete`, { quantity_out: quantityOut, quantity_scrapped: quantityScrapped, disposition: disposition ?? null, data_snapshot: dataSnapshot ?? null }).then(unwrap<Lot>);

export const moveLot = (id: string, opts?: { target_step_id?: string; result?: string; disposition?: string }) =>
  api.post(`/lots/${id}/move`, opts ?? null).then(unwrap<Lot>);

export const holdLot = (id: string, reason: string) =>
  api.post(`/lots/${id}/hold`, { reason }).then(unwrap<Lot>);

export const releaseHoldLot = (id: string, reason: string) =>
  api.post(`/lots/${id}/release-hold`, { reason }).then(unwrap<Lot>);

export const scrapLot = (id: string, reason: string) =>
  api.post(`/lots/${id}/scrap`, { reason }).then(unwrap<Lot>);

// ── Routing ──────────────────────────────────────────────────────

export const fetchDispositions = (stepId: string) =>
  api.get(`/process-segments/${stepId}/dispositions`).then(unwrap<Disposition[]>);

export const fetchDispositionCatalog = (category?: "route" | "hold" | "scrap" | "release") =>
  api
    .get("/dispositions", { params: category ? { category } : undefined })
    .then(unwrapList<DispositionCatalog>);

// ── Dispatch ─────────────────────────────────────────────────────

export const fetchStepEquipment = (
  stepId: string,
  materialId?: string | null,
  assignedEquipmentId?: string | null,
) =>
  api.get(`/dispatch/step-equipment/${stepId}`, {
    params: {
      ...(materialId ? { material_id: materialId } : {}),
      ...(assignedEquipmentId ? { assigned_equipment_id: assignedEquipmentId } : {}),
    },
  }).then(unwrapList<StepEquipmentStatus>);

export const fetchDispatchStrategies = () =>
  api.get("/dispatch/strategies").then(unwrapList<DispatchStrategyInfo>);

export const evaluateDispatch = (body: {
  unit_id?: string | null;
  lot_id?: string | null;
  strategy?: string | null;
}) => api.post("/dispatch/evaluate", body).then(unwrap<DispatchEvaluateResponse>);

// ── Data Collection ──────────────────────────────────────────────

export const collectDataPoint = (payload: {
  definition_id: string;
  unit_id?: string;
  lot_id?: string;
  value_numeric?: number;
  value_string?: string;
  value_boolean?: boolean;
}) => api.post("/data/collect", payload).then(unwrap<unknown>);

export const collectDataBatch = (items: Array<{
  definition_id: string;
  unit_id?: string;
  lot_id?: string;
  value_numeric?: number;
  value_string?: string;
  value_boolean?: boolean;
}>) => api.post("/data/collect-batch", { items }).then(unwrap<unknown>);

// ── Orders ───────────────────────────────────────────────────────

export const fetchOrders = (params?: { status?: string }) =>
  api.get("/operations-requests", { params }).then(unwrapList<ProductionOrder>);

export const createOrder = (payload: {
  order_number: string;
  product_id: string;
  route_id?: string | null;
  quantity_ordered: number;
  priority?: number;
  erp_reference?: string | null;
  notes?: string | null;
}) => api.post("/operations-requests", payload).then(unwrap<ProductionOrder>);

export const updateOrder = (id: string, payload: Record<string, unknown>) =>
  api.patch(`/operations-requests/${id}`, payload).then(unwrap<ProductionOrder>);

export const deleteOrder = (id: string) =>
  api.delete(`/operations-requests/${id}`);

export const releaseOrder = (orderId: string) =>
  api.post(`/operations-requests/${orderId}/release`).then(unwrap<ProductionOrder>);

export const completeOrder = (orderId: string) =>
  api.post(`/operations-requests/${orderId}/complete`).then(unwrap<ProductionOrder>);

export const closeOrder = (orderId: string) =>
  api.post(`/operations-requests/${orderId}/close`).then(unwrap<ProductionOrder>);

// ── Products (read-only for order creation) ──────────────────────

export const fetchProducts = () =>
  api.get("/products", { params: { limit: 200 } }).then(unwrapList<Product>);

// ── WIP Creation ─────────────────────────────────────────────────

export const createLot = (payload: {
  order_id: string;
  product_id: string;
  quantity: number;
  lot_number?: string;
  material_id?: string;
}) => api.post("/lots", payload).then(unwrap<Lot>);

export const createUnit = (payload: {
  order_id: string;
  product_id: string;
  serial_number?: string;
  material_id?: string;
}) => api.post("/units", payload).then(unwrap<Unit>);

// ── Dashboard ────────────────────────────────────────────────────

export const fetchOrderProgress = (status?: string) =>
  api.get("/dashboard/order-progress", { params: status ? { status } : {} }).then(unwrap<unknown[]>);

export const fetchLineStatus = () =>
  api.get("/dashboard/line-status").then(unwrap<unknown[]>);

export const fetchShiftSummary = (hours = 8) =>
  api.get("/dashboard/shift-summary", { params: { hours } }).then(unwrap<unknown>);

// ── Material Consumption ─────────────────────────────────────────

export const fetchStepBomItems = (stepId: string) =>
  api.get(`/process-segments/${stepId}/bom-items`).then(unwrap<BOMItem[]>);

export const fetchMaterials = () =>
  api.get("/materials").then(unwrapList<Material>);

export const fetchMaterial = (id: string) =>
  api.get(`/materials/${id}`).then(unwrap<Material>);

export const fetchMaterialLots = (materialId?: string, status?: string) =>
  api.get("/material-lots", { params: { ...(materialId ? { material_id: materialId } : {}), ...(status ? { status } : {}) } }).then(unwrapList<MaterialLot>);

export const consumeMaterial = (materialLotId: string, payload: {
  unit_id?: string;
  lot_id?: string;
  step_id?: string;
  quantity_consumed: number;
}) => api.post(`/material-lots/${materialLotId}/consume`, payload).then(unwrap<MaterialConsumption>);

export const fetchConsumedMaterials = (wipType: "unit" | "lot", wipId: string) =>
  api.get(`/${wipType === "unit" ? "units" : "lots"}/${wipId}/consumed-materials`).then(unwrap<MaterialConsumption[]>);

// ── Inventory ────────────────────────────────────────────────────

export const fetchInventoryTransactions = (params?: {
  material_lot_id?: string;
  location_id?: string;
  transaction_type?: string;
  limit?: number;
}) =>
  api.get("/inventory/transactions", { params: { limit: 200, ...params } }).then(unwrapList<InventoryTransaction>);

export const fetchInventoryBalances = (params?: {
  material_lot_id?: string;
  location_id?: string;
}) =>
  api.get("/inventory/balances", { params: { limit: 200, ...params } }).then(unwrapList<InventoryBalance>);

export const fetchStorageLocations = () =>
  api.get("/storage-locations", { params: { limit: 200 } }).then(unwrapList<StorageLocation>);

export const receiveInventory = (payload: {
  material_lot_id: string;
  to_location_id: string;
  quantity: number;
  reason?: string;
  reference_id?: string;
  reference_type?: string;
}) => api.post("/inventory/receive", payload).then(unwrap<InventoryTransaction>);

export const putawayInventory = (payload: {
  material_lot_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  reason?: string;
}) => api.post("/inventory/putaway", payload).then(unwrap<InventoryTransaction>);

export const pickInventory = (payload: {
  material_lot_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  reason?: string;
  reference_id?: string;
  reference_type?: string;
}) => api.post("/inventory/pick", payload).then(unwrap<InventoryTransaction>);

// ── Performance ─────────────────────────────────────────────────

export const fetchEquipmentStates = (equipmentId?: string) => {
  const params: Record<string, string> = { limit: "200" };
  if (equipmentId) params.equipment_id = equipmentId;
  return api.get("/performance/equipment-states", { params }).then(
    (r) => r.data.data as EquipmentStateLog[]
  );
};

export const recordStateChange = (body: StateChangeRequest) =>
  api.post("/performance/equipment-states", body).then(unwrap<EquipmentStateLog>);

export const fetchCounters = (equipmentId?: string, shiftDate?: string) => {
  const params: Record<string, string> = { limit: "200" };
  if (equipmentId) params.equipment_id = equipmentId;
  if (shiftDate) params.shift_date = shiftDate;
  return api.get("/performance/counters", { params }).then(
    (r) => r.data.data as ProductionCounter[]
  );
};

export const createOrUpdateCounter = (body: CounterCreateUpdate) =>
  api.post("/performance/counters", body).then(unwrap<ProductionCounter>);

export const moveInventory = (payload: {
  material_lot_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  reason?: string;
}) => api.post("/inventory/move", payload).then(unwrap<InventoryTransaction>);

export const consumeInventory = (payload: {
  material_lot_id: string;
  from_location_id: string;
  quantity: number;
  reason?: string;
  reference_id?: string;
  reference_type?: string;
  step_id?: string;
}) => api.post("/inventory/consume", payload).then(unwrap<InventoryTransaction>);

export const adjustInventory = (payload: {
  material_lot_id: string;
  location_id: string;
  quantity: number;
  reason: string;
}) => api.post("/inventory/adjust", payload).then(unwrap<InventoryTransaction>);

// ── Physical Model (S95 hierarchy for equipment status tree) ─────

export const fetchSites = () =>
  api.get("/sites", { params: { limit: 200 } }).then(unwrapList<Site>);

export const fetchAreas = (siteId: string) =>
  api.get(`/sites/${siteId}/areas`, { params: { limit: 200 } }).then(unwrapList<Area>);

export const fetchProductionLines = (areaId: string) =>
  api.get(`/areas/${areaId}/lines`, { params: { limit: 200 } }).then(unwrapList<ProductionLine>);

export const fetchWorkCells = (lineId: string) =>
  api.get(`/lines/${lineId}/work-cells`, { params: { limit: 200 } }).then(unwrapList<WorkCell>);

export const fetchEquipmentInWorkCell = (workCellId: string) =>
  api.get(`/work-cells/${workCellId}/equipment`, { params: { limit: 200 } }).then(unwrapList<Equipment>);

export const fetchEquipment = (equipId: string) =>
  api.get(`/equipment/${equipId}`).then(unwrap<Equipment>);

export const fetchEquipmentCurrentState = (equipId: string) =>
  api.get(`/performance/equipment/${equipId}/current-state`).then(unwrap<EquipmentCurrentState>);

// ── Hierarchy traversal helpers ───────────────────────────────────

/** Collect every Equipment leaf under a WorkCell. */
export async function fetchAllEquipmentInWorkCell(wcId: string): Promise<Equipment[]> {
  return fetchEquipmentInWorkCell(wcId);
}

/** Collect every Equipment leaf under a ProductionLine (all work cells). */
export async function fetchAllEquipmentInLine(lineId: string): Promise<Equipment[]> {
  const wcs = await fetchWorkCells(lineId);
  const nested = await Promise.all(wcs.map((wc) => fetchEquipmentInWorkCell(wc.id)));
  return nested.flat();
}

/** Collect every Equipment leaf under an Area (all lines → work cells). */
export async function fetchAllEquipmentInArea(areaId: string): Promise<Equipment[]> {
  const lines = await fetchProductionLines(areaId);
  const nested = await Promise.all(lines.map((l) => fetchAllEquipmentInLine(l.id)));
  return nested.flat();
}

/** Collect every Equipment leaf under a Site (all areas → lines → work cells). */
export async function fetchAllEquipmentInSite(siteId: string): Promise<Equipment[]> {
  const areas = await fetchAreas(siteId);
  const nested = await Promise.all(areas.map((a) => fetchAllEquipmentInArea(a.id)));
  return nested.flat();
}

/** Fetch every Equipment across all sites. */
export async function fetchAllEquipment(): Promise<Equipment[]> {
  const sites = await fetchSites();
  const nested = await Promise.all(sites.map((s) => fetchAllEquipmentInSite(s.id)));
  return nested.flat();
}

export const transitionEquipmentState = (equipId: string, newState: string, notes?: string) =>
  api.post(`/performance/equipment/${equipId}/transition`, { new_state: newState, notes: notes ?? null });

// ── Genealogy / Traceability ─────────────────────────────────────

export const fetchUnitGenealogy = (unitId: string) =>
  api.get(`/units/${unitId}/genealogy`).then(unwrap<GenealogyRecord>);

export const fetchLotGenealogy = (lotId: string) =>
  api.get(`/lots/${lotId}/genealogy`).then(unwrap<GenealogyRecord>);
