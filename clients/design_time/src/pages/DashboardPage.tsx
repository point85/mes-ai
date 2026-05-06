/**
 * Dashboard — landing page for the DT-CLIENT.
 */

import { useState } from "react";
import { seedCPGPlantData, seedElectronicsPlantData, type PlantSeedSummary } from "../api/demo";
import { formatApiError } from "../api/errors";

export default function DashboardPage() {
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<PlantSeedSummary | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  const [seedingElec, setSeedingElec] = useState(false);
  const [seedElecResult, setSeedElecResult] = useState<PlantSeedSummary | null>(null);
  const [seedElecError, setSeedElecError] = useState<string | null>(null);

  const handleSeedCPG = async () => {
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

  const handleSeedElectronics = async () => {
    setSeedingElec(true);
    setSeedElecError(null);
    setSeedElecResult(null);
    try {
      setSeedElecResult(await seedElectronicsPlantData());
    } catch (err: unknown) {
      setSeedElecError(formatApiError(err, "Seed failed"));
    } finally {
      setSeedingElec(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      <p className="mt-2 text-sm text-gray-500">
        Welcome to the MES AI configuration console. Use the sidebar to navigate
        to editors for plant model, products, materials, and more.
      </p>

      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-800">CPG Demo — Juice Bottling Plant</h2>
            <p className="mt-1 text-sm text-gray-500">
              Seed ISA-95 physical model: 1 site, 1 area, 1 production line, 6 work cells, 7 equipment pieces, and material-equipment assignments.
            </p>
          </div>
          <button onClick={handleSeedCPG} disabled={seeding} className="ml-4 rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap">
            {seeding ? "Seeding…" : "Seed CPG Demo"}
          </button>
        </div>

        {seedError && <div className="mt-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{seedError}</div>}

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

      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-800">Electronics Demo — PCB Assembly Plant</h2>
            <p className="mt-1 text-sm text-gray-500">
              Seed ISA-95 physical model: 1 site, 1 area, 1 production line, 7 work cells, 8 equipment pieces (dual pick-and-place), and material-equipment assignments.
            </p>
          </div>
          <button onClick={handleSeedElectronics} disabled={seedingElec} className="ml-4 rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
            {seedingElec ? "Seeding\u2026" : "Seed Electronics Demo"}
          </button>
        </div>

        {seedElecError && <div className="mt-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{seedElecError}</div>}

        {seedElecResult && (
          <div className="mt-3 rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
            <p className="font-medium mb-1">Electronics plant model seeded successfully</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1 text-xs">
              <span>Sites: {seedElecResult.sites}</span>
              <span>Areas: {seedElecResult.areas}</span>
              <span>Lines: {seedElecResult.production_lines}</span>
              <span>Work Cells: {seedElecResult.work_cells}</span>
              <span>Equipment: {seedElecResult.equipment}</span>
              <span>Equip-Material Links: {seedElecResult.equipment_materials}</span>
            </div>
          </div>
        )}
      </div>


    </div>
  );
}
