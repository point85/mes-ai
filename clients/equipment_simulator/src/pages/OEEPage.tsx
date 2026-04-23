import { useEffect, useState } from "react";
import { fetchOEE } from "../api/endpoints";
import { useEquipmentContext } from "../App";
import type { OEEResult } from "../types";

function toLocalDateTimeInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function OEEPage() {
  const { equipmentId, equipmentCode, equipmentName } = useEquipmentContext();

  // Period
  const now = new Date();
  const shiftStart = new Date(now);
  shiftStart.setHours(now.getHours() - 8, 0, 0, 0);
  const [periodStart, setPeriodStart] = useState(toLocalDateTimeInput(shiftStart));
  const [periodEnd, setPeriodEnd] = useState(toLocalDateTimeInput(now));

  // Result
  const [result, setResult] = useState<OEEResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clear result when equipment changes
  useEffect(() => {
    setResult(null);
    setError(null);
  }, [equipmentId]);

  async function calculate() {
    if (!equipmentId || !periodStart || !periodEnd) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const startISO = new Date(periodStart).toISOString();
      const endISO = new Date(periodEnd).toISOString();
      const r = await fetchOEE(equipmentId, startISO, endISO);
      setResult(r);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`OEE calculation failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  }

  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

  const gaugeColor = (v: number) => {
    if (v >= 0.85) return "bg-green-500";
    if (v >= 0.6) return "bg-yellow-500";
    return "bg-red-500";
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* No equipment selected */}
      {!equipmentId ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <p className="text-sm">Select equipment from the tree to calculate OEE.</p>
        </div>
      ) : (
        <>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-sm">
            Equipment: <strong>{equipmentCode}</strong>
            {equipmentName && (
              <span className="ml-2 text-xs text-gray-600">— {equipmentName}</span>
            )}
          </div>

          {/* Period selection + calculate */}
          <div className="bg-white border rounded-lg p-4 space-y-3">
            <h2 className="text-sm font-semibold text-gray-600 uppercase">Time Period</h2>
            <div className="flex flex-wrap gap-4 items-end">
              <label className="flex flex-col text-xs font-medium text-gray-600">
                Start
                <input
                  type="datetime-local"
                  className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                />
              </label>
              <label className="flex flex-col text-xs font-medium text-gray-600">
                End
                <input
                  type="datetime-local"
                  className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                />
              </label>
              <button
                className="px-4 py-1.5 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700 disabled:opacity-50"
                onClick={calculate}
                disabled={loading}
              >
                {loading ? "Calculating…" : "Calculate OEE"}
              </button>
            </div>
          </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {/* OEE Result */}
      {result && (
        <div className="space-y-4">
          {/* Gauge cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <GaugeCard label="OEE" value={result.oee} color={gaugeColor(result.oee)} pct={pct} />
            <GaugeCard label="Availability" value={result.availability} color={gaugeColor(result.availability)} pct={pct} />
            <GaugeCard label="Performance" value={result.performance} color={gaugeColor(result.performance)} pct={pct} />
            <GaugeCard label="Quality" value={result.quality} color={gaugeColor(result.quality)} pct={pct} />
          </div>

          {/* Details */}
          {result.details && Object.keys(result.details).length > 0 && (
            <div className="bg-white border rounded-lg p-4 space-y-2">
              <h3 className="text-sm font-semibold text-gray-600 uppercase">Details</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                {Object.entries(result.details).map(([key, val]) => (
                  <div key={key}>
                    <span className="text-gray-500 text-xs">{key.replace(/_/g, " ")}</span>
                    <p className="font-medium">{typeof val === "number" ? val.toFixed(2) : String(val)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Six Big Losses */}
          {result.six_big_losses && Object.keys(result.six_big_losses).length > 0 && (
            <div className="bg-white border rounded-lg p-4 space-y-2">
              <h3 className="text-sm font-semibold text-gray-600 uppercase">Six Big Losses</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                {Object.entries(result.six_big_losses).map(([key, val]) => (
                  <div key={key}>
                    <span className="text-gray-500 text-xs">{key.replace(/_/g, " ")}</span>
                    <p className="font-medium">{typeof val === "number" ? val.toFixed(2) : String(val)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
        </>
      )}
    </div>
  );
}

/* ── Gauge Card ──────────────────────────────────────────────────── */

function GaugeCard({
  label, value, color, pct,
}: {
  label: string;
  value: number;
  color: string;
  pct: (v: number) => string;
}) {
  const widthPct = Math.min(value * 100, 100);
  return (
    <div className="bg-white border rounded-lg p-4 space-y-2">
      <div className="text-xs font-semibold text-gray-500 uppercase">{label}</div>
      <div className="text-2xl font-bold">{pct(value)}</div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${widthPct}%` }} />
      </div>
    </div>
  );
}


