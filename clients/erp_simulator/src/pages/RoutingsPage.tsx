import { useState } from "react";
import { syncRoutings, type ProcessRoute } from "../api/erp";

const PRODUCT_IDS = ["FG-WIDGET-100", "FG-WIDGET-200", "FG-GADGET-300"];

export default function RoutingsPage() {
  const [selectedProduct, setSelectedProduct] = useState(PRODUCT_IDS[0]);
  const [data, setData] = useState<ProcessRoute[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSync = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await syncRoutings(selectedProduct));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <select
          value={selectedProduct}
          onChange={(e) => setSelectedProduct(e.target.value)}
          className="border rounded px-3 py-2 text-sm"
        >
          {PRODUCT_IDS.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        <button
          onClick={handleSync}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Syncing…" : "Sync Routings"}
        </button>
      </div>
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
      )}
      {data.map((route, idx) => (
        <div key={idx} className="bg-white rounded-lg border p-4 space-y-3">
          <div className="flex gap-4 text-sm">
            <span>
              <strong>Product:</strong> {route.product_code}
            </span>
            <span>
              <strong>Routing:</strong> {route.name}
            </span>
            <span>
              <strong>Version:</strong> {route.version}
            </span>
          </div>
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Seq</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Operation</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Work Center</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {route.steps.map((step, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2">{step.sequence}</td>
                  <td className="px-3 py-2">{step.name}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        step.step_type === "inspection"
                          ? "bg-yellow-100 text-yellow-800"
                          : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {step.step_type}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono">{step.work_center_code ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {data.length === 0 && !loading && (
        <div className="text-center py-8 text-gray-500 bg-white rounded-lg border">
          Select a product and click 'Sync Routings'
        </div>
      )}
    </div>
  );
}
