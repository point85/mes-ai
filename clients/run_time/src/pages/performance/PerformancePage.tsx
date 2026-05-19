import { useState, useEffect, useCallback } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { fetchEquipmentStates, fetchCounters, fetchAllEquipment } from "../../api/runtime";
import type { EquipmentStateLog, ProductionCounter, Equipment } from "../../types";

const catColors: Record<string, string> = {
  available: "bg-green-50 text-green-700",
  busy: "bg-amber-50 text-amber-700",
  unavailable_planned: "bg-blue-50 text-blue-700",
  unavailable_unplanned: "bg-red-50 text-red-700",
};

const SELECT_CLS =
  "rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500";

export default function PerformancePage() {
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [equipMap, setEquipMap] = useState<Map<string, string>>(new Map()); // id -> name

  const [states, setStates] = useState<EquipmentStateLog[]>([]);
  const [statesEquipId, setStatesEquipId] = useState("");
  const [statesLoading, setStatesLoading] = useState(true);
  const [statesError, setStatesError] = useState<string | null>(null);

  const [counters, setCounters] = useState<ProductionCounter[]>([]);
  const [countersEquipId, setCountersEquipId] = useState("");
  const [countersLoading, setCountersLoading] = useState(true);
  const [countersError, setCountersError] = useState<string | null>(null);

  // Load equipment list once
  useEffect(() => {
    fetchAllEquipment()
      .then((list) => {
        const sorted = list.sort((a, b) => a.name.localeCompare(b.name));
        setEquipment(sorted);
        setEquipMap(new Map(sorted.map((e) => [e.id, e.name])));
      })
      .catch(() => {/* non-critical */});
  }, []);

  const equipName = (id: string) => equipMap.get(id) ?? id.slice(0, 8) + "…";

  const loadStates = useCallback(async (equipId?: string) => {
    setStatesLoading(true);
    setStatesError(null);
    try {
      setStates(await fetchEquipmentStates(equipId || undefined));
    } catch {
      setStatesError("Failed to load equipment states. Is the server running?");
    } finally {
      setStatesLoading(false);
    }
  }, []);

  const loadCounters = useCallback(async (equipId?: string) => {
    setCountersLoading(true);
    setCountersError(null);
    try {
      setCounters(await fetchCounters(equipId || undefined));
    } catch {
      setCountersError("Failed to load counters. Is the server running?");
    } finally {
      setCountersLoading(false);
    }
  }, []);

  useEffect(() => { loadStates(); }, [loadStates]);
  useEffect(() => { loadCounters(); }, [loadCounters]);

  const handleStatesEquipChange = (id: string) => {
    setStatesEquipId(id);
    loadStates(id || undefined);
  };

  const handleCountersEquipChange = (id: string) => {
    setCountersEquipId(id);
    loadCounters(id || undefined);
  };

  return (
    <div className="space-y-8">
      {/* ─── Equipment State Logs ─────────────────────────────────── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-800">Equipment State Log</h2>
            <select
              value={statesEquipId}
              onChange={(e) => handleStatesEquipChange(e.target.value)}
              className={SELECT_CLS}
            >
              <option value="">All Equipment</option>
              {equipment.map((eq) => (
                <option key={eq.id} value={eq.id}>{eq.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => loadStates(statesEquipId || undefined)} disabled={statesLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 shadow-sm">
              <ArrowPathIcon className={`h-4 w-4 ${statesLoading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>
        </div>

        {statesLoading && <p className="text-sm text-gray-500">Loading state logs…</p>}
        {statesError && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{statesError}</div>
        )}

        {!statesLoading && !statesError && (
          <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Equipment", "State", "Category", "OEE Bucket", "Started", "Ended"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {states.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5 text-sm text-gray-900">{equipName(s.equipment_id)}</td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">
                      {s.state}{s.sub_state && <span className="text-gray-400 ml-1">/ {s.sub_state}</span>}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${catColors[s.dispatch_category] ?? "bg-gray-100 text-gray-600"}`}>
                        {s.dispatch_category.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-600">{s.oee_bucket.replace(/_/g, " ")}</td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">{new Date(s.started_at).toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">{s.ended_at ? new Date(s.ended_at).toLocaleString() : "—"}</td>
                  </tr>
                ))}
                {states.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">No equipment state logs found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ─── Production Counters ──────────────────────────────────── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-800">Production Counters</h2>
            <select
              value={countersEquipId}
              onChange={(e) => handleCountersEquipChange(e.target.value)}
              className={SELECT_CLS}
            >
              <option value="">All Equipment</option>
              {equipment.map((eq) => (
                <option key={eq.id} value={eq.id}>{eq.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => loadCounters(countersEquipId || undefined)} disabled={countersLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 shadow-sm">
              <ArrowPathIcon className={`h-4 w-4 ${countersLoading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>
        </div>

        {countersLoading && <p className="text-sm text-gray-500">Loading counters…</p>}
        {countersError && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{countersError}</div>
        )}

        {!countersLoading && !countersError && (
          <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Equipment", "Shift Date", "Good", "Reject", "Rework", "Cycle (s)", "Run Time (s)"].map((h, i) => (
                    <th key={h} className={`px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500 ${i >= 2 ? "text-right" : "text-left"}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {counters.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5 text-sm text-gray-900">{equipName(c.equipment_id)}</td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">{c.shift_date}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-green-700">{c.good_count}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-red-600">{c.reject_count}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-amber-600">{c.rework_count}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-600">{c.ideal_cycle_time_sec ?? "—"}</td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-600">{c.actual_run_time_sec ?? "—"}</td>
                  </tr>
                ))}
                {counters.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">No production counters found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

    </div>
  );
}
