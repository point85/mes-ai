import axios from "axios";
import type {
  Unit, Lot, UnitHistory, LotHistory,
  StepContext, ProductionOrder, Disposition,
  StepEquipmentStatus,
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

// ── Dashboard ────────────────────────────────────────────────────

export const fetchOrderProgress = (status?: string) =>
  api.get("/dashboard/order-progress", { params: status ? { status } : {} }).then(unwrap<unknown[]>);

export const fetchLineStatus = () =>
  api.get("/dashboard/line-status").then(unwrap<unknown[]>);

export const fetchShiftSummary = (hours = 8) =>
  api.get("/dashboard/shift-summary", { params: { hours } }).then(unwrap<unknown>);
