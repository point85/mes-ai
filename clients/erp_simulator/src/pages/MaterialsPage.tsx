import { useState } from "react";
import { syncMaterials, type MaterialDefinition } from "../api/erp";
import DataTable, { type Column } from "../components/DataTable";

const columns: Column<MaterialDefinition>[] = [
  { key: "code", header: "Material Code" },
  { key: "name", header: "Name" },
  { key: "material_type", header: "Type" },
  { key: "uom", header: "UoM" },
  { key: "description", header: "Description" },
  {
    key: "shelf_life_days",
    header: "Shelf Life (days)",
    render: (r: MaterialDefinition) => (r.shelf_life_days != null ? String(r.shelf_life_days) : "—"),
  },
  {
    key: "sap_material_type",
    header: "SAP Type",
    render: (r: MaterialDefinition) => String(r.metadata?.sap_material_type ?? ""),
  },
];

export default function MaterialsPage() {
  const [data, setData] = useState<MaterialDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSync = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await syncMaterials());
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
          {loading ? "Syncing…" : "Sync Materials"}
        </button>
        {data.length > 0 && (
          <span className="text-sm text-gray-500">{data.length} materials received</span>
        )}
      </div>
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
      )}
      <DataTable
        columns={columns}
        data={data}
        keyField="code"
        emptyMessage="Click 'Sync Materials' to pull material master from SAP"
      />
    </div>
  );
}
