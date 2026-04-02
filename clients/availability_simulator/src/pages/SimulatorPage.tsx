import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchAllEquipment,
  fetchCurrentState,
  fetchStateModels,
  transitionEquipment,
} from "../api/endpoints";
import StateBadge from "../components/StateBadge";
import type {
  Equipment,
  EquipmentCurrentState,
  StateModel,
} from "../types";

interface SimEquipment {
  equipment: Equipment;
  current: EquipmentCurrentState | null;
  lastTransition: string | null;
  error: string | null;
}

interface LogEntry {
  timestamp: Date;
  equipCode: string;
  fromState: string;
  toState: string;
  dispatch: string;
  success: boolean;
  error?: string;
}

export default function SimulatorPage() {
  const [allEquipment, setAllEquipment] = useState<SimEquipment[]>([]);
  const [, setModels] = useState<StateModel[]>([]);
  const [loadingEquip, setLoadingEquip] = useState(false);
  const [running, setRunning] = useState(false);
  const [intervalSec, setIntervalSec] = useState(5);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [totalTransitions, setTotalTransitions] = useState(0);
  const [totalErrors, setTotalErrors] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Only simulate equipment with state models
  const simulatable = allEquipment.filter((e) => e.equipment.state_model_id);

  // Load all equipment + state models
  async function loadEquipment() {
    setLoadingEquip(true);
    try {
      const [eqs, mods] = await Promise.all([fetchAllEquipment(), fetchStateModels()]);
      setModels(mods);

      // Load current state for each equipment that has a state model
      const simEqs: SimEquipment[] = [];
      for (const eq of eqs) {
        let current: EquipmentCurrentState | null = null;
        let error: string | null = null;
        if (eq.state_model_id) {
          try {
            current = await fetchCurrentState(eq.id);
          } catch (err: unknown) {
            error = err instanceof Error ? err.message : String(err);
          }
        }
        simEqs.push({ equipment: eq, current, lastTransition: null, error });
      }
      setAllEquipment(simEqs);
    } catch {
      // ignore
    } finally {
      setLoadingEquip(false);
    }
  }

  useEffect(() => {
    loadEquipment();
  }, []);

  // Random transition for a single equipment
  const doRandomTransition = useCallback(async (entry: SimEquipment): Promise<LogEntry | null> => {
    if (!entry.current || entry.current.valid_transitions.length === 0) return null;

    const transitions = entry.current.valid_transitions;
    const chosen = transitions[Math.floor(Math.random() * transitions.length)];
    const fromState = entry.current.state;

    try {
      const result = await transitionEquipment(entry.equipment.id, chosen.to_state);
      // Refresh current state
      const updated = await fetchCurrentState(entry.equipment.id);
      entry.current = updated;
      entry.lastTransition = `→ ${result.state} at ${new Date(result.started_at).toLocaleTimeString()}`;
      entry.error = null;
      return {
        timestamp: new Date(),
        equipCode: entry.equipment.code,
        fromState,
        toState: result.state,
        dispatch: result.dispatch_category,
        success: true,
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      entry.error = msg;
      return {
        timestamp: new Date(),
        equipCode: entry.equipment.code,
        fromState,
        toState: chosen.to_state,
        dispatch: "",
        success: false,
        error: msg,
      };
    }
  }, []);

  // Run one simulation tick: pick a random simulatable equipment and transition it
  const tick = useCallback(async () => {
    if (simulatable.length === 0) return;

    const idx = Math.floor(Math.random() * simulatable.length);
    const entry = simulatable[idx];
    const logEntry = await doRandomTransition(entry);

    if (logEntry) {
      setLog((prev) => [logEntry, ...prev].slice(0, 200));
      setTotalTransitions((n) => n + 1);
      if (!logEntry.success) setTotalErrors((n) => n + 1);
      // Force re-render of equipment list
      setAllEquipment((prev) => [...prev]);
    }
  }, [simulatable, doRandomTransition]);

  // Start / stop
  function start() {
    if (simulatable.length === 0) return;
    setRunning(true);
    // Immediately do one tick
    tick();
    timerRef.current = setInterval(tick, intervalSec * 1000);
  }

  function stop() {
    setRunning(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Restart timer when interval changes while running
  useEffect(() => {
    if (running && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = setInterval(tick, intervalSec * 1000);
    }
  }, [intervalSec, running, tick]);

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-white border rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-600 uppercase">Simulation Controls</h2>
        <div className="flex flex-wrap items-center gap-4">
          <label className="text-xs font-medium text-gray-600">
            Interval (seconds):
            <input
              type="number"
              min={1}
              max={60}
              className="ml-2 w-16 rounded border border-gray-300 px-2 py-1 text-sm"
              value={intervalSec}
              onChange={(e) => setIntervalSec(Math.max(1, Number(e.target.value)))}
            />
          </label>

          {!running ? (
            <button
              className="px-4 py-1.5 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700 disabled:opacity-50"
              onClick={start}
              disabled={simulatable.length === 0 || loadingEquip}
            >
              Start Simulation
            </button>
          ) : (
            <button
              className="px-4 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700"
              onClick={stop}
            >
              Stop Simulation
            </button>
          )}

          <button
            className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
            onClick={loadEquipment}
            disabled={loadingEquip || running}
          >
            {loadingEquip ? "Loading…" : "Reload Equipment"}
          </button>

          <button
            className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50"
            onClick={() => { setLog([]); setTotalTransitions(0); setTotalErrors(0); }}
          >
            Clear Log
          </button>
        </div>

        {simulatable.length === 0 && !loadingEquip && (
          <p className="text-sm text-amber-600">
            No equipment with state models found. Create equipment and assign state models first.
          </p>
        )}

        {/* Stats */}
        <div className="flex gap-6 text-sm pt-1">
          <span>Equipment: <strong>{simulatable.length}</strong> / {allEquipment.length}</span>
          <span>Transitions: <strong>{totalTransitions}</strong></span>
          <span>Errors: <strong className={totalErrors > 0 ? "text-red-600" : ""}>{totalErrors}</strong></span>
          {running && (
            <span className="text-emerald-600 animate-pulse font-medium">● Running</span>
          )}
        </div>
      </div>

      {/* Equipment states grid */}
      {simulatable.length > 0 && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-600 uppercase">
            Equipment States ({simulatable.length})
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {simulatable.map(({ equipment: eq, current, lastTransition, error: eqError }) => (
              <div
                key={eq.id}
                className={`border rounded-lg p-3 space-y-1 text-sm ${
                  eqError ? "border-red-300 bg-red-50" : "hover:bg-gray-50"
                }`}
              >
                <div className="font-semibold">{eq.code}</div>
                <div className="text-xs text-gray-500">{eq.name}</div>
                {current ? (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">State:</span>
                      <span className="font-medium">{current.state}</span>
                    </div>
                    <StateBadge category={current.dispatch_category} />
                    <div className="text-xs text-gray-400">{current.oee_bucket}</div>
                  </>
                ) : (
                  <div className="text-xs text-gray-400">No state data</div>
                )}
                {lastTransition && (
                  <div className="text-xs text-emerald-600">{lastTransition}</div>
                )}
                {eqError && (
                  <div className="text-xs text-red-600 truncate" title={eqError}>
                    Error: {eqError}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transition log */}
      <div className="bg-white border rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-600 uppercase">
          Transition Log ({log.length})
        </h2>
        {log.length === 0 ? (
          <p className="text-sm text-gray-500">No transitions yet. Start the simulation.</p>
        ) : (
          <div className="overflow-x-auto max-h-80 overflow-y-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                  <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">Equipment</th>
                  <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">From</th>
                  <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">To</th>
                  <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">Dispatch</th>
                  <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {log.map((entry, i) => (
                  <tr key={i} className={entry.success ? "" : "bg-red-50"}>
                    <td className="px-2 py-1 text-xs text-gray-500">
                      {entry.timestamp.toLocaleTimeString()}
                    </td>
                    <td className="px-2 py-1 font-medium">{entry.equipCode}</td>
                    <td className="px-2 py-1">{entry.fromState}</td>
                    <td className="px-2 py-1">{entry.toState}</td>
                    <td className="px-2 py-1">
                      {entry.dispatch ? <StateBadge category={entry.dispatch} /> : "—"}
                    </td>
                    <td className="px-2 py-1">
                      {entry.success ? (
                        <span className="text-green-600 text-xs font-medium">OK</span>
                      ) : (
                        <span className="text-red-600 text-xs" title={entry.error}>FAIL</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
