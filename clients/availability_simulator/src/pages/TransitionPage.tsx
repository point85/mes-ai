import { useEffect, useState } from "react";
import {
  fetchCurrentState,
  fetchStateModels,
  transitionEquipment,
} from "../api/endpoints";
import StateBadge from "../components/StateBadge";
import type { EquipmentCurrentState, StateModel, TransitionDefinition } from "../types";

export default function TransitionPage() {
  const [equipId, setEquipId] = useState("");
  const [current, setCurrent] = useState<EquipmentCurrentState | null>(null);
  const [models, setModels] = useState<StateModel[]>([]);
  const [reasonCode, setReasonCode] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  // Fetch state model list once
  useEffect(() => {
    fetchStateModels().then(setModels).catch(() => {});
  }, []);

  async function loadState() {
    if (!equipId.trim()) return;
    setError(null);
    setCurrent(null);
    try {
      const st = await fetchCurrentState(equipId.trim());
      setCurrent(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Failed to load state: ${msg}`);
    }
  }

  async function doTransition(t: TransitionDefinition) {
    if (!equipId.trim()) return;
    setBusy(true);
    setError(null);
    setLastResult(null);
    try {
      const log = await transitionEquipment(
        equipId.trim(),
        t.to_state,
        reasonCode || undefined,
        notes || undefined,
      );
      setLastResult(
        `Transitioned to "${log.state}" at ${new Date(log.started_at).toLocaleTimeString()}`,
      );
      // Refresh current state
      const st = await fetchCurrentState(equipId.trim());
      setCurrent(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Transition failed: ${msg}`);
    } finally {
      setBusy(false);
    }
  }

  // Find full state model for extra display info
  const fullModel = models.find((m) => m.model_id === current?.state_model);

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Equipment ID input */}
      <div className="bg-white rounded-lg border p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-600 uppercase">Select Equipment</h2>
        <div className="flex gap-2 items-end">
          <label className="flex flex-col text-xs font-medium text-gray-600 flex-1">
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
            onClick={loadState}
            disabled={!equipId.trim()}
          >
            Load State
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Current state display */}
      {current && (
        <div className="bg-white rounded-lg border p-4 space-y-4">
          <h2 className="text-sm font-semibold text-gray-600 uppercase">Current State</h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500 text-xs">State Model</span>
              <p className="font-medium">{current.state_model}</p>
            </div>
            <div>
              <span className="text-gray-500 text-xs">State</span>
              <p className="font-medium">{current.state}</p>
            </div>
            <div>
              <span className="text-gray-500 text-xs">Dispatch</span>
              <p><StateBadge category={current.dispatch_category} /></p>
            </div>
            <div>
              <span className="text-gray-500 text-xs">OEE Bucket</span>
              <p className="font-medium text-xs">{current.oee_bucket}</p>
            </div>
          </div>

          {current.started_at && (
            <p className="text-xs text-gray-500">
              Since: {new Date(current.started_at).toLocaleString()}
            </p>
          )}

          {/* Optional metadata fields */}
          <div className="flex gap-3">
            <label className="flex flex-col text-xs font-medium text-gray-600 flex-1">
              Reason Code (optional)
              <input
                className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm"
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
                placeholder="e.g. PM_SCHEDULED"
              />
            </label>
            <label className="flex flex-col text-xs font-medium text-gray-600 flex-1">
              Notes (optional)
              <input
                className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="free text"
              />
            </label>
          </div>

          {/* Valid transitions */}
          <h3 className="text-xs font-semibold text-gray-500 uppercase">Valid Transitions</h3>
          {current.valid_transitions.length === 0 ? (
            <p className="text-sm text-gray-500">No valid transitions from this state.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {current.valid_transitions.map((t) => {
                const targetDef = fullModel?.states.find((s) => s.name === t.to_state);
                return (
                  <button
                    key={`${t.from_state}-${t.to_state}`}
                    className="px-3 py-1.5 rounded border text-sm hover:bg-gray-50 disabled:opacity-50 flex items-center gap-2"
                    onClick={() => doTransition(t)}
                    disabled={busy}
                  >
                    <span className="font-medium">{t.to_state}</span>
                    {t.trigger && (
                      <span className="text-xs text-gray-400">({t.trigger})</span>
                    )}
                    {targetDef && (
                      <StateBadge category={targetDef.dispatch_category} />
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Last result */}
          {lastResult && (
            <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
              {lastResult}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
