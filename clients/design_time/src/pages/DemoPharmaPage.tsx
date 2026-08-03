/**
 * Pharma Demo page — seed the Solid-Dose Tablet Manufacturing ISA-95 physical model.
 */

import { useState } from "react";
import { seedPharmaPlantData, type PlantSeedSummary } from "../api/demo";
import { formatApiError } from "../api/errors";

export default function DemoPharmaPage() {
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<PlantSeedSummary | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  const handleSeed = async () => {
    setSeeding(true);
    setSeedError(null);
    setSeedResult(null);
    try {
      setSeedResult(await seedPharmaPlantData());
    } catch (err: unknown) {
      setSeedError(formatApiError(err, "Seed failed"));
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Pharma Demo</h1>
      <p className="mt-2 text-sm text-gray-500">
        Seed a Pharmaceutical Manufacturing scenario: Solid-Dose Tablet Line (Ibuprofen 200 mg).
      </p>

      {/* Scenario overview card */}
      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800">Process Overview</h2>
        <p className="mt-1 text-sm text-gray-500">
          Wet granulation → fluid-bed drying → milling → blending → tablet compression →
          in-process control (IPC) → film coating → QC release testing → blister packaging.
          Includes IPC rework loop and MRB escalation path (12 process segments, cGMP / ICH Q8).
        </p>
        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-600">
          <div className="rounded bg-green-50 border border-green-200 p-2">
            <p className="font-semibold text-green-800">Product</p>
            <p>Ibuprofen 200 mg<br />30-pack blister</p>
          </div>
          <div className="rounded bg-green-50 border border-green-200 p-2">
            <p className="font-semibold text-green-800">Batch Size</p>
            <p>50 000 tablets<br />≈ 14.95 kg coated</p>
          </div>
          <div className="rounded bg-green-50 border border-green-200 p-2">
            <p className="font-semibold text-green-800">Tracking</p>
            <p>Lot / batch<br />(process mfg)</p>
          </div>
          <div className="rounded bg-green-50 border border-green-200 p-2">
            <p className="font-semibold text-green-800">Compliance</p>
            <p>21 CFR Part 211<br />EU GMP / ICH Q8</p>
          </div>
        </div>
      </div>

      {/* Seed action card */}
      <div className="mt-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-800">
              Pharma Demo — Phoenix Pharmaceutical
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Seeds ISA-95 physical model: 1 site, 1 area, 1 production line, 10 work cells,
              12 equipment pieces (dual bin blenders &amp; dual tablet presses for dispatch
              demonstration), equipment classes &amp; capabilities, 12 storage locations
              (API vault, FG quarantine), and initial inventory transactions.
            </p>
          </div>
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="ml-4 rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
          >
            {seeding ? "Seeding…" : "Seed Pharma Demo"}
          </button>
        </div>

        {seedError && (
          <div className="mt-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {seedError}
          </div>
        )}

        {seedResult && (
          <div className="mt-3 rounded border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            <p className="font-medium mb-1">Pharma plant model seeded successfully</p>
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

      {/* Materials reference card */}
      <div className="mt-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-2">Materials Seeded</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-gray-600">
          <div>
            <p className="font-semibold text-gray-700 mb-1">API &amp; Excipients</p>
            <ul className="space-y-0.5">
              <li>RM-API-IBU — Ibuprofen API</li>
              <li>RM-EXC-MCC — Microcrystalline Cellulose</li>
              <li>RM-EXC-CCS — Croscarmellose Sodium</li>
              <li>RM-EXC-PVP — Povidone K30</li>
              <li>RM-EXC-MGST — Magnesium Stearate</li>
              <li>RM-COAT-OPW — Opadry White Film Coat</li>
              <li>RM-WATER-PW — Purified Water (WFI)</li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-gray-700 mb-1">Intermediates</p>
            <ul className="space-y-0.5">
              <li>SF-GRANULE — Dried Granule Blend</li>
              <li>SF-TABLET-UC — Uncoated Tablet Core</li>
            </ul>
            <p className="font-semibold text-gray-700 mt-2 mb-1">Finished Good</p>
            <ul className="space-y-0.5">
              <li>FG-IBU-200MG — Ibuprofen 200 mg 30-pack</li>
            </ul>
          </div>
          <div>
            <p className="font-semibold text-gray-700 mb-1">Packaging</p>
            <ul className="space-y-0.5">
              <li>PKG-BLISTER — Blister Base Film PVC/PVDC</li>
              <li>PKG-LIDDING — Blister Lidding Foil (Alu)</li>
              <li>PKG-CARTON — Folding Carton (30-pack)</li>
              <li>PKG-INSERT — Package Insert / SmPC</li>
              <li>PKG-SEAL — Tamper-Evident Seal</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
