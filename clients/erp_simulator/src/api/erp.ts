import api from "./client";

// ── Types ─────────────────────────────────────────────────────────────────

export interface ERPHealth {
  inbound: { available: boolean; plugin_id: string | null; healthy: boolean };
  outbound: { available: boolean; plugin_id: string | null; healthy: boolean };
}

export interface ProductionOrder {
  erp_reference: string;
  product_code: string;
  quantity_ordered: number;
  planned_start: string | null;
  planned_end: string | null;
  priority: number;
  uom: string;
  bom_id: string | null;
  routing_id: string | null;
  metadata: Record<string, unknown>;
}

export interface DBProductionOrder {
  id: string;
  order_number: string;
  product_id: string;
  route_id: string | null;
  quantity_ordered: number;
  quantity_completed: number;
  quantity_scrapped: number;
  status: string;
  priority: number;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  erp_reference: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialDefinition {
  code: string;
  name: string;
  material_type: string;
  uom: string;
  revision: string | null;
  description: string;
  shelf_life_days: number | null;
  metadata: Record<string, unknown>;
}

export interface ProductDefinition {
  code: string;
  name: string;
  product_type: string;
  version: string;
  description: string;
  metadata: Record<string, unknown>;
}

export interface BOMItem {
  material_code: string;
  quantity: number;
  uom: string;
  sequence: number;
}

export interface BillOfMaterial {
  product_code: string;
  version: string;
  items: BOMItem[];
  metadata: Record<string, unknown>;
}

export interface RouteStep {
  sequence: number;
  name: string;
  step_type: string;
  work_center_code: string | null;
  description: string;
}

export interface ProcessRoute {
  product_code: string;
  name: string;
  version: string;
  steps: RouteStep[];
  metadata: Record<string, unknown>;
}

export interface WorkCenter {
  code: string;
  name: string;
  area_code: string | null;
  capabilities: Record<string, unknown>;
}

export interface ERPConfirmation {
  success: boolean;
  erp_doc_number: string | null;
  message: string;
  metadata: Record<string, unknown>;
}

export interface ConfirmationRecord {
  type: string;
  order_id: string;
  posted_at: string;
  // Vendor-agnostic fields (Oracle uses erp_document/erp_payload)
  sap_document?: string;
  sap_payload?: Record<string, unknown>;
  erp_document?: string;
  erp_payload?: Record<string, unknown>;
  equipment_id?: string;
}

// ── Envelope unwrap helper ────────────────────────────────────────────────

function unwrapData<T>(resp: { data: { data: T } }): T {
  return resp.data.data;
}

// ── Health ─────────────────────────────────────────────────────────────────

export async function getERPHealth(): Promise<ERPHealth> {
  return unwrapData(await api.get("/erp/health"));
}

// ── Inbound Sync ──────────────────────────────────────────────────────────

export async function syncProductionOrders(): Promise<ProductionOrder[]> {
  return unwrapData(await api.post("/erp/sync/operations-requests"));
}

export async function readProductionOrders(): Promise<DBProductionOrder[]> {
  return unwrapData(await api.get("/operations-requests", { params: { limit: 200 } }));
}

export interface OrderCreatePayload {
  order_number: string;
  product_id: string;
  route_id?: string | null;
  quantity_ordered: number;
  priority?: number;
  planned_start?: string | null;
  planned_end?: string | null;
  erp_reference?: string | null;
  notes?: string | null;
}

export interface OrderUpdatePayload {
  order_number?: string;
  product_id?: string;
  route_id?: string | null;
  quantity_ordered?: number;
  priority?: number;
  planned_start?: string | null;
  planned_end?: string | null;
  erp_reference?: string | null;
  notes?: string | null;
}

export async function createProductionOrder(
  payload: OrderCreatePayload,
): Promise<DBProductionOrder> {
  return unwrapData(await api.post("/operations-requests", payload));
}

export async function updateProductionOrder(
  id: string,
  payload: OrderUpdatePayload,
): Promise<DBProductionOrder> {
  return unwrapData(
    await api.patch(`/operations-requests/${encodeURIComponent(id)}`, payload),
  );
}

export async function deleteProductionOrder(id: string): Promise<void> {
  await api.delete(`/operations-requests/${encodeURIComponent(id)}`);
}

export async function syncMaterials(): Promise<MaterialDefinition[]> {
  return unwrapData(await api.post("/erp/sync/materials"));
}

export async function readMaterials(): Promise<MaterialDefinition[]> {
  const rows = unwrapData(await api.get("/materials", { params: { limit: 200 } }));
  // The /materials endpoint returns uom_symbol (not uom); normalise to the
  // MaterialDefinition shape used throughout the ERP simulator.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return rows.map((r: any) => ({
    ...r,
    uom: r.uom ?? r.uom_symbol ?? "",
  }));
}

