/**
 * CPG Demo page — seed the Juice Bottling Plant ISA-95 physical model.
 */

import { useState } from "react";
import { seedCPGPlantData, type PlantSeedSummary } from "../api/demo";
import { formatApiError } from "../api/errors";

export default function DemoCpgPage() {
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<PlantSeedSummary | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  const handleSeed = async () => {
    setSeeding(true);
    setSeedError(null);
    setSeedResult(null);
    try {
      setSeedResult(await seedCPGPlantData());
    } catch (err: unknown) {
      setSeedError(formatApiError(err, "Seed failed"));
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">CPG Demo</h1>
      <p className="mt-2 text-sm text-gray-500">
        Seed a Consumer Packaged Goods scenario: Juice Bottling Plant.
      </p>

      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-800">CPG Demo — Juice Bottling Plant</h2>
            <p className="mt-1 text-sm text-gray-500">
              Seed ISA-95 physical model: 1 site, 1 area, 1 production line, 6 work cells, 7 equipment
              pieces, and material-equipment assignments.
            </p>
          </div>
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="ml-4 rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
          >
            {seeding ? "Seeding…" : "Seed CPG Demo"}
          </button>
        </div>

        {seedError && (
          <div className="mt-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {seedError}
          </div>
        )}

        {seedResult && (
          <div className="mt-3 rounded border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-800">
            <p className="font-medium mb-1">Plant model seeded successfully</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1 text-xs">
              <span>Sites: {seedResult.sites}</span>
              <span>Areas: {seedResult.areas}</span>
              <span>Lines: {seedResult.production_lines}</span>
              <span>Work Cells: {seedResult.work_cells}</span>
              <span>Equipment: {seedResult.equipment}</span>
              <span>Equip-Material Links: {seedResult.equipment_materials}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
