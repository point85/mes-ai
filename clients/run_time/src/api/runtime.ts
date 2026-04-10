import axios from "axios";
import type {
  Unit, Lot, UnitHistory, LotHistory,
  StepContext, ProductionOrder, Disposition,
  StepEquipmentStatus, BOMItem, Material, MaterialLot, MaterialConsumption,
  InventoryTransaction, StorageLocation,
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

export const fetchUnits = (params?: { status?: string; order_id?: string }) =>
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
  api.post(`/units/${id}/start`, equipmentId ? { equipment_id: equipmentId } : null).then(unwrap<Unit>);

export const completeUnit = (id: string, result: string, dataSnapshot?: Record<string, unknown>) =>
  api.post(`/units/${id}/complete`, { result, data_snapshot: dataSnapshot }).then(unwrap<Unit>);

export const moveUnit = (id: string, opts?: { target_step_id?: string; result?: string; disposition?: string }) =>
  api.post(`/units/${id}/move`, opts ?? null).then(unwrap<Unit>);

export const holdUnit = (id: string, reason: string) =>
  api.post(`/units/${id}/hold`, { reason }).then(unwrap<Unit>);

export const releaseHoldUnit = (id: string) =>
  api.post(`/units/${id}/release-hold`).then(unwrap<Unit>);

export const scrapUnit = (id: string, reason: string) =>
  api.post(`/units/${id}/scrap`, { reason }).then(unwrap<Unit>);

// ── Lots ─────────────────────────────────────────────────────────

export const fetchLots = (params?: { status?: string; order_id?: string }) =>
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
  api.post(`/lots/${id}/start`, equipmentId ? { equipment_id: equipmentId } : null).then(unwrap<Lot>);

export const completeLot = (id: string, quantityOut?: number, quantityScrapped?: number) =>
  api.post(`/lots/${id}/complete`, { quantity_out: quantityOut, quantity_scrapped: quantityScrapped }).then(unwrap<Lot>);

export const moveLot = (id: string, opts?: { target_step_id?: string; result?: string; disposition?: string }) =>
  api.post(`/lots/${id}/move`, opts ?? null).then(unwrap<Lot>);

export const holdLot = (id: string, reason: string) =>
  api.post(`/lots/${id}/hold`, { reason }).then(unwrap<Lot>);

export const releaseHoldLot = (id: string) =>
  api.post(`/lots/${id}/release-hold`).then(unwrap<Lot>);

export const scrapLot = (id: string, reason: string) =>
  api.post(`/lots/${id}/scrap`, { reason }).then(unwrap<Lot>);

// ── Routing ──────────────────────────────────────────────────────

export const fetchDispositions = (stepId: string) =>
  api.get(`/steps/${stepId}/dispositions`).then(unwrap<Disposition[]>);

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

// ── Quality ──────────────────────────────────────────────────────

export const recordQualityResult = (payload: {
  test_id: string;
  unit_id?: string;
  lot_id?: string;
  result: "pass" | "fail";
  measured_values?: Record<string, unknown>;
  tested_at: string;
  notes?: string;
}) => api.post("/quality/results", payload).then(unwrap<unknown>);

// ── Orders ───────────────────────────────────────────────────────

export const fetchOrders = (params?: { status?: string }) =>
  api.get("/orders", { params }).then(unwrapList<ProductionOrder>);

export const releaseOrder = (orderId: string) =>
  api.post(`/orders/${orderId}/release`).then(unwrap<ProductionOrder>);

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
  api.get(`/steps/${stepId}/bom-items`).then(unwrap<BOMItem[]>);

export const fetchMaterials = () =>
  api.get("/materials").then(unwrapList<Material>);

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

export const fetchStorageLocations = () =>
  api.get("/storage-locations", { params: { limit: 200 } }).then(unwrapList<StorageLocation>);
