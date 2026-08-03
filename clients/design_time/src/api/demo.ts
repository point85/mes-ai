import api from "./client";

export interface PlantSeedSummary {
  sites: number;
  areas: number;
  production_lines: number;
  work_cells: number;
  equipment: number;
  equipment_materials: number;
}

/**
 * Seed both ERP-side and plant-side CPG demo data.
 * The ERP seed must run first (plant seeder asserts the route exists),
 * and both endpoints are additive — re-running picks up any new
 * transitions, dispositions, equipment, etc. added to the data files.
 */
export async function seedCPGPlantData(): Promise<PlantSeedSummary> {
  await api.post("/demo/seed-cpg-erp");
  const { data } = await api.post<{ data: PlantSeedSummary }>("/demo/seed-cpg-plant");
  return data.data;
}

export async function seedElectronicsPlantData(): Promise<PlantSeedSummary> {
  await api.post("/demo/seed-electronics-erp");
  const { data } = await api.post<{ data: PlantSeedSummary }>("/demo/seed-electronics-plant");
  return data.data;
}

export async function seedPharmaPlantData(): Promise<PlantSeedSummary> {
  await api.post("/demo/seed-pharma-erp");
  const { data } = await api.post<{ data: PlantSeedSummary }>("/demo/seed-pharma-plant");
  return data.data;
}
