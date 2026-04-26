import { useState, useEffect, useCallback } from "react";
import { ArrowPathIcon, CpuChipIcon } from "@heroicons/react/24/outline";
import EquipmentTree from "../components/EquipmentTree";
import {
  fetchEquipment,
  fetchEquipmentCurrentState,
  fetchUnits,
  fetchLots,
} from "../api/runtime";
import type { Equipment, EquipmentCurrentState, Unit, Lot } from "../types";

const DISPATCH_BADGE: Record<string, string> = {
  available: "bg-emerald-100 text-emerald-800",
  busy: "bg-blue-100 text-blue-800",
  unavailable_planned: "bg-amber-100 text-amber-800",
  unavailable_unplanned: "bg-red-100 text-red-800",
};

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function EquipmentStatusPage() {
  const [selected, setSelected] = useState<Equipment | null>(null);
  const [equipment, setEquipment] = useState<Equipment | null>(null);
  const [currentState, setCurrentState] = useState<EquipmentCurrentState | null>(null);
  const [stateError, setStateError] = useState<string | null>(null);
  const [units, setUnits] = useState<Unit[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);

  const loadDetails = useCallback(async (equipId: string) => {
    setLoading(true);
    setStateError(null);
    try {
      // Parallel fetch — current state may 404 if equipment has no state model yet
      const [eqRes, stateRes, unitsRes, lotsRes] = await Promise.allSettled([
        fetchEquipment(equipId),
        fetchEquipmentCurrentState(equipId),
        fetchUnits({ equipment_id: equipId }),
        fetchLots({ equipment_id: equipId }),
      ]);
      setEquipment(eqRes.status === "fulfilled" ? eqRes.value : null);
      if (stateRes.status === "fulfilled") {
        setCurrentState(stateRes.value);
      } else {
        setCurrentState(null);
        setStateError("No state model assigned (assumed available).");
      }
      setUnits(unitsRes.status === "fulfilled" ? unitsRes.value : []);
      setLots(lotsRes.status === "fulfilled" ? lotsRes.value : []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selected) {
      void loadDetails(selected.id);
    } else {
      setEquipment(null);
      setCurrentState(null);
      setUnits([]);
      setLots([]);
    }
  }, [selected, refreshTick, loadDetails]);

  const queuedUnits = units.filter((u) => u.status === "queued");
  const inProcessUnits = units.filter((u) => u.status === "in_process");
  const queuedLots = lots.filter((l) => l.status === "queued");
  const inProcessLots = lots.filter((l) => l.status === "in_process");

  const queueDepth = queuedUnits.length + inProcessUnits.length + queuedLots.length + inProcessLots.length;
  const maxQueue = equipment?.max_queue_depth;

  const dispatchCategory = currentState?.dispatch_category ?? "available";
  const badgeClass = DISPATCH_BADGE[dispatchCategory] ?? "bg-gray-100 text-gray-800";

  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Left: tree */}
      <aside className="col-span-12 md:col-span-4 lg:col-span-3 bg-white border rounded-lg shadow-sm p-2 max-h-[calc(100vh-180px)] overflow-y-auto">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2 py-1">
          ISA-95 Hierarchy
        </h2>
        <EquipmentTree
          selectedEquipmentId={selected?.id ?? null}
          onSelectEquipment={(eq) => setSelected(eq)}
        />
      </aside>

      {/* Right: details */}
      <section className="col-span-12 md:col-span-8 lg:col-span-9 bg-white border rounded-lg shadow-sm p-6">
        {!selected ? (
          <div className="text-center py-16 text-gray-400">
            <CpuChipIcon className="h-12 w-12 mx-auto mb-3 opacity-40" />
            <p>Select an equipment from the tree to view its current status.</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-start justify-between mb-6 pb-4 border-b">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <CpuChipIcon className="h-6 w-6 text-indigo-600" />
                  {selected.code}
                </h1>
                <p className="text-sm text-gray-600 mt-1">{selected.name}</p>
                {(equipment?.description ?? selected.description) && (
                  <p className="text-sm text-gray-500 mt-1">
                    {equipment?.description ?? selected.description}
                  </p>
                )}
              </div>
              <button
                onClick={() => setRefreshTick((t) => t + 1)}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                <ArrowPathIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>

            {/* Metrics grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <Metric label="State Model" value={currentState?.state_model ?? equipment?.state_model_id ?? "—"} />
              <Metric label="Current State" value={currentState?.state ?? "—"} />
              <Metric
                label="Entered State At"
                value={formatDateTime(currentState?.started_at)}
              />
              <Metric
                label="Dispatch State"
                value={
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${badgeClass}`}>
                    {dispatchCategory}
                  </span>
                }
              />
              <Metric
                label="Queue Capacity"
                value={`${queueDepth} / ${maxQueue ?? "∞"}`}
              />
              <Metric
                label="OEE Bucket"
                value={currentState?.oee_bucket ?? "—"}
              />
            </div>

            {stateError && (
              <p className="text-xs text-amber-600 mb-4 italic">{stateError}</p>
            )}

            {/* Queue contents */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <WipList
                title="Queued for Processing"
                emptyText="Nothing queued"
                units={queuedUnits}
                lots={queuedLots}
              />
              <WipList
                title="Currently Being Processed"
                emptyText="Nothing in process"
                units={inProcessUnits}
                lots={inProcessLots}
              />
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-gray-50 rounded-md px-3 py-2">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-sm font-medium text-gray-900 mt-1">{value}</p>
    </div>
  );
}

function WipList({
  title,
  emptyText,
  units,
  lots,
}: {
  title: string;
  emptyText: string;
  units: Unit[];
  lots: Lot[];
}) {
  const total = units.length + lots.length;
  return (
    <div className="border rounded-md">
      <div className="px-3 py-2 bg-gray-50 border-b flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        <span className="text-xs text-gray-500">{total} item{total === 1 ? "" : "s"}</span>
      </div>
      <div className="p-3">
        {total === 0 ? (
          <p className="text-xs text-gray-400 italic">{emptyText}</p>
        ) : (
          <ul className="space-y-1.5">
            {units.map((u) => (
              <li key={u.id} className="flex items-center gap-2 text-sm">
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">UNIT</span>
                <span className="font-mono text-gray-800">{u.serial_number}</span>
              </li>
            ))}
            {lots.map((l) => (
              <li key={l.id} className="flex items-center gap-2 text-sm">
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">LOT</span>
                <span className="font-mono text-gray-800">{l.lot_number}</span>
                <span className="text-xs text-gray-500">qty {l.quantity}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
