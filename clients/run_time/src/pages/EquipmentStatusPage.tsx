import { useState, useEffect, useCallback, useRef } from "react";
import { ArrowPathIcon, CpuChipIcon } from "@heroicons/react/24/outline";
import EquipmentTree from "../components/EquipmentTree";
import type { CheckedNode } from "../components/EquipmentTree";
import {
  fetchEquipment,
  fetchEquipmentCurrentState,
  fetchEquipmentMaterialSetup,
  fetchUnits,
  fetchLots,
  fetchAllEquipmentInSite,
  fetchAllEquipmentInArea,
  fetchAllEquipmentInLine,
  fetchAllEquipmentInWorkCell,
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

function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const diffMs = Date.now() - new Date(iso).getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "< 1 min";
    if (diffMin < 60) return `${diffMin} min`;
    const diffHr = Math.floor(diffMin / 60);
    return `${diffHr}h ${diffMin % 60}m`;
  } catch {
    return "—";
  }
}

// ── per-equipment row data for summary table ──────────────────────

interface EquipRow {
  equipment: Equipment;
  state: EquipmentCurrentState | null;
  stateError: string | null;
  queuedCount: number;
  inProcessCount: number;
  uom: string;
  materialCode: string | null;
  materialName: string | null;
}

async function resolveEquipmentForNode(node: CheckedNode): Promise<Equipment[]> {
  try {
    switch (node.kind) {
      case "site":      return await fetchAllEquipmentInSite(node.id);
      case "area":      return await fetchAllEquipmentInArea(node.id);
      case "line":      return await fetchAllEquipmentInLine(node.id);
      case "workcell":  return await fetchAllEquipmentInWorkCell(node.id);
      case "equipment": {
        const eq = await fetchEquipment(node.id);
        return [eq];
      }
    }
  } catch {
    return [];
  }
}

async function loadEquipRow(eq: Equipment): Promise<EquipRow> {
  const [stateRes, unitsRes, lotsRes] = await Promise.allSettled([
    fetchEquipmentCurrentState(eq.id),
    fetchUnits({ equipment_id: eq.id }),
    fetchLots({ equipment_id: eq.id }),
  ]);
  const state = stateRes.status === "fulfilled" ? stateRes.value : null;
  const stateError = stateRes.status === "rejected" ? "No state model" : null;
  const units = unitsRes.status === "fulfilled" ? unitsRes.value : [];
  const lots = lotsRes.status === "fulfilled" ? lotsRes.value : [];
  const queued = units.filter((u) => u.status === "queued").length
    + lots.filter((l) => l.status === "queued").length;
  const inProc = units.filter((u) => u.status === "in_process").length
    + lots.filter((l) => l.status === "in_process").length;
  const uom = units.length > 0 ? "units" : lots.length > 0 ? "lots" : "—";

  // Material the equipment is set up for: read from the equipment's material-setup
  let materialCode: string | null = null;
  let materialName: string | null = null;
  try {
    const setup = await fetchEquipmentMaterialSetup(eq.id);
    materialCode = setup.material_code;
    materialName = setup.material_name;
  } catch { /* equipment has no material setup configured */ }

  return { equipment: eq, state, stateError, queuedCount: queued, inProcessCount: inProc, uom, materialCode, materialName };
}

