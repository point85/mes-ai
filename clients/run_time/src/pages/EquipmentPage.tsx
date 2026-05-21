import { useState, useEffect } from "react";
import EquipmentStatusPage from "./EquipmentStatusPage";
import PerformancePage from "./performance/PerformancePage";
import EquipmentTree from "../components/EquipmentTree";
import {
  fetchEquipmentMaterials,
  fetchEquipmentMaterialSetup,
  setEquipmentMaterialSetup,
  clearEquipmentMaterialSetup,
} from "../api/runtime";
import type { Equipment, EquipmentMaterialSetup, MaterialSetup } from "../types";

type EquipTab = "material_setup" | "monitor" | "performance";

const TABS: { id: EquipTab; label: string }[] = [
  { id: "material_setup", label: "Material Setup" },
  { id: "monitor", label: "Monitor" },
  { id: "performance", label: "Performance" },
];

export default function EquipmentPage() {
  const [tab, setTab] = useState<EquipTab>("material_setup");

  // ── Material Setup tab state ──────────────────────────────────────
  const [msEquipment, setMsEquipment] = useState<Equipment | null>(null);
  const [materialSetup, setMaterialSetupState] = useState<MaterialSetup | null>(null);
  const [configuredMaterials, setConfiguredMaterials] = useState<EquipmentMaterialSetup[]>([]);
  const [selectedEmId, setSelectedEmId] = useState("");
  const [jobNumber, setJobNumber] = useState("");
  const [setupBusy, setSetupBusy] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  // Load material setup and configured materials when equipment changes
  useEffect(() => {
    setMaterialSetupState(null);
    setConfiguredMaterials([]);
    setSelectedEmId("");
    setJobNumber("");
    setSetupError(null);

    if (!msEquipment) return;
    let cancelled = false;
    (async () => {
      try {
        const [ms, mats] = await Promise.all([
          fetchEquipmentMaterialSetup(msEquipment.id),
          fetchEquipmentMaterials(msEquipment.id),
        ]);
        if (!cancelled) {
          setMaterialSetupState(ms);
          setConfiguredMaterials(mats);
        }
      } catch {
        // non-critical
      }
    })();
    return () => { cancelled = true; };
  }, [msEquipment]);

  return (
    <div className="space-y-4">
      <div className="flex gap-1 border-b">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Material Setup tab ──────────────────────────────────────── */}
      <div className={tab === "material_setup" ? "space-y-4" : "hidden"}>
        <div className="flex gap-4">
          {/* Equipment picker */}
          <div className="w-64 shrink-0 bg-white rounded-lg border p-3 self-start">
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Select Equipment</p>
            <EquipmentTree
              selectedEquipmentId={msEquipment?.id ?? null}
              onSelectEquipment={(eq) => setMsEquipment(eq)}
              checkedNodeIds={new Set()}
              onToggleCheck={() => {}}
            />
          </div>

          {/* Setup controls */}
          <div className="flex-1 space-y-4">
            {!msEquipment && (
              <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
                <p className="text-sm">Select equipment from the tree to configure material setup.</p>
              </div>
            )}

            {msEquipment && (
              <>
                {/* Current Material Setup */}
                <div className="bg-white rounded-lg border p-4 space-y-3">
                  <h2 className="text-sm font-semibold text-gray-600 uppercase">
                    Current Material Setup — {msEquipment.code} ({msEquipment.name})
                  </h2>
                  {materialSetup?.equipment_material_id ? (
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                      <div>
                        <span className="text-gray-500">Material:</span>{" "}
                        <span className="font-medium">{materialSetup.material_name ?? "—"}</span>
                        {materialSetup.material_code && (
                          <span className="text-gray-400 ml-1">({materialSetup.material_code})</span>
                        )}
                      </div>
                      <div>
                        <span className="text-gray-500">Job Number:</span>{" "}
                        <span className="font-medium">{materialSetup.job_number || "—"}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Design Speed:</span>{" "}
                        <span className="font-medium">
                          {materialSetup.design_speed != null ? materialSetup.design_speed : "—"}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">Setup At:</span>{" "}
                        <span className="font-medium">
                          {materialSetup.setup_at
                            ? new Date(materialSetup.setup_at).toLocaleString()
                            : "—"}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400 italic">No material is currently set up.</p>
                  )}
                  {materialSetup?.equipment_material_id && (
                    <button
                      className="text-xs text-red-600 hover:text-red-800 font-medium disabled:opacity-50"
                      onClick={async () => {
                        if (!msEquipment) return;
                        setSetupBusy(true);
                        setSetupError(null);
                        try {
                          await clearEquipmentMaterialSetup(msEquipment.id);
                          setMaterialSetupState(null);
                        } catch (err: unknown) {
                          setSetupError(err instanceof Error ? err.message : String(err));
                        } finally {
                          setSetupBusy(false);
                        }
                      }}
                      disabled={setupBusy}
                    >
                      Clear Setup
                    </button>
                  )}
                </div>

                {/* Switch Material */}
                <div className="bg-white rounded-lg border p-4 space-y-3">
                  <h2 className="text-sm font-semibold text-gray-600 uppercase">
                    Switch Material
                  </h2>
                  {configuredMaterials.length === 0 ? (
                    <p className="text-sm text-gray-400 italic">
                      No materials configured for this equipment. Add material setups in the Design-Time client.
                    </p>
                  ) : (
                    <div className="flex flex-wrap items-end gap-3">
                      <label className="flex flex-col text-xs font-medium text-gray-600">
                        Material
                        <select
                          className="mt-0.5 rounded border border-gray-300 px-2 py-1.5 text-sm min-w-[220px]"
                          value={selectedEmId}
                          onChange={(e) => setSelectedEmId(e.target.value)}
                        >
                          <option value="">— Select material —</option>
                          {configuredMaterials.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.material_name ?? m.material_code ?? m.material_id} (speed: {m.design_speed} {m.design_speed_uom})
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="flex flex-col text-xs font-medium text-gray-600">
                        Job Number
                        <input
                          type="text"
                          className="mt-0.5 rounded border border-gray-300 px-2 py-1.5 text-sm w-40"
                          placeholder="Optional"
                          value={jobNumber}
                          onChange={(e) => setJobNumber(e.target.value)}
                        />
                      </label>

                      <button
                        className="px-4 py-1.5 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700 disabled:opacity-50"
                        disabled={!selectedEmId || setupBusy}
                        onClick={async () => {
                          if (!msEquipment || !selectedEmId) return;
                          setSetupBusy(true);
                          setSetupError(null);
                          try {
                            const result = await setEquipmentMaterialSetup(
                              msEquipment.id,
                              selectedEmId,
                              jobNumber || null,
                            );
                            setMaterialSetupState(result);
                            setSelectedEmId("");
                            setJobNumber("");
                          } catch (err: unknown) {
                            setSetupError(err instanceof Error ? err.message : String(err));
                          } finally {
                            setSetupBusy(false);
                          }
                        }}
                      >
                        {setupBusy ? "Switching…" : "Switch Material"}
                      </button>
                    </div>
                  )}

                  {setupError && (
                    <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                      {setupError}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <div className={tab === "monitor" ? undefined : "hidden"}>
        <EquipmentStatusPage />
      </div>
      <div className={tab === "performance" ? undefined : "hidden"}>
        <PerformancePage />
      </div>
    </div>
  );
}
