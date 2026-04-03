import api from "./client";

export interface PlantSeedSummary {
  sites: number;
  areas: number;
  production_lines: number;
  work_cells: number;
  equipment: number;
  equipment_materials: number;
}

export async function seedCPGPlantData(): Promise<PlantSeedSummary> {
  const { data } = await api.post<{ data: PlantSeedSummary }>("/demo/seed-cpg-plant");
  return data.data;
}
