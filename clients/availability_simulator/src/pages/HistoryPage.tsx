import { useEffect, useState } from "react";
import {
  fetchSites,
  fetchAreas,
  fetchLines,
  fetchWorkCells,
  fetchEquipmentInWorkCell,
  fetchStateHistory,
} from "../api/endpoints";
import { useEquipmentContext } from "../App";
import DataTable, { type Column } from "../components/DataTable";
import StateBadge from "../components/StateBadge";
import type {
  Site,
  Area,
  ProductionLine,
  WorkCell,
  Equipment,
  EquipmentStateLog,
} from "../types";

export default function HistoryPage() {
  const { equipmentId, equipmentCode } = useEquipmentContext();

  // Hierarchy drill-down state
  const [sites, setSites] = useState<Site[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [lines, setLines] = useState<ProductionLine[]>([]);
  const [workCells, setWorkCells] = useState<WorkCell[]>([]);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [siteId, setSiteId] = useState("");
  const [areaId, setAreaId] = useState("");
  const [lineId, setLineId] = useState("");
  const [wcId, setWcId] = useState("");
  const [selectedEquipId, setSelectedEquipId] = useState("");
  const [, setSelectedEquipCode] = useState("");

  const [logs, setLogs] = useState<EquipmentStateLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limit, setLimit] = useState(50);

  // Load sites on mount
  useEffect(() => {
    fetchSites().then(setSites).catch(() => {});
  }, []);

  // If equipment context is set, auto-load history
  useEffect(() => {
    if (equipmentId) {
      setSelectedEquipId(equipmentId);
      setSelectedEquipCode(equipmentCode ?? equipmentId);
      loadHistory(equipmentId, limit);
    }
  }, [equipmentId, equipmentCode]); // eslint-disable-line react-hooks/exhaustive-deps

  // Hierarchy cascades
  useEffect(() => {
    setAreas([]); setLines([]); setWorkCells([]); setEquipment([]);
    if (!siteId) return;
    fetchAreas(siteId).then(setAreas).catch(() => {});
  }, [siteId]);

  useEffect(() => {
    setLines([]); setWorkCells([]); setEquipment([]);
    if (!areaId) return;
    fetchLines(areaId).then(setLines).catch(() => {});
  }, [areaId]);

  useEffect(() => {
    setWorkCells([]); setEquipment([]);
    if (!lineId) return;
    fetchWorkCells(lineId).then(setWorkCells).catch(() => {});
  }, [lineId]);

  useEffect(() => {
    setEquipment([]);
    if (!wcId) return;
    fetchEquipmentInWorkCell(wcId).then(setEquipment).catch(() => {});
  }, [wcId]);

  async function loadHistory(equipId: string, maxRows: number) {
    if (!equipId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStateHistory(equipId, maxRows);
      setLogs(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Failed to load history: ${msg}`);
    } finally {
      setLoading(false);
    }
  }

  function onEquipmentSelect(eqId: string) {
    const eq = equipment.find((e) => e.id === eqId);
    setSelectedEquipId(eqId);
    setSelectedEquipCode(eq?.code ?? eqId);
    if (eqId) loadHistory(eqId, limit);
    else setLogs([]);
  }

  const columns: Column<EquipmentStateLog>[] = [
    { key: "state", header: "State", render: (r) => <span className="font-medium">{r.state}</span> },
    { key: "state_model", header: "Model" },
    {
      key: "dispatch_category",
      header: "Dispatch",
      render: (r) => <StateBadge category={r.dispatch_category} />,
    },
    { key: "oee_bucket", header: "OEE Bucket" },
    { key: "reason_code", header: "Reason", render: (r) => r.reason_code ?? "—" },
    { key: "notes", header: "Notes", render: (r) => r.notes ?? "—" },
    {
      key: "started_at",
      header: "Started",
      render: (r) => new Date(r.started_at).toLocaleString(),
    },
    {
      key: "ended_at",
      header: "Ended",
      render: (r) =>
        r.ended_at ? new Date(r.ended_at).toLocaleString() : <span className="text-green-600 font-medium">active</span>,
    },
    {
      key: "duration",
      header: "Duration",
      render: (r) => {
        const end = r.ended_at ? new Date(r.ended_at) : new Date();
        const start = new Date(r.started_at);
        const secs = Math.round((end.getTime() - start.getTime()) / 1000);
        if (secs < 60) return `${secs}s`;
        if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`;
        return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
      },
    },
  ];

  return (
    <div className="space-y-4 max-w-6xl">
      {/* Equipment selector: hierarchy or context */}
      {equipmentId ? (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-sm">
          Showing history for <strong>{equipmentCode}</strong>
          <span className="ml-2 text-xs text-gray-500 font-mono">({equipmentId})</span>
        </div>
      ) : (
        <div className="flex flex-wrap gap-3 items-end">
          <HierarchySelect label="Site" value={siteId} options={sites.map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` }))} onChange={(v) => { setSiteId(v); setAreaId(""); setLineId(""); setWcId(""); }} />
          <HierarchySelect label="Area" value={areaId} options={areas.map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }))} onChange={(v) => { setAreaId(v); setLineId(""); setWcId(""); }} disabled={!siteId} />
          <HierarchySelect label="Line" value={lineId} options={lines.map((l) => ({ value: l.id, label: `${l.code} — ${l.name}` }))} onChange={(v) => { setLineId(v); setWcId(""); }} disabled={!areaId} />
          <HierarchySelect label="Work Cell" value={wcId} options={workCells.map((wc) => ({ value: wc.id, label: `${wc.code} — ${wc.name}` }))} onChange={(v) => setWcId(v)} disabled={!lineId} />
          <HierarchySelect label="Equipment" value={selectedEquipId} options={equipment.map((e) => ({ value: e.id, label: `${e.code} — ${e.name}` }))} onChange={onEquipmentSelect} disabled={!wcId} />
        </div>
      )}

      {/* Limit control + refresh */}
      {selectedEquipId && (
        <div className="flex items-center gap-3">
          <label className="text-xs text-gray-600">
            Max rows:
            <select
              className="ml-1 rounded border border-gray-300 bg-white px-2 py-1 text-sm"
              value={limit}
              onChange={(e) => {
                const n = Number(e.target.value);
                setLimit(n);
                loadHistory(selectedEquipId, n);
              }}
            >
              {[25, 50, 100, 200].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
          <button
            className="px-3 py-1 bg-emerald-600 text-white text-xs rounded hover:bg-emerald-700 disabled:opacity-50"
            onClick={() => loadHistory(selectedEquipId, limit)}
            disabled={loading}
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      <DataTable columns={columns} data={logs} emptyMessage={selectedEquipId ? "No state history" : "Select equipment above"} />

      {logs.length > 0 && (
        <p className="text-xs text-gray-500">Showing {logs.length} entries (newest first)</p>
      )}
    </div>
  );
}

/* ── Mini select helper ──────────────────────────────────────────── */

function HierarchySelect({
  label, value, options, onChange, disabled,
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
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}
