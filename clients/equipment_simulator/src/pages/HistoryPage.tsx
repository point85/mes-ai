import { useEffect, useState } from "react";
import { fetchStateHistory } from "../api/endpoints";
import { useEquipmentContext } from "../App";
import DataTable, { type Column } from "../components/DataTable";
import StateBadge from "../components/StateBadge";
import type { EquipmentStateLog } from "../types";

export default function HistoryPage() {
  const { equipmentId, equipmentCode } = useEquipmentContext();

  const [logs, setLogs] = useState<EquipmentStateLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limit, setLimit] = useState(50);

  // Load history whenever equipment context changes
  useEffect(() => {
    setLogs([]);
    setError(null);
    if (!equipmentId) return;
    loadHistory(equipmentId, limit);
  }, [equipmentId]); // eslint-disable-line react-hooks/exhaustive-deps

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
      {/* No equipment selected */}
      {!equipmentId ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <p className="text-sm">Select equipment from the tree to view state history.</p>
        </div>
      ) : (
        <>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-sm">
            Showing history for <strong>{equipmentCode}</strong>
            <span className="ml-2 text-xs text-gray-500 font-mono">({equipmentId})</span>
          </div>

          {/* Limit control + refresh */}
          <div className="flex items-center gap-3">
            <label className="text-xs text-gray-600">
              Max rows:
              <select
                className="ml-1 rounded border border-gray-300 bg-white px-2 py-1 text-sm"
                value={limit}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setLimit(n);
                  loadHistory(equipmentId, n);
                }}
              >
                {[25, 50, 100, 200].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </label>
            <button
              className="px-3 py-1 bg-emerald-600 text-white text-xs rounded hover:bg-emerald-700 disabled:opacity-50"
              onClick={() => loadHistory(equipmentId, limit)}
              disabled={loading}
            >
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
              {error}
            </div>
          )}

          <DataTable columns={columns} data={logs} emptyMessage="No state history" />

          {logs.length > 0 && (
            <p className="text-xs text-gray-500">Showing {logs.length} entries (newest first)</p>
          )}
        </>
      )}
    </div>
  );
}
