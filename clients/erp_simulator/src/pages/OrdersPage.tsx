import { useState } from "react";
import { syncProductionOrders, type ProductionOrder } from "../api/erp";
import DataTable, { type Column } from "../components/DataTable";

const columns: Column<ProductionOrder>[] = [
  { key: "erp_reference", header: "SAP Order #" },
  { key: "product_code", header: "Product" },
  { key: "quantity_ordered", header: "Qty" },
  { key: "uom", header: "UoM" },
  { key: "priority", header: "Priority" },
  {
    key: "planned_start",
    header: "Planned Start",
    render: (r: ProductionOrder) =>
      r.planned_start ? new Date(r.planned_start).toLocaleDateString() : "—",
  },
  { key: "bom_id", header: "BOM ID" },
  { key: "routing_id", header: "Routing ID" },
  {
    key: "sap_order_type",
    header: "Order Type",
    render: (r: ProductionOrder) => String(r.metadata?.sap_order_type ?? ""),
  },
];

export default function OrdersPage() {
  const [data, setData] = useState<ProductionOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSync = async () => {
    setLoading(true);
    setError(null);
    try {
      const orders = await syncProductionOrders();
      setData(orders);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sync failed";
      setError(msg);
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
          {loading ? "Syncing…" : "Sync Production Orders"}
        </button>
        {data.length > 0 && (
          <span className="text-sm text-gray-500">{data.length} orders received</span>
        )}
      </div>
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
          {error}
        </div>
      )}
      <DataTable
        columns={columns}
        data={data}
        keyField="erp_reference"
        emptyMessage="Click 'Sync Production Orders' to pull data from SAP"
      />
    </div>
  );
}
