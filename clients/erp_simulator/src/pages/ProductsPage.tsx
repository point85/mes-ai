import { useState } from "react";
import { syncProducts, type ProductDefinition } from "../api/erp";
import DataTable, { type Column } from "../components/DataTable";

const columns: Column<ProductDefinition>[] = [
  { key: "code", header: "Product Code" },
  { key: "name", header: "Name" },
  { key: "product_type", header: "Type" },
  { key: "version", header: "Version" },
  { key: "description", header: "Description" },
];

export default function ProductsPage() {
  const [data, setData] = useState<ProductDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSync = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await syncProducts());
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
          {loading ? "Syncing…" : "Sync Products"}
        </button>
        {data.length > 0 && (
          <span className="text-sm text-gray-500">{data.length} products received</span>
        )}
      </div>
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
      )}
      <DataTable
        columns={columns}
        data={data}
        keyField="code"
        emptyMessage="Click 'Sync Products' to pull product definitions from SAP"
      />
    </div>
  );
}
