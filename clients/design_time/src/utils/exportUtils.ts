/**
 * Export utilities — fetch selected DT objects from the API and build a zip archive.
 *
 * Zip structure:
 *   sites/              <site_code>.json   (full hierarchy: areas → lines → work-cells → equipment)
 *   equipment_classes/  <class_code>.json  (class + properties)
 *   storage_locations/  <loc_code>.json
 *   products/           <product_code>.json (product + BOMs + BOM items)
 *   routes/             <route_name_version>.json (route + steps + params + requirements + assignments)
 *   dispositions/       <disp_code>.json
 *   materials/          <mat_code>.json
 *   uom/                <uom_symbol>.json
 *   work_schedules/     <schedule_name>.json (full nested: shifts/breaks/rotations/teams)
 *   data_definitions/   <def_code>.json
 *   reason_codes/       <reason_code>.json  (reason + all descendants)
 */

import JSZip from "jszip";
import type { Reason } from "../types";
import {
  fetchSite,
  fetchAreas,
  fetchLines,
  fetchWorkCells,
  fetchEquipment,
  fetchEquipmentMaterials,
  fetchEquipmentCapabilities,
  fetchEquipmentClassDetail,
  fetchStorageLocation,
  fetchProduct,
  fetchBOMs,
  fetchBOMItems,
  fetchRoute,
  fetchRouteSteps,
  fetchStepParameters,
  fetchStepEquipmentRequirements,
  fetchStepMaterialRequirements,
  fetchRouteProducts,
  fetchRouteMaterials,
  fetchDispositions,
  fetchMaterial,
  fetchUoM,
  fetchWorkSchedule,
  fetchDataDefinition,
  fetchReasons,
} from "../api";

export interface ExportSelection {
  sites: string[];
  equipment_classes: string[];
  storage_locations: string[];
  products: string[];
  routes: string[];
  dispositions: string[];
  materials: string[];
  uom: string[];
  work_schedules: string[];
  data_definitions: string[];
  reason_codes: string[]; // top-level reason IDs only
}

