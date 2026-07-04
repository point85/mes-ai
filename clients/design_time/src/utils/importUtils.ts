/**
 * importUtils.ts — Parse an export zip and import DT objects to the API.
 *
 * Import order (honours FK dependencies):
 *   UoMs → Equipment Classes → Dispositions → Materials →
 *   Storage Locations → Sites (hierarchy) → Products → Routes →
 *   Work Schedules → Data Definitions → Reason Codes
 *
 * Backwards compatibility:
 *   • All fields are extracted with optional chaining / nullish coalescing so
 *     objects from older exports that lack newer attributes import cleanly.
 *   • Server-managed fields (id, created_at, updated_at) are never sent.
 *   • Cross-reference UUIDs are resolved through an idMap built during import;
 *     unresolvable references fall back to null.
 */

import JSZip from "jszip";
import type {
  UoM,
  EquipmentClassDetail,
  StorageLocation,
  Material,
  Disposition,
  Product,
  BOM,
  BOMItem,
  ProcessRoute,
  RouteStep,
  StepParameter,
  StepEquipmentRequirement,
  StepMaterialRequirement,
  RouteProductAssignment,
  RouteMaterialAssignment,
  Site,
  Area,
  ProductionLine,
  WorkCell,
  Equipment,
  EquipmentMaterial,
  EquipmentCapabilityRead,
  WorkScheduleRead,
  DataDefinition,
  Reason,
} from "../types";
import {
  fetchUoMs,
  createUoM,
  updateUoM,
  fetchEquipmentClasses,
  fetchEquipmentClassDetail,
  createEquipmentClass,
  updateEquipmentClass,
  createClassProperty,
  fetchStorageLocations,
  createStorageLocation,
  updateStorageLocation,
  fetchMaterials,
  createMaterial,
  updateMaterial,
  fetchDispositions,
  createDisposition,
  updateDisposition,
  fetchProducts,
  createProduct,
  updateProduct,
  createBOM,
  createBOMItem,
  fetchAllRoutes,
  createStandaloneRoute,
  updateStandaloneRoute,
  fetchRouteSteps,
  createRouteStep,
  updateRouteStep,
  fetchStepParameters,
  createStepParameter,
  deleteStepParameter,
  createStepEquipmentRequirement,
  createStepMaterialRequirement,
  assignProductToRoute,
  assignMaterialToRoute,
  fetchRouteProducts,
  fetchRouteMaterials,
  fetchSites,
  createSite,
  updateSite,
  fetchAreas,
  createArea,
  fetchLines,
  createLine,
  fetchWorkCells,
  createWorkCell,
  fetchEquipment,
  createEquipment,
  createEquipmentMaterial,
  createEquipmentCapability,
  fetchWorkSchedules,
  createWorkSchedule,
  updateWorkSchedule,
  createShift,
  addBreak,
  createRotation,
  addRotationSegment,
  createTeam,
  createNonWorkingPeriod,
  fetchDataDefinitions,
  createDataDefinition,
  updateDataDefinition,
  fetchReasons,
  createReason,
  updateReason,
} from "../api";

// ─── Export node shapes ───────────────────────────────────────────────────────

export interface EquipmentExportNode {
  equipment: Equipment;
  materials: EquipmentMaterial[];
  capabilities: EquipmentCapabilityRead[];
}

export interface WorkCellExportNode {
  work_cell: WorkCell;
  equipment: EquipmentExportNode[];
}

export interface LineExportNode {
  line: ProductionLine;
  work_cells: WorkCellExportNode[];
}

export interface AreaExportNode {
  area: Area;
  lines: LineExportNode[];
}

export interface SiteExportNode {
  site: Site;
  areas: AreaExportNode[];
}

export interface ProductExportNode {
  product: Product;
  boms: { bom: BOM; items: BOMItem[] }[];
}

export interface StepExportNode {
  step: RouteStep;
  parameters: StepParameter[];
  equipment_requirements: StepEquipmentRequirement[];
  material_requirements: StepMaterialRequirement[];
}

export interface RouteExportNode {
  route: ProcessRoute;
  steps: StepExportNode[];
  product_assignments: RouteProductAssignment[];
  material_assignments: RouteMaterialAssignment[];
}

export interface ReasonExportNode {
  reason: Reason;
  children: ReasonExportNode[];
}

export interface ParsedZip {
  uom: UoM[];
  equipment_classes: EquipmentClassDetail[];
  storage_locations: StorageLocation[];
  materials: Material[];
  dispositions: Disposition[];
  sites: SiteExportNode[];
  products: ProductExportNode[];
  routes: RouteExportNode[];
  work_schedules: WorkScheduleRead[];
  data_definitions: DataDefinition[];
  reason_codes: ReasonExportNode[];
}

// ─── Conflict & resolution types ──────────────────────────────────────────────

export interface ConflictItem {
  /** Display category label, e.g. "UoM" */
  category: string;
  /** Human-readable item label, e.g. "kg" or "APEX-ELEC" */
  label: string;
  /** UUID of this item in the exported ZIP */
  importedId: string;
  /** UUID of the matching item already in the target DB */
  existingId: string;
}

export type ConflictResolution = "overwrite" | "skip";

export interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

// ─── Small coercion helpers ───────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyObj = Record<string, any>;

function s(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}
function sn(v: unknown): string | null {
  return typeof v === "string" ? v : null;
}
function n(v: unknown, fallback = 0): number {
  return typeof v === "number" ? v : fallback;
}

function conflictKey(category: string, importedId: string): string {
  return `${category}::${importedId}`;
}

// Normalise material_type values from older exports that used different names.
const MATERIAL_TYPE_ALIASES: Record<string, string> = {
  semi_finished: "semi",
};
function normaliseMaterialType(v: string): string {
  return MATERIAL_TYPE_ALIASES[v] ?? v;
}