export async function syncProducts(): Promise<ProductDefinition[]> {
  return unwrapData(await api.post("/erp/sync/products"));
}

export interface DBProduct {
  id: string;
  name: string;
  code: string;
  version: string;
  description: string | null;
  uom: string;
  product_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export async function readProducts(): Promise<DBProduct[]> {
  return unwrapData(await api.get("/products", { params: { limit: 200 } }));
}

export async function deleteProduct(id: string): Promise<void> {
  await api.delete(`/products/${encodeURIComponent(id)}`);
}

export interface ProductClonePayload {
  code: string;
  name: string;
  version: string;
  description: string | null;
}

export async function cloneProduct(id: string, payload: ProductClonePayload): Promise<DBProduct> {
  return unwrapData(await api.post(`/products/${encodeURIComponent(id)}/clone`, payload));
}

export interface DBBom {
  id: string;
  product_id: string;
  version: string;
  effective_date: string | null;
  expiry_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DBBomItem {
  id: string;
  bom_id: string;
  material_code: string;
  quantity: number;
  uom_id: string;
  uom_symbol: string;
  position: number;
  process_segment_id: string | null;
  is_active: boolean;
}

export async function readProductBoms(productId: string): Promise<DBBom[]> {
  return unwrapData(await api.get(`/products/${encodeURIComponent(productId)}/boms`, { params: { limit: 200 } }));
}

export async function readBomItems(bomId: string): Promise<DBBomItem[]> {
  return unwrapData(await api.get(`/boms/${encodeURIComponent(bomId)}/items`, { params: { limit: 200 } }));
}

export interface DBMaterial {
  id: string;
  code: string;
  name: string;
  uom_symbol: string;
  material_type: string;
  is_active: boolean;
}

export async function readMaterialsDB(): Promise<DBMaterial[]> {
  return unwrapData(await api.get("/materials", { params: { limit: 500 } }));
}

export interface DBMaterialLot {
  id: string;
  material_id: string;
  lot_number: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  status: string;
  supplier: string | null;
  is_active: boolean;
}

export async function readLotsForMaterial(materialCode: string): Promise<DBMaterialLot[]> {
  return unwrapData(await api.get("/material-lots", { params: { material_code: materialCode, limit: 200 } }));
}

export interface DBRoute {
  id: string;
  product_id: string;
  version: string;
  name: string;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DBRouteStep {
  id: string;
  route_id: string;
  sequence: number;
  name: string;
  step_type: string;
  work_cell_id: string | null;
  expected_cycle_time_sec: number | null;
  erp_operation_number: string | null;
  is_active: boolean;
}

export async function readProductRoutes(productId: string): Promise<DBRoute[]> {
  return unwrapData(await api.get(`/products/${encodeURIComponent(productId)}/operations-definitions`, { params: { limit: 200 } }));
}

export async function readRouteSteps(routeId: string): Promise<DBRouteStep[]> {
  return unwrapData(await api.get(`/operations-definitions/${encodeURIComponent(routeId)}/process-segments`, { params: { limit: 200 } }));
}

export async function syncBoms(productId: string): Promise<BillOfMaterial[]> {
  return unwrapData(
    await api.post("/erp/sync/boms", null, { params: { product_id: productId } })
  );
}

export async function syncRoutings(productId: string): Promise<ProcessRoute[]> {
  return unwrapData(
    await api.post("/erp/sync/routings", null, {
      params: { product_id: productId },
    })
  );
}

export async function syncWorkCenters(): Promise<WorkCenter[]> {
  return unwrapData(await api.post("/erp/sync/work-centers"));
}

// ── Dispositions ──────────────────────────────────────────────────────────

export interface DBDisposition {
  id: string;
  code: string;
  name: string;
  description: string | null;
  category: string;
  is_active: boolean;
}

export async function readDispositions(category?: string): Promise<DBDisposition[]> {
  return unwrapData(await api.get("/dispositions", {
    params: { ...(category ? { category } : {}), limit: 200 },
  }));
}

// ── Outbound Reports ──────────────────────────────────────────────────────

export async function reportCompletion(data: {
  order_id: string;
  qty_good: number;
  qty_reject: number;
  step_id?: string;
}): Promise<ERPConfirmation> {
  return unwrapData(await api.post("/erp/report/completion", data));
}

export async function reportConsumption(data: {
  order_id: string;
  materials: { material_code: string; quantity: number; uom: string; lot_number?: string }[];
}): Promise<ERPConfirmation> {
  return unwrapData(await api.post("/erp/report/consumption", data));
}

export async function reportScrap(data: {
  order_id: string;
  qty_scrapped: number;
  reason_code: string;
}): Promise<ERPConfirmation> {
  return unwrapData(await api.post("/erp/report/scrap", data));
}

export async function reportLabor(data: {
  order_id: string;
  operator_id: string;
  duration_minutes: number;
}): Promise<ERPConfirmation> {
  return unwrapData(await api.post("/erp/report/labor", data));
}

export async function reportDowntime(data: {
  equipment_id: string;
  duration_minutes: number;
  reason_code: string;
  started_at: string;
}): Promise<ERPConfirmation> {
  return unwrapData(await api.post("/erp/report/downtime", data));
}

export async function reportQualityResult(data: {
  order_id: string;
  test_id: string;
  result: string;
  details: Record<string, unknown>;
}): Promise<ERPConfirmation> {
  return unwrapData(await api.post("/erp/report/quality-result", data));
}

export async function getConfirmations(): Promise<ConfirmationRecord[]> {
  return unwrapData(await api.get("/erp/confirmations"));
}

// ── Simulator Options ─────────────────────────────────────────────────────

export interface MaterialTypeOption {
  code: string;
  label: string;
}

export interface UOMOption {
  symbol: string;
  name: string;
}

export interface SimulatorOptions {
  erp_type: "sap" | "oracle" | string;
  material_types: MaterialTypeOption[];
  uom_options: UOMOption[];
}

export async function getSimulatorOptions(): Promise<SimulatorOptions> {
  return unwrapData(await api.get("/erp/simulator/options"));
}

// ── Simulator Material CRUD ───────────────────────────────────────────────

export interface MaterialCreatePayload {
  code: string;
  name: string;
  material_type: string;
  uom: string;
  revision?: string | null;
  description: string;
  shelf_life_days: number | null;
}

export interface MaterialUpdatePayload {
  name?: string;
  material_type?: string;
  uom?: string;
  revision?: string | null;
  description?: string;
  shelf_life_days?: number | null;
}

export async function createMaterial(data: MaterialCreatePayload): Promise<MaterialDefinition> {
  return unwrapData(await api.post("/erp/simulator/materials", data));
}

export async function updateMaterial(
  code: string,
  data: MaterialUpdatePayload,
): Promise<MaterialDefinition> {
  return unwrapData(await api.put(`/erp/simulator/materials/${encodeURIComponent(code)}`, data));
}

export async function deleteMaterial(code: string): Promise<void> {
  await api.delete(`/erp/simulator/materials/${encodeURIComponent(code)}`);
}
