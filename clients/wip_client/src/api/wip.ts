import axios from "axios";
import type {
  Unit,
  Lot,
  Product,
  StepContext,
  StepEquipmentStatus,
  BOMItem,
  Material,
  MaterialLot,
  MaterialConsumption,
  DataPoint,
  StepParameterValue,
  DispositionCatalog,
} from "../types";

const api = axios.create({ baseURL: "/api/v1" });

// Unwrap { status, data } envelope
function unwrap<T>(res: { data: { data: T } }): T {
  return res.data.data;
}

function unwrapList<T>(res: { data: { data: T[] } }): T[] {
  return res.data.data;
}

// Shared error extraction helper (FR10)
export function apiErrorMessage(err: unknown): string {
  return (
    (err as { response?: { data?: { error?: { message?: string } } } })?.response
      ?.data?.error?.message ?? "Request failed"
  );
}

// ── Lookup by identifier ─────────────────────────────────────────

export const fetchUnitBySerial = (serial: string) =>
  api.get(`/units/by-serial/${encodeURIComponent(serial)}`).then(unwrap<Unit>);

export const fetchLotByNumber = (lotNumber: string) =>
  api.get(`/lots/by-number/${encodeURIComponent(lotNumber)}`).then(unwrap<Lot>);

// ── Dispositions ─────────────────────────────────────────────────

export const fetchDispositionCatalog = (
  category?: "route" | "hold" | "scrap" | "release",
) =>
  api
    .get("/dispositions", { params: category ? { category } : undefined })
    .then(unwrapList<DispositionCatalog>);

// ── Step context ─────────────────────────────────────────────────

export const fetchUnitStepContext = (id: string) =>
  api.get(`/units/${id}/step-context`).then(unwrap<StepContext>);

export const fetchLotStepContext = (id: string) =>
  api.get(`/lots/${id}/step-context`).then(unwrap<StepContext>);

// ── Equipment at step ────────────────────────────────────────────

export const fetchStepEquipment = (
  stepId: string,
  materialId?: string | null,
  assignedEquipmentId?: string | null,
) =>
  api
    .get(`/dispatch/step-equipment/${stepId}`, {
      params: {
        ...(materialId ? { material_id: materialId } : {}),
        ...(assignedEquipmentId ? { assigned_equipment_id: assignedEquipmentId } : {}),
      },
    })
    .then(unwrapList<StepEquipmentStatus>);

// ── Start ────────────────────────────────────────────────────────

export const startUnit = (id: string, equipmentId?: string) =>
  api.post(`/units/${id}/start`, { equipment_id: equipmentId ?? null }).then(unwrap<Unit>);

export const startLot = (id: string, equipmentId?: string) =>
  api.post(`/lots/${id}/start`, { equipment_id: equipmentId ?? null }).then(unwrap<Lot>);

// ── Data Collection ──────────────────────────────────────────────

export const collectDataBatch = (
  items: Array<{
    definition_id: string;
    unit_id?: string;
    lot_id?: string;
    value_numeric?: number;
    value_string?: string;
    value_boolean?: boolean;
    /** Update the current row for (definition, WIP) instead of appending. */
    upsert?: boolean;
  }>,
) => api.post("/data/collect-batch", { items }).then(unwrap<unknown>);

/** Data points already persisted for a WIP (latest first, server-side). */
export const fetchDataPoints = (wipType: "unit" | "lot", wipId: string) =>
  api
    .get("/data/points", {
      params: {
        ...(wipType === "unit" ? { unit_id: wipId } : { lot_id: wipId }),
        limit: 200,
      },
    })
    .then(unwrapList<DataPoint>);

// ── Step Parameter values (recorded actuals) ─────────────────────

/** Record (upsert) step-parameter actual values for a WIP. */
export const recordParameterValues = (
  items: Array<{
    parameter_id: string;
    unit_id?: string;
    lot_id?: string;
    value_numeric?: number;
    value_string?: string;
    value_boolean?: boolean;
  }>,
) =>
  api
    .post("/segment-parameter-values/batch", { items })
    .then(unwrap<unknown>);

