import { useEffect, useState } from "react";
import {
  fetchSites,
  fetchAreas,
  fetchLines,
  fetchWorkCells,
  fetchEquipmentInWorkCell,
  fetchCurrentState,
  fetchStateModels,
  transitionEquipment,
} from "../api/endpoints";
import DataTable, { type Column } from "../components/DataTable";
import StateBadge from "../components/StateBadge";
import type {
  Site,
  Area,
  ProductionLine,
  WorkCell,
  Equipment,
  EquipmentCurrentState,
  StateModel,
  TransitionDefinition,
} from "../types";

interface Selection {
  siteId?: string;
  areaId?: string;
  lineId?: string;
  wcId?: string;
}

export default function EquipmentPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [lines, setLines] = useState<ProductionLine[]>([]);
  const [workCells, setWorkCells] = useState<WorkCell[]>([]);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [sel, setSel] = useState<Selection>({});
  const [loading, setLoading] = useState(false);

  // Transition control state
  const [selectedEquip, setSelectedEquip] = useState<Equipment | null>(null);
  const [current, setCurrent] = useState<EquipmentCurrentState | null>(null);
  const [models, setModels] = useState<StateModel[]>([]);
  const [reasonCode, setReasonCode] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  // Load sites + state models on mount
  useEffect(() => {
    fetchSites().then(setSites).catch(() => {});
    fetchStateModels().then(setModels).catch(() => {});
  }, []);

  // Load areas when site changes
  useEffect(() => {
    setAreas([]); setLines([]); setWorkCells([]); setEquipment([]);
    clearSelection();
    if (!sel.siteId) return;
    fetchAreas(sel.siteId).then(setAreas).catch(() => {});
  }, [sel.siteId]);

  // Load lines when area changes
  useEffect(() => {
    setLines([]); setWorkCells([]); setEquipment([]);
    clearSelection();
    if (!sel.areaId) return;
    fetchLines(sel.areaId).then(setLines).catch(() => {});
  }, [sel.areaId]);

  // Load work cells when line changes
  useEffect(() => {
    setWorkCells([]); setEquipment([]);
    clearSelection();
    if (!sel.lineId) return;
    fetchWorkCells(sel.lineId).then(setWorkCells).catch(() => {});
  }, [sel.lineId]);

  // Load equipment when work cell changes
  useEffect(() => {
    setEquipment([]);
    clearSelection();
    if (!sel.wcId) return;
    setLoading(true);
    fetchEquipmentInWorkCell(sel.wcId)
      .then(setEquipment)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sel.wcId]);

  function clearSelection() {
    setSelectedEquip(null);
    setCurrent(null);
    setError(null);
    setLastResult(null);
  }

  async function selectEquipment(eq: Equipment) {
    setSelectedEquip(eq);
    setCurrent(null);
    setError(null);
    setLastResult(null);
    setReasonCode("");
    setNotes("");
    try {
      const st = await fetchCurrentState(eq.id);
      setCurrent(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Failed to load state: ${msg}`);
    }
  }

  async function doTransition(t: TransitionDefinition) {
    if (!selectedEquip) return;
    setBusy(true);
    setError(null);
    setLastResult(null);
    try {
      const log = await transitionEquipment(
        selectedEquip.id,
        t.to_state,
        reasonCode || undefined,
        notes || undefined,
      );
      setLastResult(
        `Transitioned to "${log.state}" at ${new Date(log.started_at).toLocaleTimeString()}`,
      );
      const st = await fetchCurrentState(selectedEquip.id);
      setCurrent(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Transition failed: ${msg}`);
    } finally {
      setBusy(false);
    }
  }

  const fullModel = models.find((m) => m.model_id === current?.state_model);

  const equipColumns: Column<Equipment>[] = [
    { key: "code", header: "Code" },
    { key: "name", header: "Name" },
    { key: "equipment_type", header: "Type", render: (r) => r.equipment_type ?? "—" },
    { key: "status", header: "Status" },
    {
      key: "state_model_id",
      header: "State Model",
      render: (r) => r.state_model_id ?? <span className="text-gray-400">none</span>,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Hierarchy selectors */}
      <div className="flex flex-wrap gap-3">
        <Select
          label="Site"
          value={sel.siteId ?? ""}
          options={sites.map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` }))}
          onChange={(v) => setSel({ siteId: v || undefined })}
        />
        <Select
          label="Area"
          value={sel.areaId ?? ""}
          options={areas.map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }))}
          onChange={(v) => setSel((p) => ({ ...p, areaId: v || undefined, lineId: undefined, wcId: undefined }))}
          disabled={!sel.siteId}
        />
        <Select
          label="Line"
          value={sel.lineId ?? ""}
          options={lines.map((l) => ({ value: l.id, label: `${l.code} — ${l.name}` }))}
          onChange={(v) => setSel((p) => ({ ...p, lineId: v || undefined, wcId: undefined }))}
          disabled={!sel.areaId}
        />
        <Select
          label="Work Cell"
          value={sel.wcId ?? ""}
          options={workCells.map((wc) => ({ value: wc.id, label: `${wc.code} — ${wc.name}` }))}
          onChange={(v) => setSel((p) => ({ ...p, wcId: v || undefined }))}
          disabled={!sel.lineId}
        />
      </div>

      {/* Equipment table */}
      {loading ? (
        <p className="text-gray-500 text-sm">Loading equipment…</p>
      ) : (
        <DataTable
          columns={equipColumns}
          data={equipment}
          emptyMessage={sel.wcId ? "No equipment in this work cell" : "Select a work cell above"}
          onRowClick={selectEquipment}
        />
      )}

      {/* Quick summary */}
      {equipment.length > 0 && (
        <div className="flex gap-4 text-sm text-gray-600">
          <span>Total: <strong>{equipment.length}</strong></span>
          <span>
            With state model:{" "}
            <strong>{equipment.filter((e) => e.state_model_id).length}</strong>
          </span>
        </div>
      )}

      {/* ── Transition Control Panel ──────────────────────────────── */}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {selectedEquip && current && (
        <div className="bg-white rounded-lg border p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-600 uppercase">
              Transition Control — {selectedEquip.code} ({selectedEquip.name})
            </h2>
            <button
              className="text-xs text-gray-400 hover:text-gray-600"
              onClick={clearSelection}
            >
              ✕ close
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500 text-xs">State Model</span>
              <p className="font-medium">{current.state_model}</p>
            </div>
            <div>
              <span className="text-gray-500 text-xs">State</span>
              <p className="font-medium">{current.state}</p>
            </div>
            <div>
              <span className="text-gray-500 text-xs">Dispatch</span>
              <p><StateBadge category={current.dispatch_category} /></p>
            </div>
            <div>
              <span className="text-gray-500 text-xs">OEE Bucket</span>
              <p className="font-medium text-xs">{current.oee_bucket}</p>
            </div>
          </div>

          {current.started_at && (
            <p className="text-xs text-gray-500">
              Since: {new Date(current.started_at).toLocaleString()}
            </p>
          )}

          {/* Optional metadata */}
          <div className="flex gap-3">
            <label className="flex flex-col text-xs font-medium text-gray-600 flex-1">
              Reason Code (optional)
              <input
                className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm"
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
                placeholder="e.g. PM_SCHEDULED"
              />
            </label>
            <label className="flex flex-col text-xs font-medium text-gray-600 flex-1">
              Notes (optional)
              <input
                className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="free text"
              />
            </label>
          </div>

          {/* Valid transitions */}
          <h3 className="text-xs font-semibold text-gray-500 uppercase">Valid Transitions</h3>
          {current.valid_transitions.length === 0 ? (
            <p className="text-sm text-gray-500">No valid transitions from this state.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {current.valid_transitions.map((t) => {
                const targetDef = fullModel?.states.find((s) => s.name === t.to_state);
                return (
                  <button
                    key={`${t.from_state}-${t.to_state}`}
                    className="px-3 py-1.5 rounded border text-sm hover:bg-gray-50 disabled:opacity-50 flex items-center gap-2"
                    onClick={() => doTransition(t)}
                    disabled={busy}
                  >
                    <span className="font-medium">{t.to_state}</span>
                    {t.trigger && (
                      <span className="text-xs text-gray-400">({t.trigger})</span>
                    )}
                    {targetDef && (
                      <StateBadge category={targetDef.dispatch_category} />
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Last result */}
          {lastResult && (
            <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
              {lastResult}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Tiny select helper ─────────────────────────────────────────── */

function Select({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex flex-col text-xs font-medium text-gray-600">
      {label}
      <select
        className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm disabled:opacity-50"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        <option value="">— select —</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
