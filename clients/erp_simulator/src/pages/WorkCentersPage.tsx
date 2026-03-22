import { useState } from "react";
import { syncWorkCenters, type WorkCenter } from "../api/erp";
import DataTable, { type Column } from "../components/DataTable";

const columns: Column<WorkCenter>[] = [
  { key: "code", header: "Code" },
  { key: "name", header: "Name" },
  { key: "area_code", header: "Area" },
  {
    key: "sap_category",
    header: "SAP Category",
    render: (r: WorkCenter) => String(r.capabilities?.sap_category ?? ""),
  },
];

export default function WorkCentersPage() {
  const [data, setData] = useState<WorkCenter[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSync = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await syncWorkCenters());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={handleSync}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Syncing…" : "Sync Work Centers"}
        </button>
        {data.length > 0 && (
          <span className="text-sm text-gray-500">{data.length} work centers received</span>
        )}
      </div>
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
      )}
      <DataTable
        columns={columns}
        data={data}
        keyField="code"
        emptyMessage="Click 'Sync Work Centers' to pull work center definitions from SAP"
      />
    </div>
  );
}
