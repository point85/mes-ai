import { useState } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { fetchUnitBySerial, fetchLotByNumber, fetchUnitStepContext, fetchLotStepContext } from "../api/runtime";
import type { StepContext } from "../types";
import StepProcessingPanel from "../components/StepProcessingPanel";

export default function ScanPage() {
  const [scanInput, setScanInput] = useState("");
  const [scanType, setScanType] = useState<"unit" | "lot">("unit");
  const [context, setContext] = useState<StepContext | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleScan = async () => {
    const value = scanInput.trim();
    if (!value) return;
    setLoading(true);
    setError(null);
    setContext(null);

    try {
      if (scanType === "unit") {
        const unit = await fetchUnitBySerial(value);
        const ctx = await fetchUnitStepContext(unit.id);
        setContext(ctx);
      } else {
        const lot = await fetchLotByNumber(value);
        const ctx = await fetchLotStepContext(lot.id);
        setContext(ctx);
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
        ?? "Not found";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleScan();
  };

  const resetScan = () => {
    setContext(null);
    setError(null);
    setScanInput("");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Scan WIP</h2>
        {context && (
          <button onClick={resetScan} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
            <ArrowPathIcon className="h-4 w-4" /> New Scan
          </button>
        )}
      </div>

      {/* Scan bar */}
      <div className="bg-white rounded-lg shadow p-5">
        <div className="flex items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Type</label>
            <select
              value={scanType}
              onChange={(e) => setScanType(e.target.value as "unit" | "lot")}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="unit">Unit (Serial #)</option>
              <option value="lot">Lot (Lot #)</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-600 mb-1">
              {scanType === "unit" ? "Serial Number" : "Lot Number"}
            </label>
            <input
              type="text"
              value={scanInput}
              onChange={(e) => setScanInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={scanType === "unit" ? "Scan or type serial number…" : "Scan or type lot number…"}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              autoFocus
            />
          </div>
          <button
            onClick={handleScan}
            disabled={loading}
            className="bg-indigo-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </div>

        {error && (
          <div className="mt-3 p-3 bg-red-50 text-red-700 text-sm rounded-md">{error}</div>
        )}
      </div>

      {/* Step Processing Panel */}
      {context && (
        <StepProcessingPanel
          context={context}
          onRefresh={async () => {
            // Re-fetch context after action
            try {
              if (context.wip_type === "unit") {
                const ctx = await fetchUnitStepContext(context.wip.id);
                setContext(ctx);
              } else {
                const ctx = await fetchLotStepContext(context.wip.id);
                setContext(ctx);
              }
            } catch {
              // ignore
            }
          }}
        />
      )}
    </div>
  );
}