export default function EquipmentStatusPage() {
  // ── single-equipment selection (detail pane) ─────────────────────
  const [selected, setSelected] = useState<Equipment | null>(null);
  const [detailEquipment, setDetailEquipment] = useState<Equipment | null>(null);
  const [detailState, setDetailState] = useState<EquipmentCurrentState | null>(null);
  const [detailStateError, setDetailStateError] = useState<string | null>(null);
  const [detailUnits, setDetailUnits] = useState<Unit[]>([]);
  const [detailLots, setDetailLots] = useState<Lot[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  // ── multi-monitor ────────────────────────────────────────────────
  const [checkedNodes, setCheckedNodes] = useState<Map<string, CheckedNode>>(new Map());
  const [monitoredEquip, setMonitoredEquip] = useState<Equipment[]>([]);
  const [summaryRows, setSummaryRows] = useState<EquipRow[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // ── refresh controls ─────────────────────────────────────────────
  const [refreshInterval, setRefreshInterval] = useState(10);
  const [refreshTick, setRefreshTick] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const checkedCount = checkedNodes.size;
  const showSummary = checkedCount > 0;
  const showSingleDetail = !showSummary && selected !== null;

  // ── auto-refresh timer ───────────────────────────────────────────
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (checkedCount > 0 || selected) {
      timerRef.current = setInterval(
        () => setRefreshTick((t) => t + 1),
        Math.max(1, refreshInterval) * 1000,
      );
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [checkedCount, selected, refreshInterval]);

  // ── detail pane loader ───────────────────────────────────────────
  const loadDetails = useCallback(async (equipId: string) => {
    setDetailLoading(true);
    setDetailStateError(null);
    try {
      const [eqRes, stateRes, unitsRes, lotsRes] = await Promise.allSettled([
        fetchEquipment(equipId),
        fetchEquipmentCurrentState(equipId),
        fetchUnits({ equipment_id: equipId }),
        fetchLots({ equipment_id: equipId }),
      ]);
      setDetailEquipment(eqRes.status === "fulfilled" ? eqRes.value : null);
      if (stateRes.status === "fulfilled") {
        setDetailState(stateRes.value);
      } else {
        setDetailState(null);
        setDetailStateError("No state model assigned (assumed available).");
      }
      setDetailUnits(unitsRes.status === "fulfilled" ? unitsRes.value : []);
      setDetailLots(lotsRes.status === "fulfilled" ? lotsRes.value : []);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (showSingleDetail) {
      void loadDetails(selected!.id);
    } else {
      setDetailEquipment(null);
      setDetailState(null);
      setDetailUnits([]);
      setDetailLots([]);
    }
  }, [selected, showSingleDetail, refreshTick, loadDetails]);

  // ── resolve equipment under checked nodes ────────────────────────
  useEffect(() => {
    if (checkedCount === 0) {
      setMonitoredEquip([]);
      setSummaryRows([]);
      return;
    }
    const nodes = Array.from(checkedNodes.values());
    void (async () => {
      const nested = await Promise.all(nodes.map(resolveEquipmentForNode));
      const seen = new Set<string>();
      const flat: Equipment[] = [];
      for (const eq of nested.flat()) {
        if (!seen.has(eq.id)) { seen.add(eq.id); flat.push(eq); }
      }
      setMonitoredEquip(flat);
    })();
  }, [checkedNodes]);

  // ── summary data loader ──────────────────────────────────────────
  useEffect(() => {
    if (monitoredEquip.length === 0) return;
    setSummaryLoading(true);
    void Promise.all(monitoredEquip.map(loadEquipRow))
      .then(setSummaryRows)
      .finally(() => setSummaryLoading(false));
  }, [monitoredEquip, refreshTick]);

  // ── handlers ─────────────────────────────────────────────────────
  function handleToggleCheck(node: CheckedNode) {
    setCheckedNodes((prev) => {
      // If already checked, uncheck it; otherwise replace with only this node
      if (prev.has(node.id)) return new Map();
      return new Map([[node.id, node]]);
    });
  }

  function handleSelectEquipment(eq: Equipment) {
    setSelected(eq);
    setCheckedNodes(new Map()); // clear group monitoring when direct select
  }

  // ── detail pane derived values ───────────────────────────────────
  const queuedUnits = detailUnits.filter((u) => u.status === "queued");
  const inProcessUnits = detailUnits.filter((u) => u.status === "in_process");
  const queuedLots = detailLots.filter((l) => l.status === "queued");
  const inProcessLots = detailLots.filter((l) => l.status === "in_process");
  const queueDepth = queuedUnits.length + inProcessUnits.length + queuedLots.length + inProcessLots.length;
  const maxQueue = detailEquipment?.max_queue_depth;
  const dispatchCategory = detailState?.dispatch_category ?? "available";
  const badgeClass = DISPATCH_BADGE[dispatchCategory] ?? "bg-gray-100 text-gray-800";

  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Left: tree */}
      <aside className="col-span-12 md:col-span-4 lg:col-span-3 bg-white border rounded-lg shadow-sm p-2 max-h-[calc(100vh-180px)] overflow-y-auto">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2 py-1">
          ISA-95 Hierarchy
        </h2>
        <p className="text-[10px] text-gray-400 px-2 pb-1">
          ☑ Check a node to monitor all equipment beneath it, or click a leaf to view details. Only one node can be checked at a time.
        </p>
        <EquipmentTree
          selectedEquipmentId={showSingleDetail ? (selected?.id ?? null) : null}
          onSelectEquipment={handleSelectEquipment}
          checkedNodeIds={new Set(checkedNodes.keys())}
          onToggleCheck={handleToggleCheck}
        />
      </aside>

      {/* Right: content */}
      <section className="col-span-12 md:col-span-8 lg:col-span-9 bg-white border rounded-lg shadow-sm p-4">

        {/* Refresh toolbar — shown whenever something is being monitored */}
        {(showSummary || showSingleDetail) && (
          <div className="flex flex-wrap items-center gap-3 mb-4 pb-3 border-b">
            <button
              onClick={() => setRefreshTick((t) => t + 1)}
              disabled={summaryLoading || detailLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              <ArrowPathIcon className={`h-4 w-4 ${(summaryLoading || detailLoading) ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <span>Refresh every</span>
              <input
                type="number"
                min={1}
                max={3600}
                className="w-16 rounded border border-gray-300 px-2 py-1 text-sm text-center"
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Math.max(1, Number(e.target.value)))}
              />
              <span>seconds</span>
            </label>
            {showSummary && (
              <span className="ml-auto text-xs text-gray-400">
                Monitoring {summaryRows.length} equipment
              </span>
            )}
          </div>
        )}

        {/* Empty state */}
        {!showSummary && !showSingleDetail && (
          <div className="text-center py-16 text-gray-400">
            <CpuChipIcon className="h-12 w-12 mx-auto mb-3 opacity-40" />
            <p>Select an equipment from the tree to view its current status,</p>
            <p className="text-sm mt-1">or check a node to monitor all equipment within it.</p>
          </div>
        )}

        {/* ── Summary table ── */}
        {showSummary && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  <th className="px-3 py-2 border-b">Equipment</th>
                  <th className="px-3 py-2 border-b">Description</th>
                  <th className="px-3 py-2 border-b">Material Code</th>
                  <th className="px-3 py-2 border-b">Material Name</th>
                  <th className="px-3 py-2 border-b text-right">Queued</th>
                  <th className="px-3 py-2 border-b text-right">In Process</th>
                  <th className="px-3 py-2 border-b">WIP</th>
                  <th className="px-3 py-2 border-b">State</th>
                  <th className="px-3 py-2 border-b">In State</th>
                  <th className="px-3 py-2 border-b">Dispatch</th>
                  <th className="px-3 py-2 border-b text-right">Queue Cap.</th>
                  <th className="px-3 py-2 border-b">OEE Bucket</th>
                </tr>
              </thead>
              <tbody>
                {summaryRows.length === 0 ? (
                  <tr>
                    <td colSpan={12} className="px-3 py-8 text-center text-gray-400 text-xs italic">
                      {summaryLoading ? "Loading…" : "No equipment found under selected nodes."}
                    </td>
                  </tr>
                ) : summaryRows.map(({ equipment: eq, state, stateError, queuedCount, inProcessCount, uom, materialCode, materialName }) => {
                  const dc = state?.dispatch_category ?? "available";
                  const bc = DISPATCH_BADGE[dc] ?? "bg-gray-100 text-gray-800";
                  return (
                    <tr
                      key={eq.id}
                      className="border-b hover:bg-indigo-50 cursor-pointer"
                      onClick={() => {
                        setSelected(eq);
                        setCheckedNodes(new Map());
                      }}
                      title="Click to open detail view"
                    >
                      <td className="px-3 py-2 font-medium text-indigo-700 whitespace-nowrap">
                        <span className="mr-1 text-indigo-400">⚙</span>{eq.code}
                      </td>
                      <td className="px-3 py-2 text-gray-600 max-w-xs truncate">{eq.description ?? eq.name}</td>
                      <td className="px-3 py-2 font-mono text-xs text-gray-700 whitespace-nowrap">{materialCode ?? "—"}</td>
                      <td className="px-3 py-2 text-gray-600 max-w-xs truncate">{materialName ?? "—"}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{queuedCount}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{inProcessCount}</td>
                      <td className="px-3 py-2 text-gray-500">{uom}</td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {stateError
                          ? <span className="text-xs text-amber-500 italic">—</span>
                          : <span className="font-medium">{state?.state ?? "—"}</span>
                        }
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                        {formatRelative(state?.started_at)}
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${bc}`}>
                          {dc}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right text-gray-600">
                        {eq.max_queue_depth ?? "∞"}
                      </td>
                      <td className="px-3 py-2 text-gray-600">{state?.oee_bucket ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Single equipment detail pane ── */}
        {showSingleDetail && (
          <>
            {/* Header */}
            <div className="flex items-start justify-between mb-6 pb-4 border-b">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <CpuChipIcon className="h-6 w-6 text-indigo-600" />
                  {selected!.code}
                </h1>
                <p className="text-sm text-gray-600 mt-1">{selected!.name}</p>
                {(detailEquipment?.description ?? selected!.description) && (
                  <p className="text-sm text-gray-500 mt-1">
                    {detailEquipment?.description ?? selected!.description}
                  </p>
                )}
              </div>
            </div>

            {/* Metrics grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <Metric label="State Model" value={detailState?.state_model ?? detailEquipment?.state_model_id ?? "—"} />
              <Metric label="Current State" value={detailState?.state ?? "—"} />
              <Metric
                label="Entered State At"
                value={formatDateTime(detailState?.started_at)}
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
                value={detailState?.oee_bucket ?? "—"}
              />
            </div>

            {detailStateError && (
              <p className="text-xs text-amber-600 mb-4 italic">{detailStateError}</p>
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
