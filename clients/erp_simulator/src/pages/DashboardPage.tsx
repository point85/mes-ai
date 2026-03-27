import { useState } from "react";
import { getERPHealth, type ERPHealth } from "../api/erp";
import StatusBadge from "../components/StatusBadge";
import { useERPType } from "../hooks/useERPType";

export default function DashboardPage() {
  const [health, setHealth] = useState<ERPHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { erpType, erpLabel } = useERPType();

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      setHealth(await getERPHealth());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Health check failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">ERP Simulator Dashboard</h2>
        <p className="text-sm text-gray-600 mt-1">
          Monitor adapter health and connectivity to the {erpLabel} ERP Simulator plugin.
        </p>
      </div>

      <div className="bg-white rounded-lg border p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-gray-800">Adapter Health</h3>
          <button onClick={checkHealth} disabled={loading} className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
            {loading ? "Checking…" : "Check Health"}
          </button>
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>}

        {health && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <StatusBadge ok={health.inbound.available} />
                <span className="font-medium">Inbound Adapter</span>
              </div>
              <div className="text-sm text-gray-600">
                {health.inbound.available ? "Connected — ERP → MES sync ready" : "Unavailable — no ERP inbound adapter loaded"}
              </div>
              {health.inbound.available && (
                <div className="mt-2 text-sm">
                  Health: <StatusBadge ok={health.inbound.healthy} />
                </div>
              )}
            </div>
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <StatusBadge ok={health.outbound.available} />
                <span className="font-medium">Outbound Adapter</span>
              </div>
              <div className="text-sm text-gray-600">
                {health.outbound.available ? "Connected — MES → ERP reporting ready" : "Unavailable — no ERP outbound adapter loaded"}
              </div>
              {health.outbound.available && (
                <div className="mt-2 text-sm">
                  Health: <StatusBadge ok={health.outbound.healthy} />
                </div>
              )}
            </div>
          </div>
        )}

        {!health && !error && (
          <div className="text-sm text-gray-500">Click "Check Health" to verify adapter connectivity.</div>
        )}
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-medium text-gray-800 mb-3">Quick Reference</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <h4 className="font-medium text-gray-700 mb-1">Inbound (ERP → MES)</h4>
            <ul className="list-disc list-inside space-y-0.5">
              <li>Production Orders</li>
              <li>Materials</li>
              <li>Products</li>
              <li>Bills of Material</li>
              <li>Routings</li>
              <li>Work Centers</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-gray-700 mb-1">Outbound (MES → ERP)</h4>
            <ul className="list-disc list-inside space-y-0.5">
              <li>Production Completion{erpType === "sap" ? " (MIGO 101)" : ""}</li>
              <li>Material Consumption{erpType === "sap" ? " (MIGO 261)" : " (WIP Issue)"}</li>
              <li>Scrap Report{erpType === "sap" ? " (MIGO 531)" : ""}</li>
              <li>Labor{erpType === "sap" ? " (CATS Time)" : " (Resource Charge)"}</li>
              <li>Downtime{erpType === "sap" ? " (PM Notification)" : " (Maintenance Event)"}</li>
              <li>Quality Results{erpType === "sap" ? " (QM Recording)" : " (Inspection Result)"}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
