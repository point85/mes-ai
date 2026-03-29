import { useState } from "react";
import { fetchStateHistory } from "../api/endpoints";
import DataTable, { type Column } from "../components/DataTable";
import StateBadge from "../components/StateBadge";
import type { EquipmentStateLog } from "../types";

export default function HistoryPage() {
  const [equipId, setEquipId] = useState("");
  const [logs, setLogs] = useState<EquipmentStateLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadHistory() {
    if (!equipId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStateHistory(equipId.trim());
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
  ];

  return (
    <div className="space-y-4 max-w-5xl">
      {/* Equipment selector */}
      <div className="flex gap-2 items-end">
        <label className="flex flex-col text-xs font-medium text-gray-600 flex-1 max-w-md">
          Equipment ID (UUID)
          <input
            className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm font-mono"
            value={equipId}
            onChange={(e) => setEquipId(e.target.value)}
            placeholder="paste equipment UUID"
          />
        </label>
        <button
          className="px-3 py-1.5 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700 disabled:opacity-50"
          onClick={loadHistory}
          disabled={!equipId.trim() || loading}
        >
          {loading ? "Loading…" : "Load History"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      <DataTable columns={columns} data={logs} emptyMessage="No state history" />

      {logs.length > 0 && (
        <p className="text-xs text-gray-500">Showing latest {logs.length} entries</p>
      )}
    </div>
  );
}