// Normalise data-collection source values from older exports.
const DATA_SOURCE_ALIASES: Record<string, string> = {
  operator: "manual",
};
function normaliseDataSource(v: string): string {
  return DATA_SOURCE_ALIASES[v] ?? v;
}

// ─── parseZip ─────────────────────────────────────────────────────────────────

export async function parseZip(file: File): Promise<ParsedZip> {
  const buffer = await file.arrayBuffer();
  const zip = await JSZip.loadAsync(buffer);

  const result: ParsedZip = {
    uom: [],
    equipment_classes: [],
    storage_locations: [],
    materials: [],
    dispositions: [],
    sites: [],
    products: [],
    routes: [],
    work_schedules: [],
    data_definitions: [],
    reason_codes: [],
  };

  for (const [path, entry] of Object.entries(zip.files)) {
    if (entry.dir || !path.endsWith(".json")) continue;
    let json: AnyObj;
    try {
      json = JSON.parse(await entry.async("string")) as AnyObj;
    } catch {
      continue; // skip malformed files — backwards compat
    }
    const folder = path.split("/")[0];
    switch (folder) {
      case "uom":               result.uom.push(json as UoM); break;
      case "equipment_classes": result.equipment_classes.push(json as EquipmentClassDetail); break;
      case "storage_locations": result.storage_locations.push(json as StorageLocation); break;
      case "materials":         result.materials.push(json as Material); break;
      case "dispositions":      result.dispositions.push(json as Disposition); break;
      case "sites":             result.sites.push(json as SiteExportNode); break;
      case "products":          result.products.push(json as ProductExportNode); break;
      case "routes":            result.routes.push(json as RouteExportNode); break;
      case "work_schedules":    result.work_schedules.push(json as WorkScheduleRead); break;
      case "data_definitions":  result.data_definitions.push(json as DataDefinition); break;
      case "reason_codes":      result.reason_codes.push(json as ReasonExportNode); break;
    }
  }

  return result;
}

// ─── detectConflicts ──────────────────────────────────────────────────────────

export async function detectConflicts(parsed: ParsedZip): Promise<ConflictItem[]> {
  const out: ConflictItem[] = [];

  if (parsed.uom.length) {
    const bySymbol = new Map((await fetchUoMs()).data.map((u) => [u.symbol, u]));
    for (const u of parsed.uom) {
      const ex = bySymbol.get(u.symbol);
      if (ex) out.push({ category: "UoM", label: u.symbol, importedId: u.id, existingId: ex.id });
    }
  }
  if (parsed.equipment_classes.length) {
    const byCode = new Map((await fetchEquipmentClasses()).data.map((c) => [c.code, c]));
    for (const c of parsed.equipment_classes) {
      const ex = byCode.get(c.code);
      if (ex) out.push({ category: "Equipment Class", label: c.code, importedId: c.id, existingId: ex.id });
    }
  }
  if (parsed.dispositions.length) {
    const byCode = new Map((await fetchDispositions()).data.map((d) => [d.code, d]));
    for (const d of parsed.dispositions) {
      const ex = byCode.get(d.code);
      if (ex) out.push({ category: "Disposition", label: d.code, importedId: d.id, existingId: ex.id });
    }
  }
  if (parsed.materials.length) {
    const byCode = new Map((await fetchMaterials()).data.map((m) => [m.code, m]));
    for (const m of parsed.materials) {
      const ex = byCode.get(m.code);
      if (ex) out.push({ category: "Material", label: m.code, importedId: m.id, existingId: ex.id });
    }
  }
  if (parsed.storage_locations.length) {
    const byCode = new Map((await fetchStorageLocations()).data.map((l) => [l.code, l]));
    for (const loc of parsed.storage_locations) {
      const ex = byCode.get(loc.code);
      if (ex) out.push({ category: "Storage Location", label: loc.code, importedId: loc.id, existingId: ex.id });
    }
  }
  if (parsed.sites.length) {
    const byCode = new Map((await fetchSites()).data.map((s) => [s.code, s]));
    for (const node of parsed.sites) {
      const ex = byCode.get(node.site.code);
      if (ex) out.push({ category: "Site", label: node.site.code, importedId: node.site.id, existingId: ex.id });
    }
  }
  if (parsed.products.length) {
    const byCode = new Map((await fetchProducts()).data.map((p) => [p.code, p]));
    for (const node of parsed.products) {
      const ex = byCode.get(node.product.code);
      if (ex) out.push({ category: "Product", label: node.product.code, importedId: node.product.id, existingId: ex.id });
    }
  }
  if (parsed.routes.length) {
    const byKey = new Map((await fetchAllRoutes()).data.map((r) => [`${r.name}::${r.version}`, r]));
    for (const node of parsed.routes) {
      const ex = byKey.get(`${node.route.name}::${node.route.version}`);
      if (ex) out.push({ category: "Route", label: `${node.route.name} v${node.route.version}`, importedId: node.route.id, existingId: ex.id });
    }
  }
  if (parsed.work_schedules.length) {
    const byName = new Map((await fetchWorkSchedules()).data.map((s) => [s.name, s]));
    for (const ws of parsed.work_schedules) {
      const ex = byName.get(ws.name);
      if (ex) out.push({ category: "Work Schedule", label: ws.name, importedId: ws.id, existingId: ex.id });
    }
  }
  if (parsed.data_definitions.length) {
    const byCode = new Map((await fetchDataDefinitions()).data.map((d) => [d.code, d]));
    for (const dd of parsed.data_definitions) {
      const ex = byCode.get(dd.code);
      if (ex) out.push({ category: "Data Definition", label: dd.code, importedId: dd.id, existingId: ex.id });
    }
  }
  if (parsed.reason_codes.length) {
    const byCode = new Map((await fetchReasons()).map((r) => [r.code, r]));
    for (const node of parsed.reason_codes) {
      const ex = byCode.get(node.reason.code);
      if (ex) out.push({ category: "Reason Code", label: node.reason.code, importedId: node.reason.id, existingId: ex.id });
    }
  }

  return out;
}