/** Step-parameter values already persisted for a WIP. */
export const fetchParameterValues = (wipType: "unit" | "lot", wipId: string) =>
  api
    .get("/segment-parameter-values", {
      params: {
        ...(wipType === "unit" ? { unit_id: wipId } : { lot_id: wipId }),
        limit: 200,
      },
    })
    .then(unwrapList<StepParameterValue>);

// ── Complete ─────────────────────────────────────────────────────

export const completeUnit = (
  id: string,
  result: string,
  dataSnapshot?: Record<string, unknown>,
  disposition?: string,
) =>
  api
    .post(`/units/${id}/complete`, {
      result,
      data_snapshot: dataSnapshot,
      disposition: disposition ?? null,
    })
    .then(unwrap<Unit>);

export const completeLot = (
  id: string,
  quantityScrapped?: number,
  disposition?: string,
  dataSnapshot?: Record<string, unknown>,
  failureMode?: string,
) =>
  api
    .post(`/lots/${id}/complete`, {
      quantity_scrapped: quantityScrapped,
      disposition: disposition ?? null,
      data_snapshot: dataSnapshot ?? null,
      failure_mode: failureMode ?? null,
    })
    .then(unwrap<Lot>);

export const scrapUnit = (
  id: string,
  reason: string,
  disposition?: string,
) =>
  api
    .post(`/units/${id}/scrap`, {
      reason,
      disposition: disposition ?? null,
    })
    .then(unwrap<Unit>);

// ── Move (advance along the route) ───────────────────────────────

export const moveUnit = (
  id: string,
  opts?: { target_step_id?: string; result?: string; disposition?: string },
) => api.post(`/units/${id}/move`, opts ?? null).then(unwrap<Unit>);

export const moveLot = (
  id: string,
  opts?: { target_step_id?: string; result?: string; disposition?: string },
) => api.post(`/lots/${id}/move`, opts ?? null).then(unwrap<Lot>);

// ── Transfer a WIP unit/lot into inventory ───────────────────────

export interface TransferInfo {
  available: boolean;
  transferred: boolean;
  location_id: string | null;
  location_code: string | null;
  location_name: string | null;
}

const wipPath = (wipType: "unit" | "lot") => (wipType === "unit" ? "units" : "lots");

export const fetchTransferInfo = (wipType: "unit" | "lot", id: string) =>
  api.get(`/${wipPath(wipType)}/${id}/transfer-info`).then(unwrap<TransferInfo>);

export const transferToInventory = (wipType: "unit" | "lot", id: string) =>
  api
    .post(`/${wipPath(wipType)}/${id}/transfer-to-inventory`)
    .then(unwrap<{ material_lot_id: string; lot_number: string; quantity: number }>);

// ── Products (name display on the info card) ─────────────────────

export const fetchProducts = () =>
  api.get("/products", { params: { limit: 200 } }).then(unwrapList<Product>);

// ── Material consumption (BOM picking) ───────────────────────────

export const fetchStepBomItems = (stepId: string) =>
  api.get(`/process-segments/${stepId}/bom-items`).then(unwrap<BOMItem[]>);

export const fetchMaterials = () =>
  api.get("/materials", { params: { limit: 200 } }).then(unwrapList<Material>);

export const fetchMaterialLots = (materialId?: string, status?: string) =>
  api
    .get("/material-lots", {
      params: {
        ...(materialId ? { material_id: materialId } : {}),
        ...(status ? { status } : {}),
      },
    })
    .then(unwrapList<MaterialLot>);

export const fetchMaterialLotByNumber = (lotNumber: string) =>
  api
    .get("/material-lots", { params: { lot_number: lotNumber, limit: 1 } })
    .then(unwrapList<MaterialLot>)
    .then((lots) => lots[0] ?? null);

export const consumeMaterial = (
  materialLotId: string,
  payload: {
    unit_id?: string;
    lot_id?: string;
    step_id?: string;
    quantity_consumed?: number;
  },
) =>
  api
    .post(`/material-lots/${materialLotId}/consume`, payload)
    .then(unwrap<MaterialConsumption>);

export const fetchConsumedMaterials = (wipType: "unit" | "lot", wipId: string) =>
  api
    .get(`/${wipType === "unit" ? "units" : "lots"}/${wipId}/consumed-materials`)
    .then(unwrap<MaterialConsumption[]>);