function sanitize(name: string): string {
  return name
    .replace(/[/\\:*?"<>|]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 100);
}

// ─── Reason subtree builder ─────────────────────────────────────────────────

function buildReasonSubtree(
  rootId: string,
  allReasons: Reason[],
): object {
  const root = allReasons.find((r) => r.id === rootId);
  if (!root) return {};
  const children = allReasons
    .filter((r) => r.parent_id === rootId)
    .map((child) => buildReasonSubtree(child.id, allReasons));
  return { reason: root, children };
}

// ─── Main zip builder ───────────────────────────────────────────────────────

export async function buildExportZip(
  selection: ExportSelection,
  onProgress?: (msg: string) => void,
): Promise<Blob> {
  const zip = new JSZip();

  // ── Sites (full hierarchy) ──────────────────────────────────────────
  if (selection.sites.length > 0) {
    const folder = zip.folder("sites")!;
    for (const siteId of selection.sites) {
      const site = await fetchSite(siteId);
      onProgress?.(`Exporting site ${site.code}…`);
      const areasResp = await fetchAreas(siteId);
      const areas: object[] = [];
      for (const area of areasResp.data) {
        const linesResp = await fetchLines(area.id);
        const lines: object[] = [];
        for (const line of linesResp.data) {
          const wcsResp = await fetchWorkCells(line.id);
          const workCells: object[] = [];
          for (const wc of wcsResp.data) {
            const [equipResp] = await Promise.all([fetchEquipment(wc.id)]);
            const equipment: object[] = [];
            for (const equip of equipResp.data) {
              const [matsResp, capsResp] = await Promise.all([
                fetchEquipmentMaterials(equip.id),
                fetchEquipmentCapabilities(equip.id),
              ]);
              equipment.push({
                equipment: equip,
                materials: matsResp.data,
                capabilities: capsResp.data,
              });
            }
            workCells.push({ work_cell: wc, equipment });
          }
          lines.push({ line, work_cells: workCells });
        }
        areas.push({ area, lines });
      }
      const payload = { site, areas };
      folder.file(
        `${sanitize(site.code)}.json`,
        JSON.stringify(payload, null, 2),
      );
    }
  }

  // ── Equipment Classes ──────────────────────────────────────────────
  if (selection.equipment_classes.length > 0) {
    const folder = zip.folder("equipment_classes")!;
    for (const classId of selection.equipment_classes) {
      const detail = await fetchEquipmentClassDetail(classId);
      onProgress?.(`Exporting equipment class ${detail.code}…`);
      folder.file(
        `${sanitize(detail.code)}.json`,
        JSON.stringify(detail, null, 2),
      );
    }
  }

  // ── Storage Locations ──────────────────────────────────────────────
  if (selection.storage_locations.length > 0) {
    const folder = zip.folder("storage_locations")!;
    for (const locId of selection.storage_locations) {
      const loc = await fetchStorageLocation(locId);
      onProgress?.(`Exporting storage location ${loc.code}…`);
      folder.file(
        `${sanitize(loc.code)}.json`,
        JSON.stringify(loc, null, 2),
      );
    }
  }

  // ── Products (product + BOMs + BOM items) ──────────────────────────
  if (selection.products.length > 0) {
    const folder = zip.folder("products")!;
    for (const productId of selection.products) {
      const product = await fetchProduct(productId);
      onProgress?.(`Exporting product ${product.code}…`);
      const bomsResp = await fetchBOMs(productId);
      const boms: object[] = [];
      for (const bom of bomsResp.data) {
        const itemsResp = await fetchBOMItems(bom.id);
        boms.push({ bom, items: itemsResp.data });
      }
      const payload = { product, boms };
      folder.file(
        `${sanitize(product.code)}.json`,
        JSON.stringify(payload, null, 2),
      );
    }
  }

  // ── Routes (route + steps + parameters + requirements + assignments) ─
  if (selection.routes.length > 0) {
    const folder = zip.folder("routes")!;
    for (const routeId of selection.routes) {
      const route = await fetchRoute(routeId);
      onProgress?.(`Exporting route ${route.name}…`);
      const [stepsResp, productAssignments, materialAssignments] =
        await Promise.all([
          fetchRouteSteps(routeId),
          fetchRouteProducts(routeId),
          fetchRouteMaterials(routeId),
        ]);
      const steps: object[] = [];
      for (const step of stepsResp.data) {
        const [params, equipReqs, matReqs] = await Promise.all([
          fetchStepParameters(step.id),
          fetchStepEquipmentRequirements(step.id),
          fetchStepMaterialRequirements(step.id),
        ]);
        steps.push({
          step,
          parameters: params.data,
          equipment_requirements: equipReqs.data,
          material_requirements: matReqs.data,
        });
      }
      const payload = {
        route,
        steps,
        product_assignments: productAssignments.data,
        material_assignments: materialAssignments.data,
      };
      const filename = sanitize(`${route.name}_v${route.version}`);
      folder.file(`${filename}.json`, JSON.stringify(payload, null, 2));
    }
  }

  // ── Dispositions ───────────────────────────────────────────────────
  if (selection.dispositions.length > 0) {
    onProgress?.(`Exporting ${selection.dispositions.length} disposition(s)…`);
    const folder = zip.folder("dispositions")!;
    const allDisps = (await fetchDispositions()).data;
    for (const dispId of selection.dispositions) {
      const disp = allDisps.find((d) => d.id === dispId);
      if (disp) {
        folder.file(
          `${sanitize(disp.code)}.json`,
          JSON.stringify(disp, null, 2),
        );
      }
    }
  }

  // ── Materials ──────────────────────────────────────────────────────
  if (selection.materials.length > 0) {
    const folder = zip.folder("materials")!;
    for (const matId of selection.materials) {
      const mat = await fetchMaterial(matId);
      onProgress?.(`Exporting material ${mat.code}…`);
      folder.file(
        `${sanitize(mat.code)}.json`,
        JSON.stringify(mat, null, 2),
      );
    }
  }

  // ── Units of Measure ───────────────────────────────────────────────
  if (selection.uom.length > 0) {
    const folder = zip.folder("uom")!;
    for (const uomId of selection.uom) {
      const uom = await fetchUoM(uomId);
      onProgress?.(`Exporting UoM ${uom.symbol}…`);
      folder.file(
        `${sanitize(uom.symbol)}.json`,
        JSON.stringify(uom, null, 2),
      );
    }
  }

  // ── Work Schedules ─────────────────────────────────────────────────
  if (selection.work_schedules.length > 0) {
    const folder = zip.folder("work_schedules")!;
    for (const schedId of selection.work_schedules) {
      const schedule = await fetchWorkSchedule(schedId);
      onProgress?.(`Exporting work schedule ${schedule.name}…`);
      folder.file(
        `${sanitize(schedule.name)}.json`,
        JSON.stringify(schedule, null, 2),
      );
    }
  }

  // ── Data Definitions ───────────────────────────────────────────────
  if (selection.data_definitions.length > 0) {
    const folder = zip.folder("data_definitions")!;
    for (const defId of selection.data_definitions) {
      const def = await fetchDataDefinition(defId);
      onProgress?.(`Exporting data definition ${def.code}…`);
      folder.file(
        `${sanitize(def.code)}.json`,
        JSON.stringify(def, null, 2),
      );
    }
  }

  // ── Reason Codes (with descendants) ────────────────────────────────
  if (selection.reason_codes.length > 0) {
    const folder = zip.folder("reason_codes")!;
    const allReasons = await fetchReasons();
    for (const reasonId of selection.reason_codes) {
      const root = allReasons.find((r) => r.id === reasonId);
      if (root) {
        onProgress?.(`Exporting reason code ${root.code}…`);
        const subtree = buildReasonSubtree(reasonId, allReasons);
        folder.file(
          `${sanitize(root.code)}.json`,
          JSON.stringify(subtree, null, 2),
        );
      }
    }
  }

  onProgress?.("Building zip archive…");
  return zip.generateAsync({ type: "blob", compression: "DEFLATE" });
}