// ─── runImport ────────────────────────────────────────────────────────────────

export async function runImport(
  parsed: ParsedZip,
  conflicts: ConflictItem[],
  resolutions: Map<string, ConflictResolution>,
  onProgress: (msg: string) => void,
): Promise<ImportResult> {
  const res: ImportResult = { created: 0, updated: 0, skipped: 0, errors: [] };

  // idMap: exported UUID → DB UUID (built as we import)
  const idMap = new Map<string, string>();

  // Pre-populate idMap from all conflicts so cross-references always resolve,
  // regardless of whether we overwrite or skip the conflicting item.
  for (const c of conflicts) {
    idMap.set(c.importedId, c.existingId);
  }

  const conflictMap = new Map(conflicts.map((c) => [conflictKey(c.category, c.importedId), c]));

  function hasConflict(category: string, importedId: string): boolean {
    return conflictMap.has(conflictKey(category, importedId));
  }

  function shouldOverwrite(category: string, importedId: string): boolean {
    return resolutions.get(conflictKey(category, importedId)) === "overwrite";
  }

  function resolveId(oldId: string | null | undefined): string | null {
    if (!oldId) return null;
    return idMap.get(oldId) ?? null;
  }

  // ── UoMs ────────────────────────────────────────────────────────────────
  let uomBySymbol = new Map((await fetchUoMs()).data.map((u) => [u.symbol, u]));

  // Topological sort: ensure each UoM is imported after the base UoMs it
  // references via left_uom_symbol / right_uom_symbol.  Without this,
  // composite UoMs (quotient, product, power) fail with 404 when the server
  // tries to look up their components and they don't exist yet.
  const uomsToImport = (() => {
    const bySymbol = new Map(parsed.uom.map((u) => [u.symbol, u]));
    const sorted: UoM[] = [];
    const visited = new Set<string>();
    function visit(u: UoM) {
      if (visited.has(u.symbol)) return;
      visited.add(u.symbol); // mark early to handle cycles safely
      if (u.left_uom_symbol) {
        const dep = bySymbol.get(u.left_uom_symbol);
        if (dep) visit(dep);
      }
      if (u.right_uom_symbol) {
        const dep = bySymbol.get(u.right_uom_symbol);
        if (dep) visit(dep);
      }
      sorted.push(u);
    }
    for (const u of parsed.uom) visit(u);
    return sorted;
  })();

  for (const u of uomsToImport) {
    onProgress(`Importing UoM: ${u.symbol}…`);
    try {
      if (hasConflict("UoM", u.id)) {
        if (shouldOverwrite("UoM", u.id)) {
          const dbId = idMap.get(u.id)!;
          await updateUoM(dbId, {
            name: s(u.name),
            description: sn(u.description),
            uom_type: s(u.uom_type, "custom"),
            uom_class: (u.uom_class as UoM["uom_class"]) ?? "scalar",
            multiplier: n(u.multiplier, 1),
            offset: n(u.offset, 0),
            left_uom_symbol: sn(u.left_uom_symbol),
            right_uom_symbol: sn(u.right_uom_symbol),
            exponent: u.exponent != null ? n(u.exponent) : null,
          });
          res.updated++;
        } else {
          res.skipped++;
        }
      } else {
        const created = await createUoM({
          symbol: s(u.symbol),
          name: s(u.name),
          description: sn(u.description),
          uom_type: s(u.uom_type, "custom"),
          uom_class: (u.uom_class as UoM["uom_class"]) ?? "scalar",
          multiplier: n(u.multiplier, 1),
          offset: n(u.offset, 0),
          left_uom_symbol: sn(u.left_uom_symbol),
          right_uom_symbol: sn(u.right_uom_symbol),
          exponent: u.exponent != null ? n(u.exponent) : null,
        });
        idMap.set(u.id, created.id);
        res.created++;
      }
    } catch (e) {
      res.errors.push(`UoM "${u.symbol}": ${String(e)}`);
    }
  }

  // Refresh UoM lookup after imports
  uomBySymbol = new Map((await fetchUoMs()).data.map((u) => [u.symbol, u]));

  function resolveUomId(symbol: string | null | undefined, oldId: string | null | undefined): string | null {
    if (symbol && uomBySymbol.has(symbol)) return uomBySymbol.get(symbol)!.id;
    return resolveId(oldId ?? null);
  }

  // ── Equipment Classes ────────────────────────────────────────────────────
  const classByCode = new Map((await fetchEquipmentClasses()).data.map((c) => [c.code, c]));

  for (const cls of parsed.equipment_classes) {
    onProgress(`Importing Equipment Class: ${cls.code}…`);
    let classDbId: string;
    try {
      if (hasConflict("Equipment Class", cls.id)) {
        classDbId = idMap.get(cls.id)!;
        if (shouldOverwrite("Equipment Class", cls.id)) {
          await updateEquipmentClass(classDbId, {
            name: s(cls.name),
            description: sn(cls.description),
          });
          res.updated++;
        } else {
          res.skipped++;
        }
      } else {
        const created = await createEquipmentClass({
          code: s(cls.code),
          name: s(cls.name),
          description: sn(cls.description),
        });
        classDbId = created.id;
        idMap.set(cls.id, classDbId);
        res.created++;
      }

      // Always build property idMap — needed for capability cross-refs
      const detail = await fetchEquipmentClassDetail(classDbId);
      const existingPropsByName = new Map((detail.properties ?? []).map((p) => [p.name, p]));

      for (const prop of (cls.properties ?? []) as AnyObj[]) {
        const existingProp = existingPropsByName.get(s(prop.name));
        if (existingProp) {
          idMap.set(s(prop.id), existingProp.id);
        } else {
          try {
            const created = await createClassProperty(classDbId, {
              name: s(prop.name),
              description: sn(prop.description),
              data_type: s(prop.data_type, "string"),
              uom_id: resolveUomId(sn(prop.uom_symbol), sn(prop.uom_id)),
              default_value: sn(prop.default_value),
            });
            idMap.set(s(prop.id), created.id);
          } catch (e) {
            res.errors.push(`Class property "${cls.code}.${prop.name}": ${String(e)}`);
          }
        }
      }
    } catch (e) {
      res.errors.push(`Equipment Class "${cls.code}": ${String(e)}`);
    }
  }
  void classByCode; // suppress unused warning — kept for reference

  // ── Dispositions ─────────────────────────────────────────────────────────
  let dispByCode = new Map((await fetchDispositions()).data.map((d) => [d.code, d]));

  for (const d of parsed.dispositions) {
    onProgress(`Importing Disposition: ${d.code}…`);
    try {
      if (hasConflict("Disposition", d.id)) {
        if (shouldOverwrite("Disposition", d.id)) {
          await updateDisposition(idMap.get(d.id)!, {
            name: s(d.name),
            description: sn(d.description),
            category: s(d.category),
          });
          res.updated++;
        } else {
          res.skipped++;
        }
      } else {
        const created = await createDisposition({
          code: s(d.code),
          name: s(d.name),
          description: sn(d.description),
          category: s(d.category, "pass"),
        });
        idMap.set(d.id, created.id);
        res.created++;
      }
    } catch (e) {
      res.errors.push(`Disposition "${d.code}": ${String(e)}`);
    }
  }

  // Refresh disposition lookup
  dispByCode = new Map((await fetchDispositions()).data.map((d) => [d.code, d]));

  function resolveDispIds(rawDisps: AnyObj[]): string[] {
    const ids: string[] = [];
    for (const d of rawDisps ?? []) {
      const code = sn(d.code);
      if (code && dispByCode.has(code)) {
        ids.push(dispByCode.get(code)!.id);
      } else {
        const resolved = resolveId(s(d.id));
        if (resolved) ids.push(resolved);
      }
    }
    return ids;
  }

  // ── Materials ─────────────────────────────────────────────────────────────
  let matByCode = new Map((await fetchMaterials()).data.map((m) => [m.code, m]));

  for (const m of parsed.materials) {
    onProgress(`Importing Material: ${m.code}…`);
    try {
      const uomId = resolveUomId(sn(m.uom_symbol), sn(m.uom_id));
      if (hasConflict("Material", m.id)) {
        if (shouldOverwrite("Material", m.id)) {
          await updateMaterial(idMap.get(m.id)!, {
            name: s(m.name),
            description: sn(m.description),
            material_type: normaliseMaterialType(s(m.material_type, "raw")),
            uom_id: uomId ?? undefined,
            shelf_life_days: m.shelf_life_days != null ? n(m.shelf_life_days) : null,
          });
          res.updated++;
        } else {
          res.skipped++;
        }
      } else {
        // uom_id is required; fall back to first available UoM if unresolvable
        const fallbackUomId = uomId ?? [...uomBySymbol.values()][0]?.id ?? "";
        const created = await createMaterial({
          code: s(m.code),
          name: s(m.name),
          description: sn(m.description),
          material_type: normaliseMaterialType(s(m.material_type, "raw")),
          uom_id: fallbackUomId,
          shelf_life_days: m.shelf_life_days != null ? n(m.shelf_life_days) : null,
        });
        idMap.set(m.id, created.id);
        res.created++;
      }
    } catch (e) {
      res.errors.push(`Material "${m.code}": ${String(e)}`);
    }
  }

  matByCode = new Map((await fetchMaterials()).data.map((m) => [m.code, m]));

  function resolveMatId(code: string | null | undefined, oldId: string | null | undefined): string | null {
    if (code && matByCode.has(code)) return matByCode.get(code)!.id;
    return resolveId(oldId ?? null);
  }

  // ── Storage Locations ─────────────────────────────────────────────────────
  for (const loc of parsed.storage_locations) {
    onProgress(`Importing Storage Location: ${loc.code}…`);
    try {
      if (hasConflict("Storage Location", loc.id)) {
        if (shouldOverwrite("Storage Location", loc.id)) {
          await updateStorageLocation(idMap.get(loc.id)!, {
            name: s(loc.name),
            description: sn(loc.description),
            location_type: s(loc.location_type),
          });
          res.updated++;
        } else {
          res.skipped++;
        }
      } else {
        const created = await createStorageLocation({
          code: s(loc.code),
          name: s(loc.name),
          description: sn(loc.description),
          location_type: s(loc.location_type, "warehouse"),
        });
        idMap.set(loc.id, created.id);
        res.created++;
      }
    } catch (e) {
      res.errors.push(`Storage Location "${loc.code}": ${String(e)}`);
    }
  }

  // ── Sites (full hierarchy — upsert sub-objects by code) ──────────────────
  const siteByCode = new Map((await fetchSites()).data.map((s2) => [s2.code, s2]));

  for (const node of parsed.sites) {
    const { site } = node;
    onProgress(`Importing Site: ${site.code}…`);
    let siteDbId: string;
    let skipHierarchy = false;

    try {
      if (hasConflict("Site", site.id)) {
        siteDbId = idMap.get(site.id)!;
        if (shouldOverwrite("Site", site.id)) {
          await updateSite(siteDbId, {
            name: s(site.name),
            description: sn(site.description),
            timezone: sn(site.timezone),
            address: sn(site.address),
          });
          res.updated++;
        } else {
          res.skipped++;
          skipHierarchy = true;
        }
      } else {
        const created = await createSite({
          code: s(site.code),
          name: s(site.name),
          description: sn(site.description),
          timezone: sn(site.timezone),
          address: sn(site.address),
        });
        siteDbId = created.id;
        idMap.set(site.id, siteDbId);
        res.created++;
      }

      if (skipHierarchy) continue;

      // Upsert nested hierarchy (additive: create if missing, map if exists)
      const existingAreas = (await fetchAreas(siteDbId)).data;
      const areaByCode = new Map(existingAreas.map((a) => [a.code, a]));

      for (const areaNode of (node.areas ?? []) as AreaExportNode[]) {
        const { area } = areaNode;
        onProgress(`  Area: ${area.code}…`);
        let areaDbId: string;
        try {
          const existing = areaByCode.get(s(area.code));
          if (existing) {
            areaDbId = existing.id;
            idMap.set(area.id, areaDbId);
          } else {
            const created = await createArea(siteDbId, {
              code: s(area.code),
              name: s(area.name),
              description: sn(area.description),
            });
            areaDbId = created.id;
            idMap.set(area.id, areaDbId);
            res.created++;
          }

          const existingLines = (await fetchLines(areaDbId)).data;
          const lineByCode = new Map(existingLines.map((l) => [l.code, l]));

          for (const lineNode of (areaNode.lines ?? []) as LineExportNode[]) {
            const { line } = lineNode;
            onProgress(`    Line: ${line.code}…`);
            let lineDbId: string;
            try {
              const exLine = lineByCode.get(s(line.code));
              if (exLine) {
                lineDbId = exLine.id;
                idMap.set(line.id, lineDbId);
              } else {
                const created = await createLine(areaDbId, {
                  code: s(line.code),
                  name: s(line.name),
                  description: sn(line.description),
                });
                lineDbId = created.id;
                idMap.set(line.id, lineDbId);
                res.created++;
              }

              const existingWCs = (await fetchWorkCells(lineDbId)).data;
              const wcByCode = new Map(existingWCs.map((wc) => [wc.code, wc]));

              for (const wcNode of (lineNode.work_cells ?? []) as WorkCellExportNode[]) {
                const { work_cell: wc } = wcNode;
                onProgress(`      Work Cell: ${wc.code}…`);
                let wcDbId: string;
                try {
                  const exWC = wcByCode.get(s(wc.code));
                  if (exWC) {
                    wcDbId = exWC.id;
                    idMap.set(wc.id, wcDbId);
                  } else {
                    const created = await createWorkCell(lineDbId, {
                      code: s(wc.code),
                      name: s(wc.name),
                      description: sn(wc.description),
                      default_dispatch_strategy: sn(wc.default_dispatch_strategy),
                      custom_strategy_prompt: sn(wc.custom_strategy_prompt),
                    });
                    wcDbId = created.id;
                    idMap.set(wc.id, wcDbId);
                    res.created++;
                  }

                  const existingEquip = (await fetchEquipment(wcDbId)).data;
                  const equipByCode = new Map(existingEquip.map((e2) => [e2.code, e2]));

                  for (const equipNode of (wcNode.equipment ?? []) as EquipmentExportNode[]) {
                    const { equipment: eq } = equipNode;
                    onProgress(`        Equipment: ${eq.code}…`);
                    let equipDbId: string;
                    try {
                      const exEq = equipByCode.get(s(eq.code));
                      if (exEq) {
                        equipDbId = exEq.id;
                        idMap.set(eq.id, equipDbId);
                      } else {
                        const created = await createEquipment(wcDbId, {
                          code: s(eq.code),
                          name: s(eq.name),
                          description: sn(eq.description),
                          equipment_class_id: resolveId(sn(eq.equipment_class_id)),
                          max_queue_depth: eq.max_queue_depth != null ? n(eq.max_queue_depth) : null,
                        });
                        equipDbId = created.id;
                        idMap.set(eq.id, equipDbId);
                        res.created++;
                      }

                      // Equipment materials (only create, skip if material unresolvable)
                      for (const em of (equipNode.materials ?? []) as AnyObj[]) {
                        const matId = resolveId(s(em.material_id)) ?? resolveMatId(null, s(em.material_id));
                        const speedUomId = resolveUomId(sn(em.design_speed_uom_symbol), sn(em.design_speed_uom_id));
                        const rejectUomId = resolveUomId(sn(em.reject_uom_symbol), sn(em.reject_uom_id));
                        if (!matId || !speedUomId || !rejectUomId) continue;
                        try {
                          await createEquipmentMaterial(equipDbId, {
                            material_id: matId,
                            design_speed: n(em.design_speed, 0),
                            design_speed_uom_id: speedUomId,
                            reject_uom_id: rejectUomId,
                            target_oee: n(em.target_oee, 85),
                          });
                        } catch {
                          // ignore duplicate material setups
                        }
                      }

                      // Equipment capabilities
                      for (const cap of (equipNode.capabilities ?? []) as AnyObj[]) {
                        const capClassId = resolveId(sn(cap.equipment_class_id));
                        const props = ((cap.properties ?? []) as AnyObj[])
                          .map((p) => ({
                            class_property_id: resolveId(s(p.class_property_id)) ?? s(p.class_property_id),
                            value: s(p.value),
                          }))
                          .filter((p) => p.class_property_id);
                        try {
                          await createEquipmentCapability(equipDbId, {
                            equipment_class_id: capClassId,
                            capability_type: s(cap.capability_type, "committed"),
                            reason: sn(cap.reason),
                            start_time: sn(cap.start_time),
                            end_time: sn(cap.end_time),
                            properties: props,
                          });
                        } catch {
                          // ignore duplicate capabilities
                        }
                      }
                    } catch (e) {
                      res.errors.push(`Equipment "${eq.code}": ${String(e)}`);
                    }
                  }
                } catch (e) {
                  res.errors.push(`Work Cell "${wc.code}": ${String(e)}`);
                }
              }
            } catch (e) {
              res.errors.push(`Line "${line.code}": ${String(e)}`);
            }
          }
        } catch (e) {
          res.errors.push(`Area "${area.code}": ${String(e)}`);
        }
      }
    } catch (e) {
      res.errors.push(`Site "${site.code}": ${String(e)}`);
    }
  }
  void siteByCode;

  // ── Products ──────────────────────────────────────────────────────────────
  const productByCode = new Map((await fetchProducts()).data.map((p) => [p.code, p]));

  for (const node of parsed.products) {
    const { product } = node;
    onProgress(`Importing Product: ${product.code}…`);
    let productDbId: string;
    let productSkipped = false;
    try {
      const uomId = resolveUomId(sn(product.uom_symbol), sn(product.uom_id));
      if (hasConflict("Product", product.id)) {
        productDbId = idMap.get(product.id)!;
        if (shouldOverwrite("Product", product.id)) {
          await updateProduct(productDbId, {
            name: s(product.name),
            version: s(product.version, "1"),
            description: sn(product.description),
            uom_id: uomId ?? undefined,
            product_type: s(product.product_type, "finished"),
          });
          res.updated++;
        } else {
          res.skipped++;
          productSkipped = true;
        }
      } else {
        const fallbackUomId = uomId ?? [...uomBySymbol.values()][0]?.id ?? "";
        const created = await createProduct({
          code: s(product.code),
          name: s(product.name),
          version: s(product.version, "1"),
          description: sn(product.description),
          uom_id: fallbackUomId,
          product_type: s(product.product_type, "finished"),
        });
        productDbId = created.id;
        idMap.set(product.id, productDbId);
        productByCode.set(created.code, created);
        res.created++;
      }

      if (!productSkipped) {
        for (const { bom, items } of (node.boms ?? []) as { bom: BOM; items: BOMItem[] }[]) {
          try {
            const createdBom = await createBOM(productDbId, {
              version: s(bom.version, "1"),
              effective_date: sn(bom.effective_date),
              expiry_date: sn(bom.expiry_date),
            });
            for (const item of items ?? []) {
              try {
                const itemUomId = resolveUomId(sn(item.uom_symbol), sn(item.uom_id));
                await createBOMItem(createdBom.id, {
                  material_code: s(item.material_code),
                  quantity: n(item.quantity, 1),
                  uom_id: itemUomId ?? [...uomBySymbol.values()][0]?.id ?? "",
                  position: n(item.position, 0),
                  process_segment_id: null, // route step IDs change; don't carry over
                });
              } catch (e) {
                res.errors.push(`BOM item in "${product.code}": ${String(e)}`);
              }
            }
          } catch (e) {
            res.errors.push(`BOM for "${product.code}": ${String(e)}`);
          }
        }
      }
    } catch (e) {
      res.errors.push(`Product "${product.code}": ${String(e)}`);
    }
  }

  // Refresh product lookup
  const freshProducts = (await fetchProducts()).data;
  const finalProductByCode = new Map(freshProducts.map((p) => [p.code, p]));

  // ── Routes ────────────────────────────────────────────────────────────────
  const routeByKey = new Map((await fetchAllRoutes()).data.map((r) => [`${r.name}::${r.version}`, r]));

  for (const node of parsed.routes) {
    const { route } = node;
    onProgress(`Importing Route: ${route.name} v${route.version}…`);
    let routeDbId: string;
    let routeSkipped = false;
    try {
      const routeKey = `${route.name}::${route.version}`;
      if (hasConflict("Route", route.id)) {
        routeDbId = idMap.get(route.id)!;
        if (shouldOverwrite("Route", route.id)) {
          await updateStandaloneRoute(routeDbId, {
            name: s(route.name),
            version: s(route.version, "1"),
            description: sn(route.description),
            is_default: typeof route.is_default === "boolean" ? route.is_default : false,
          });
          res.updated++;
        } else {
          res.skipped++;
          routeSkipped = true;
        }
      } else {
        const created = await createStandaloneRoute({
          name: s(route.name),
          version: s(route.version, "1"),
          description: sn(route.description),
          is_default: typeof route.is_default === "boolean" ? route.is_default : false,
        });
        routeDbId = created.id;
        idMap.set(route.id, routeDbId);
        routeByKey.set(routeKey, created);
        res.created++;
      }

      if (!routeSkipped) {
        // Import steps — upsert by sequence number
        const existingSteps = (await fetchRouteSteps(routeDbId)).data;
        const stepBySeq = new Map(existingSteps.map((st) => [st.sequence, st]));

        for (const stepNode of (node.steps ?? []) as StepExportNode[]) {
          const { step } = stepNode;
          onProgress(`  Step ${step.sequence}: ${step.name}…`);
          const inDispIds = resolveDispIds((step.input_dispositions ?? []) as AnyObj[]);
          const outDispIds = resolveDispIds((step.output_dispositions ?? []) as AnyObj[]);
          const classId = resolveId(sn(step.equipment_class_id));

          try {
            let stepDbId: string;
            const existing = stepBySeq.get(step.sequence);
            if (existing) {
              await updateRouteStep(existing.id, {
                name: s(step.name),
                step_type: s(step.step_type, "operation"),
                equipment_class_id: classId,
                expected_cycle_time_sec: step.expected_cycle_time_sec != null
                  ? n(step.expected_cycle_time_sec) : null,
                erp_operation_number: sn(step.erp_operation_number),
                is_initial_step: typeof step.is_initial_step === "boolean" ? step.is_initial_step : false,
                input_disposition_ids: inDispIds,
                output_disposition_ids: outDispIds,
              });
              stepDbId = existing.id;
              idMap.set(step.id, stepDbId);
            } else {
              const created = await createRouteStep(routeDbId, {
                sequence: n(step.sequence, 0),
                name: s(step.name),
                step_type: s(step.step_type, "operation"),
                equipment_class_id: classId,
                expected_cycle_time_sec: step.expected_cycle_time_sec != null
                  ? n(step.expected_cycle_time_sec) : null,
                erp_operation_number: sn(step.erp_operation_number),
                is_initial_step: typeof step.is_initial_step === "boolean" ? step.is_initial_step : false,
                input_disposition_ids: inDispIds,
                output_disposition_ids: outDispIds,
              });
              stepDbId = created.id;
              idMap.set(step.id, stepDbId);
            }

            // Parameters: delete existing, recreate from import (if step was updated)
            if (existing) {
              const oldParams = (await fetchStepParameters(stepDbId)).data;
              for (const p of oldParams) {
                try { await deleteStepParameter(p.id); } catch { /* ignore */ }
              }
            }
            for (const param of (stepNode.parameters ?? []) as AnyObj[]) {
              try {
                await createStepParameter(stepDbId, {
                  name: s(param.name),
                  data_type: s(param.data_type, "string"),
                  uom_id: resolveUomId(sn(param.uom_symbol), sn(param.uom_id)),
                  target_value: sn(param.target_value),
                  lower_limit: sn(param.lower_limit),
                  upper_limit: sn(param.upper_limit),
                  is_required: typeof param.is_required === "boolean" ? param.is_required : false,
                });
              } catch (e) {
                res.errors.push(`Step param "${param.name}": ${String(e)}`);
              }
            }

            // Equipment requirements (create only; no delete to avoid breaking things)
            for (const er of (stepNode.equipment_requirements ?? []) as AnyObj[]) {
              try {
                await createStepEquipmentRequirement(stepDbId, {
                  equipment_class_id: resolveId(sn(er.equipment_class_id)),
                  equipment_id: resolveId(sn(er.equipment_id)),
                  use_type: (er.use_type as "required" | "preferred" | "alternate") ?? "required",
                  description: sn(er.description),
                });
              } catch { /* ignore duplicate */ }
            }

            // Material requirements
            for (const mr of (stepNode.material_requirements ?? []) as AnyObj[]) {
              const matId = resolveId(s(mr.material_id));
              if (!matId) continue;
              const mrUomId = resolveUomId(sn(mr.uom_symbol), sn(mr.uom_id));
              if (!mrUomId) continue;
              try {
                await createStepMaterialRequirement(stepDbId, {
                  material_id: matId,
                  quantity: n(mr.quantity, 1),
                  uom_id: mrUomId,
                  material_use: (mr.material_use as "consumed" | "produced") ?? "consumed",
                  position: n(mr.position, 0),
                  description: sn(mr.description),
                });
              } catch { /* ignore duplicate */ }
            }
          } catch (e) {
            res.errors.push(`Route step "${step.name}": ${String(e)}`);
          }
        }

        // Product assignments
        const existingPA = (await fetchRouteProducts(routeDbId)).data;
        const assignedProductIds = new Set(existingPA.map((a) => a.product_id));
        for (const pa of (node.product_assignments ?? []) as AnyObj[]) {
          const newProdId = resolveId(s(pa.product_id));
          if (!newProdId || assignedProductIds.has(newProdId)) continue;
          try {
            await assignProductToRoute(routeDbId, { product_id: newProdId });
          } catch { /* ignore */ }
        }

        // Material assignments
        const existingMA = (await fetchRouteMaterials(routeDbId)).data;
        const assignedMatIds = new Set(existingMA.map((a) => a.material_id));
        for (const ma of (node.material_assignments ?? []) as AnyObj[]) {
          const newMatId = resolveId(s(ma.material_id));
          if (!newMatId || assignedMatIds.has(newMatId)) continue;
          try {
            await assignMaterialToRoute(routeDbId, { material_id: newMatId });
          } catch { /* ignore */ }
        }
      }
    } catch (e) {
      res.errors.push(`Route "${route.name}": ${String(e)}`);
    }
  }
  void routeByKey;

  // ── Work Schedules ────────────────────────────────────────────────────────
  for (const ws of parsed.work_schedules) {
    onProgress(`Importing Work Schedule: ${ws.name}…`);
    let wsDbId: string;
    let wsSkipped = false;
    try {
      if (hasConflict("Work Schedule", ws.id)) {
        wsDbId = idMap.get(ws.id)!;
        if (shouldOverwrite("Work Schedule", ws.id)) {
          await updateWorkSchedule(wsDbId, {
            name: s(ws.name),
            description: sn(ws.description),
          });
          res.updated++;
          // Note: nested shifts/rotations/teams are not re-imported on overwrite
          // to avoid duplicating existing schedule data.
          wsSkipped = true; // skip creating nested items
        } else {
          res.skipped++;
          wsSkipped = true;
        }
      } else {
        const created = await createWorkSchedule({
          name: s(ws.name),
          description: sn(ws.description),
        });
        wsDbId = created.id;
        idMap.set(ws.id, wsDbId);
        res.created++;
      }

      if (wsSkipped) continue;

      // Shifts
      const shiftIdMap = new Map<string, string>(); // old shift id → new shift id
      for (const shift of (ws.shifts ?? []) as AnyObj[]) {
        try {
          const created = await createShift(wsDbId, {
            name: s(shift.name),
            description: sn(shift.description),
            start_time: s(shift.start_time, "06:00:00"),
            duration_seconds: n(shift.duration_seconds, 28800),
          });
          shiftIdMap.set(s(shift.id), created.id);
          idMap.set(s(shift.id), created.id);
          // Breaks
          for (const brk of (shift.breaks ?? []) as AnyObj[]) {
            try {
              await addBreak(wsDbId, created.id, {
                name: s(brk.name),
                description: sn(brk.description),
                start_time: s(brk.start_time, "10:00:00"),
                duration_seconds: n(brk.duration_seconds, 900),
              });
            } catch (e) {
              res.errors.push(`Shift break "${brk.name}": ${String(e)}`);
            }
          }
        } catch (e) {
          res.errors.push(`Shift "${shift.name}": ${String(e)}`);
        }
      }

      // Rotations
      const rotationIdMap = new Map<string, string>();
      for (const rot of (ws.rotations ?? []) as AnyObj[]) {
        try {
          const created = await createRotation(wsDbId, {
            name: s(rot.name),
            description: sn(rot.description),
          });
          rotationIdMap.set(s(rot.id), created.id);
          idMap.set(s(rot.id), created.id);
          // Segments
          for (const seg of (rot.segments ?? []) as AnyObj[]) {
            const shiftDbId = shiftIdMap.get(s(seg.shift_id)) ?? resolveId(s(seg.shift_id));
            if (!shiftDbId) continue;
            try {
              await addRotationSegment(wsDbId, created.id, {
                shift_id: shiftDbId,
                days_on: n(seg.days_on, 1),
                days_off: n(seg.days_off, 0),
                sequence: n(seg.sequence, 1),
              });
            } catch (e) {
              res.errors.push(`Rotation segment: ${String(e)}`);
            }
          }
        } catch (e) {
          res.errors.push(`Rotation "${rot.name}": ${String(e)}`);
        }
      }

      // Teams (rotation reference required; member references skipped — user-specific)
      for (const team of (ws.teams ?? []) as AnyObj[]) {
        const rotDbId = rotationIdMap.get(s(team.rotation_id)) ?? resolveId(s(team.rotation_id));
        if (!rotDbId) continue;
        try {
          await createTeam(wsDbId, {
            name: s(team.name),
            description: sn(team.description),
            rotation_id: rotDbId,
            rotation_start: s(team.rotation_start, new Date().toISOString().slice(0, 10)),
          });
        } catch (e) {
          res.errors.push(`Team "${team.name}": ${String(e)}`);
        }
      }

      // Non-working periods
      for (const nwp of (ws.non_working_periods ?? []) as AnyObj[]) {
        try {
          await createNonWorkingPeriod(wsDbId, {
            name: s(nwp.name),
            description: sn(nwp.description),
            start_datetime: s(nwp.start_datetime, new Date().toISOString()),
            duration_seconds: n(nwp.duration_seconds, 86400),
          });
        } catch (e) {
          res.errors.push(`Non-working period "${nwp.name}": ${String(e)}`);
        }
      }
    } catch (e) {
      res.errors.push(`Work Schedule "${ws.name}": ${String(e)}`);
    }
  }

  // ── Data Definitions ──────────────────────────────────────────────────────
  for (const dd of parsed.data_definitions) {
    onProgress(`Importing Data Definition: ${dd.code}…`);
    try {
      const uomId = resolveUomId(sn(dd.uom_symbol), sn(dd.uom_id));
      if (hasConflict("Data Definition", dd.id)) {
        if (shouldOverwrite("Data Definition", dd.id)) {
          await updateDataDefinition(idMap.get(dd.id)!, {
            name: s(dd.name),
            description: sn(dd.description),
            data_type: s(dd.data_type, "numeric"),
            uom_id: uomId,
            source: normaliseDataSource(s(dd.source, "manual")),
            is_required: typeof dd.is_required === "boolean" ? dd.is_required : false,
            enum_values: sn(dd.enum_values),
            lower_limit: dd.lower_limit != null ? n(dd.lower_limit) : null,
            upper_limit: dd.upper_limit != null ? n(dd.upper_limit) : null,
          });
          res.updated++;
        } else {
          res.skipped++;
        }
      } else {
        const created = await createDataDefinition({
          code: s(dd.code),
          name: s(dd.name),
          description: sn(dd.description),
          data_type: s(dd.data_type, "numeric"),
          uom_id: uomId,
          source: normaliseDataSource(s(dd.source, "manual")),
          is_required: typeof dd.is_required === "boolean" ? dd.is_required : false,
          enum_values: sn(dd.enum_values),
          lower_limit: dd.lower_limit != null ? n(dd.lower_limit) : null,
          upper_limit: dd.upper_limit != null ? n(dd.upper_limit) : null,
        });
        idMap.set(dd.id, created.id);
        res.created++;
      }
    } catch (e) {
      res.errors.push(`Data Definition "${dd.code}": ${String(e)}`);
    }
  }

  // ── Reason Codes (recursive) ──────────────────────────────────────────────
  const allReasons = await fetchReasons();
  const reasonByCode = new Map(allReasons.map((r) => [r.code, r]));

  async function importReasonTree(node: ReasonExportNode, parentDbId: string | null): Promise<void> {
    const { reason } = node;
    onProgress(`Importing Reason Code: ${reason.code}…`);
    let reasonDbId: string;
    try {
      if (hasConflict("Reason Code", reason.id)) {
        reasonDbId = idMap.get(reason.id)!;
        if (shouldOverwrite("Reason Code", reason.id)) {
          await updateReason(reasonDbId, {
            name: s(reason.name),
            description: sn(reason.description),
            oee_bucket: s(reason.oee_bucket, "downtime_unplanned"),
          });
          res.updated++;
        } else {
          res.skipped++;
        }
      } else {
        const existing = reasonByCode.get(s(reason.code));
        if (existing) {
          // Child reasons may not have been flagged as top-level conflicts
          reasonDbId = existing.id;
          idMap.set(reason.id, reasonDbId);
        } else {
          const created = await createReason({
            code: s(reason.code),
            name: s(reason.name),
            description: sn(reason.description),
            oee_bucket: s(reason.oee_bucket, "downtime_unplanned"),
            parent_id: parentDbId,
          });
          reasonDbId = created.id;
          idMap.set(reason.id, reasonDbId);
          reasonByCode.set(created.code, created);
          res.created++;
        }
      }

      for (const child of (node.children ?? []) as ReasonExportNode[]) {
        await importReasonTree(child, reasonDbId);
      }
    } catch (e) {
      res.errors.push(`Reason Code "${reason.code}": ${String(e)}`);
    }
  }

  for (const node of parsed.reason_codes) {
    await importReasonTree(node, null);
  }
  void finalProductByCode; // suppress unused warning

  return res;
}
