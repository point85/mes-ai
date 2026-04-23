import { useEffect, useState } from "react";
import {
  fetchCurrentState,
  fetchStateModels,
  fetchReasons,
  transitionEquipment,
  simulateOpcuaState,
  simulateMqttState,
  simulateHistorianState,
  simulateHistorianCounts,
  fetchHistorianMapping,
  simulateMqttCounts,
  incrementCounter,
  fetchCounters,
  fetchEquipmentMaterials,
  fetchMaterialSetup,
  setMaterialSetup,
  clearMaterialSetup,
  simulateOpcuaMaterialSetup,
  simulateMqttMaterialSetup,
  simulateHistorianMaterialSetup,
} from "../api/endpoints";
import { useEquipmentContext } from "../App";
import StateBadge from "../components/StateBadge";
import type {
  EquipmentCurrentState,
  EquipmentMaterialSetup,
  MaterialSetupRead,
  StateModel,
  TransitionDefinition,
  Reason,
  ProductionCounterRead,
} from "../types";

export default function EquipmentPage() {
  const { equipmentId, equipmentCode, equipmentName, setEquipment, navigateTo } = useEquipmentContext();
  // Derive a selection object from context for use in handlers / JSX
  const selectedEquip = equipmentId
    ? { id: equipmentId, code: equipmentCode ?? "", name: equipmentName ?? "" }
    : null;

  // Transition control state
  const [current, setCurrent] = useState<EquipmentCurrentState | null>(null);
  const [models, setModels] = useState<StateModel[]>([]);
  const [reasonCode, setReasonCode] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [reasons, setReasons] = useState<Reason[]>([]);

  // OPC-UA simulation state
  const [opcuaValue, setOpcuaValue] = useState<number>(4); // default Idle
  const [opcuaTag, setOpcuaTag] = useState("ns=2;s=Equipment1/CurrentState");
  const [opcuaBusy, setOpcuaBusy] = useState(false);
  const [opcuaResult, setOpcuaResult] = useState<string | null>(null);
  const [opcuaError, setOpcuaError] = useState<string | null>(null);

  // MQTT simulation state
  const [mqttState, setMqttState] = useState<number>(4); // default Idle
  const [mqttTopic, setMqttTopic] = useState("mes/equipment/{equipment_id}/state");
  const [mqttReason, setMqttReason] = useState("");
  const [mqttBusy, setMqttBusy] = useState(false);
  const [mqttResult, setMqttResult] = useState<string | null>(null);
  const [mqttError, setMqttError] = useState<string | null>(null);

  // Production counts simulation state
  const [goodDelta, setGoodDelta] = useState(1);
  const [rejectDelta, setRejectDelta] = useState(0);
  const [reworkDelta, setReworkDelta] = useState(0);
  const [counterBusy, setCounterBusy] = useState(false);
  const [counterResult, setCounterResult] = useState<string | null>(null);
  const [counterError, setCounterError] = useState<string | null>(null);
  const [todayCounter, setTodayCounter] = useState<ProductionCounterRead | null>(null);

  // MQTT production counts simulation state
  const [mqttCountTopic, setMqttCountTopic] = useState("mes/equipment/{equipment_id}/counts");
  const [mqttProcessed, setMqttProcessed] = useState(1);
  const [mqttDefective, setMqttDefective] = useState(0);
  const [mqttRework, setMqttRework] = useState(0);
  const [mqttCountBusy, setMqttCountBusy] = useState(false);
  const [mqttCountResult, setMqttCountResult] = useState<string | null>(null);
  const [mqttCountError, setMqttCountError] = useState<string | null>(null);

  // Historian production counts simulation state
  const [histCountTagFqn, setHistCountTagFqn] = useState("Simulated.CountTag");
  const [histCountProcessed, setHistCountProcessed] = useState(1);
  const [histCountDefective, setHistCountDefective] = useState(0);
  const [histCountRework, setHistCountRework] = useState(0);
  const [histCountBusy, setHistCountBusy] = useState(false);
  const [histCountResult, setHistCountResult] = useState<string | null>(null);
  const [histCountError, setHistCountError] = useState<string | null>(null);

  // Simulation tab
  const [simTab, setSimTab] = useState<"availability" | "production" | "material_setup">("availability");

  // Material setup state
  const [materialSetup, setMaterialSetup_] = useState<MaterialSetupRead | null>(null);
  const [configuredMaterials, setConfiguredMaterials] = useState<EquipmentMaterialSetup[]>([]);
  const [selectedEmId, setSelectedEmId] = useState("");
  const [jobNumber, setJobNumber] = useState("");
  const [setupBusy, setSetupBusy] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  // OPC-UA material-setup simulation
  const [opcuaSetupTag, setOpcuaSetupTag] = useState("ns=2;s=Equipment1/MaterialSetup");
  const [opcuaSetupCode, setOpcuaSetupCode] = useState("");
  const [opcuaSetupJob, setOpcuaSetupJob] = useState("");
  const [opcuaSetupBusy, setOpcuaSetupBusy] = useState(false);
  const [opcuaSetupResult, setOpcuaSetupResult] = useState<string | null>(null);
  const [opcuaSetupError, setOpcuaSetupError] = useState<string | null>(null);

  // MQTT material-setup simulation
  const [mqttSetupTopic, setMqttSetupTopic] = useState("mes/equipment/{equipment_id}/material-setup");
  const [mqttSetupCode, setMqttSetupCode] = useState("");
  const [mqttSetupJob, setMqttSetupJob] = useState("");
  const [mqttSetupBusy, setMqttSetupBusy] = useState(false);
  const [mqttSetupResult, setMqttSetupResult] = useState<string | null>(null);
  const [mqttSetupError, setMqttSetupError] = useState<string | null>(null);

  // Historian material-setup simulation
  const [histSetupTagFqn, setHistSetupTagFqn] = useState("Simulated.MaterialSetupTag");
  const [histSetupCode, setHistSetupCode] = useState("");
  const [histSetupJob, setHistSetupJob] = useState("");
  const [histSetupBusy, setHistSetupBusy] = useState(false);
  const [histSetupResult, setHistSetupResult] = useState<string | null>(null);
  const [histSetupError, setHistSetupError] = useState<string | null>(null);

  // Historian simulation state
  const [histTagFqn, setHistTagFqn] = useState("Simulated.StateTag");
  const [histState, setHistState] = useState("");
  const [histBusy, setHistBusy] = useState(false);
  const [histResult, setHistResult] = useState<string | null>(null);
  const [histError, setHistError] = useState<string | null>(null);

  // Load state models + reasons on mount
  useEffect(() => {
    fetchStateModels().then(setModels).catch(() => {});
    fetchReasons().then(setReasons).catch(() => {});
  }, []);

  // Load equipment state whenever the context equipmentId changes
  useEffect(() => {
    setCurrent(null);
    setError(null);
    setLastResult(null);
    setReasonCode("");
    setNotes("");
    setTodayCounter(null);
    setCounterResult(null);
    setCounterError(null);
    setMaterialSetup_(null);
    setConfiguredMaterials([]);
    setSelectedEmId("");
    setJobNumber("");
    setSetupError(null);

    if (!equipmentId) return;

    let cancelled = false;
    (async () => {
      try {
        const st = await fetchCurrentState(equipmentId);
        if (!cancelled) setCurrent(st);
      } catch (err: unknown) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : String(err);
          setError(`Failed to load state: ${msg}`);
        }
      }
      // Load today's production counter
      try {
        const counters = await fetchCounters(equipmentId);
        if (!cancelled) {
          const today = new Date().toISOString().slice(0, 10);
          const match = counters.find((c) => c.shift_date === today);
          setTodayCounter(match ?? null);
        }
      } catch {
        // non-critical
      }
      // Look up historian tag FQN from plugin config
      const mapping = await fetchHistorianMapping(equipmentId);
      if (!cancelled) {
        if (mapping?.state_tag_fqn) {
          setHistTagFqn(mapping.state_tag_fqn);
        } else {
          setHistTagFqn("Simulated.StateTag");
        }
      }
      // Load material setup
      try {
        const [ms, mats] = await Promise.all([
          fetchMaterialSetup(equipmentId),
          fetchEquipmentMaterials(equipmentId),
        ]);
        if (!cancelled) {
          setMaterialSetup_(ms);
          setConfiguredMaterials(mats.filter((m) => m.is_active));
        }
      } catch {
        // non-critical
      }
    })();

    return () => { cancelled = true; };
  }, [equipmentId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function doTransition(t: TransitionDefinition) {
    if (!selectedEquip) return;
    setBusy(true);
    setError(null);
    setLastResult(null);
    try {
      const log = await transitionEquipment(
        selectedEquip.id,
        t.to_state,
        reasonCode || undefined,
        notes || undefined,
      );
      setLastResult(
        `Transitioned to "${log.state}" at ${new Date(log.started_at).toLocaleTimeString()}`,
      );
      setReasonCode("");
      const st = await fetchCurrentState(selectedEquip.id);
      setCurrent(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Transition failed: ${msg}`);
    } finally {
      setBusy(false);
    }
  }

  // PackML integer-to-state name mapping (OPC 40083)
  const PACKML_STATES: { value: number; name: string }[] = [
    { value: 0, name: "Undefined" },
    { value: 1, name: "Clearing" },
    { value: 2, name: "Stopped" },
    { value: 3, name: "Starting" },
    { value: 4, name: "Idle" },
    { value: 5, name: "Suspended" },
    { value: 6, name: "Execute" },
    { value: 7, name: "Stopping" },
    { value: 8, name: "Aborting" },
    { value: 9, name: "Aborted" },
    { value: 10, name: "Holding" },
    { value: 11, name: "Held" },
    { value: 12, name: "Unholding" },
    { value: 13, name: "Suspending" },
    { value: 14, name: "Unsuspending" },
    { value: 15, name: "Resetting" },
    { value: 16, name: "Completing" },
    { value: 17, name: "Complete" },
  ];

  async function simulateOpcua() {
    if (!selectedEquip) return;
    setOpcuaBusy(true);
    setOpcuaError(null);
    setOpcuaResult(null);
    try {
      const log = await simulateOpcuaState(selectedEquip.id, opcuaValue, opcuaTag);
      setOpcuaResult(
        `OPC-UA → "${log.state}" (int=${opcuaValue}) at ${new Date(log.started_at).toLocaleTimeString()}`,
      );
      // Refresh the current state display
      const st = await fetchCurrentState(selectedEquip.id);
      setCurrent(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setOpcuaError(`Simulated OPC-UA event failed: ${msg}`);
    } finally {
      setOpcuaBusy(false);
    }
  }

  async function simulateMqtt() {
    if (!selectedEquip) return;
    setMqttBusy(true);
    setMqttError(null);
    setMqttResult(null);
    try {
      const log = await simulateMqttState(
        selectedEquip.id,
        mqttState,
        mqttReason || undefined,
        mqttTopic,
      );
      const stateName = PACKML_STATES.find((s) => s.value === mqttState)?.name ?? String(mqttState);
      setMqttResult(
        `MQTT → "${log.state}" (int=${mqttState}, ${stateName})${mqttReason ? ` reason=${mqttReason}` : ""} at ${new Date(log.started_at).toLocaleTimeString()}`,
      );
      // Refresh the current state display
      const st = await fetchCurrentState(selectedEquip.id);
      setCurrent(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setMqttError(`Simulated MQTT message failed: ${msg}`);
    } finally {
      setMqttBusy(false);
    }
  }

  async function simulateHistorian() {
    if (!selectedEquip || !histState) return;
    setHistBusy(true);
    setHistError(null);
    setHistResult(null);
    try {
      const log = await simulateHistorianState(selectedEquip.id, histState, histTagFqn);
      setHistResult(
        `Historian → "${log.state}" (tag=${histTagFqn}) at ${new Date(log.started_at).toLocaleTimeString()}`,
      );
      const st = await fetchCurrentState(selectedEquip.id);
      setCurrent(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setHistError(`Simulated Historian event failed: ${msg}`);
    } finally {
      setHistBusy(false);
    }
  }

  async function submitCounts() {
    if (!selectedEquip) return;
    if (goodDelta === 0 && rejectDelta === 0 && reworkDelta === 0) return;
    setCounterBusy(true);
    setCounterError(null);
    setCounterResult(null);
    try {
      const counter = await incrementCounter(
        selectedEquip.id,
        goodDelta,
        rejectDelta,
        reworkDelta,
      );
      setTodayCounter(counter);
      const parts: string[] = [];
      if (goodDelta > 0) parts.push(`+${goodDelta} good`);
      if (rejectDelta > 0) parts.push(`+${rejectDelta} reject`);
      if (reworkDelta > 0) parts.push(`+${reworkDelta} rework`);
      setCounterResult(
        `Counts updated: ${parts.join(", ")} — totals: ${counter.good_count} good, ${counter.reject_count} reject, ${counter.rework_count} rework`,
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setCounterError(`Failed to update counts: ${msg}`);
    } finally {
      setCounterBusy(false);
    }
  }

  async function submitMqttCounts() {
    if (!selectedEquip) return;
    if (mqttProcessed === 0 && mqttDefective === 0 && mqttRework === 0) return;
    setMqttCountBusy(true);
    setMqttCountError(null);
    setMqttCountResult(null);
    try {
      const counter = await simulateMqttCounts(
        selectedEquip.id,
        mqttProcessed,
        mqttDefective,
        mqttRework,
        mqttCountTopic,
      );
      setTodayCounter(counter);
      const topic = mqttCountTopic.replace("{equipment_id}", selectedEquip.id);
      const parts: string[] = [];
      if (mqttProcessed > 0) parts.push(`+${mqttProcessed} processed`);
      if (mqttDefective > 0) parts.push(`+${mqttDefective} defective`);
      if (mqttRework > 0) parts.push(`+${mqttRework} rework`);
      setMqttCountResult(
        `MQTT → topic=${topic} ${parts.join(", ")} — totals: ${counter.good_count} good, ${counter.reject_count} reject, ${counter.rework_count} rework`,
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setMqttCountError(`Simulated MQTT count message failed: ${msg}`);
    } finally {
      setMqttCountBusy(false);
    }
  }

  async function submitHistorianCounts() {
    if (!selectedEquip) return;
    if (histCountProcessed === 0 && histCountDefective === 0 && histCountRework === 0) return;
    setHistCountBusy(true);
    setHistCountError(null);
    setHistCountResult(null);
    try {
      const counter = await simulateHistorianCounts(
        selectedEquip.id,
        histCountProcessed,
        histCountDefective,
        histCountRework,
        histCountTagFqn,
      );
      setTodayCounter(counter);
      const parts: string[] = [];
      if (histCountProcessed > 0) parts.push(`+${histCountProcessed} processed`);
      if (histCountDefective > 0) parts.push(`+${histCountDefective} defective`);
      if (histCountRework > 0) parts.push(`+${histCountRework} rework`);
      setHistCountResult(
        `Historian → tag=${histCountTagFqn} ${parts.join(", ")} — totals: ${counter.good_count} good, ${counter.reject_count} reject, ${counter.rework_count} rework`,
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setHistCountError(`Simulated Historian count failed: ${msg}`);
    } finally {
      setHistCountBusy(false);
    }
  }

  const fullModel = models.find((m) => m.model_id === current?.state_model);

  // Build a lookup: target state name → oee_bucket from the state model
  const targetOeeBuckets: Record<string, string> = {};
  if (fullModel) {
    for (const s of fullModel.states) {
      targetOeeBuckets[s.name] = s.oee_bucket;
    }
  }

  // Valid destination state names from the current state
  const validNextStates = new Set(
    (current?.valid_transitions ?? []).map((t) => t.to_state),
  );

  // PackML states filtered to only valid transitions for OPC-UA / MQTT dropdowns
  const validPackmlStates = PACKML_STATES.filter((s) => validNextStates.has(s.name));

  // Set of OEE buckets reachable via valid transitions from current state
  const reachableBuckets = new Set(
    (current?.valid_transitions ?? [])
      .map((t) => targetOeeBuckets[t.to_state])
      .filter(Boolean),
  );

  // Filter reasons to only those whose oee_bucket matches a reachable target state
  const compatibleReasons = reasons.filter((r) => reachableBuckets.has(r.oee_bucket));

  // When a reason is selected, determine which transitions are compatible
  const selectedReason = reasons.find((r) => r.code === reasonCode);

  function isTransitionCompatible(t: TransitionDefinition): boolean {
    if (!selectedReason) return true; // no reason selected → all transitions available
    const targetBucket = targetOeeBuckets[t.to_state];
    return targetBucket === selectedReason.oee_bucket;
  }

  return (
    <div className="space-y-4">
      {/* Prompt when nothing is selected */}
      {!equipmentId && (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          <p className="text-sm">Select equipment from the tree to begin.</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {/* ── Simulation Tabs ──────────────────────────────────── */}

      {selectedEquip && current && (
        <div>
          {/* Tab bar */}
          <div className="flex border-b border-gray-200">
            {(["availability", "production", "material_setup"] as const).map((tab) => (
              <button
                key={tab}
                className={`px-5 py-2 text-sm font-medium border-b-2 -mb-px ${
                  simTab === tab
                    ? "border-emerald-500 text-emerald-700"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
                onClick={() => setSimTab(tab)}
              >
                {tab === "availability" ? "Availability" : tab === "production" ? "Production" : "Material Setup"}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="space-y-4 pt-4">

          {/* ── Availability tab ──────────────────────────────────── */}
          {simTab === "availability" && (
            <>
              {/* ── Transition Control Panel ──────────────────────────────── */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-gray-600 uppercase">
                    Transition Control — {selectedEquip.code} ({selectedEquip.name})
                  </h2>
                  <div className="flex items-center gap-2">
                    <button
                      className="text-xs text-emerald-600 hover:text-emerald-800 font-medium"
                      onClick={() => navigateTo("history")}
                    >
                      History →
                    </button>
                    <button
                      className="text-xs text-emerald-600 hover:text-emerald-800 font-medium"
                      onClick={() => navigateTo("oee")}
                    >
                      OEE →
                    </button>
                    <button
                      className="text-xs text-gray-400 hover:text-gray-600"
                      onClick={() => setEquipment(null, null)}
                    >
                      ✕ close
                    </button>
                  </div>
                </div>

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

                {/* Optional metadata */}
                <div className="flex gap-3">
                  <label className="flex flex-col text-xs font-medium text-gray-600 flex-1">
                    Reason Code (optional)
                    <select
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm bg-white"
                      value={reasonCode}
                      onChange={(e) => setReasonCode(e.target.value)}
                    >
                      <option value="">— none —</option>
                      {compatibleReasons.map((r) => (
                        <option key={r.id} value={r.code}>
                          {r.code} — {r.name} ({r.oee_bucket})
                        </option>
                      ))}
                    </select>
                    {compatibleReasons.length === 0 && reasons.length > 0 && (
                      <span className="text-xs text-amber-600 mt-0.5">
                        No reasons match the reachable states
                      </span>
                    )}
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
                      const compatible = isTransitionCompatible(t);
                      return (
                        <button
                          key={`${t.from_state}-${t.to_state}`}
                          className={`px-3 py-1.5 rounded border text-sm flex items-center gap-2 ${
                            compatible
                              ? "hover:bg-gray-50 disabled:opacity-50"
                              : "opacity-40 cursor-not-allowed"
                          }`}
                          onClick={() => doTransition(t)}
                          disabled={busy || !compatible}
                          title={
                            compatible
                              ? undefined
                              : `Reason "${selectedReason?.name}" (${selectedReason?.oee_bucket}) ≠ target "${t.to_state}" (${targetOeeBuckets[t.to_state]})`
                          }
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

              {/* OPC-UA State Simulation — PackML-only */}
              {current?.state_model === "packml" && (
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Simulate OPC-UA State Change — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Simulates an OPC-UA data-change notification on a PackML CurrentState tag.
                  Select a PackML state (OPC 40083 integer) and fire the event.
                </p>

                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    OPC-UA Tag
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-72"
                      value={opcuaTag}
                      onChange={(e) => setOpcuaTag(e.target.value)}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    PackML State
                    <select
                      className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm"
                      value={opcuaValue}
                      onChange={(e) => setOpcuaValue(Number(e.target.value))}
                    >
                      {validPackmlStates.length === 0 && (
                        <option value="">— no valid transitions —</option>
                      )}
                      {validPackmlStates.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.value} — {s.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <button
                    className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
                    onClick={simulateOpcua}
                    disabled={opcuaBusy || validPackmlStates.length === 0}
                  >
                    {opcuaBusy ? "Sending…" : "Send OPC-UA Event"}
                  </button>
                </div>

                {opcuaResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {opcuaResult}
                  </div>
                )}
                {opcuaError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {opcuaError}
                  </div>
                )}
              </div>
              )}

              {/* MQTT State Simulation */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Simulate MQTT State Message — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Simulates an MQTT JSON message on a state topic.
                  Payload: <code className="bg-gray-100 px-1 rounded">
                  {`{"state": ${mqttState}, "reason_code": ${mqttReason ? `"${mqttReason}"` : "null"}}`}
                  </code>
                </p>

                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    MQTT Topic
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-80"
                      value={mqttTopic}
                      onChange={(e) => setMqttTopic(e.target.value)}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    PackML State
                    <select
                      className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm"
                      value={mqttState}
                      onChange={(e) => setMqttState(Number(e.target.value))}
                    >
                      {validPackmlStates.length === 0 && (
                        <option value="">— no valid transitions —</option>
                      )}
                      {validPackmlStates.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.value} — {s.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Reason Code (optional)
                    <select
                      className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm"
                      value={mqttReason}
                      onChange={(e) => setMqttReason(e.target.value)}
                    >
                      <option value="">— none —</option>
                      {reasons.map((r) => (
                        <option key={r.id} value={r.code}>
                          {r.code} — {r.name} ({r.oee_bucket})
                        </option>
                      ))}
                    </select>
                  </label>

                  <button
                    className="px-4 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50"
                    onClick={simulateMqtt}
                    disabled={mqttBusy}
                  >
                    {mqttBusy ? "Sending…" : "Publish MQTT Message"}
                  </button>
                </div>

                {mqttResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {mqttResult}
                  </div>
                )}
                {mqttError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {mqttError}
                  </div>
                )}
              </div>

              {/* Historian State Simulation */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Simulate Historian State Change — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Simulates an AVEVA Historian tag value change. The tag FQN is
                  auto-populated from the AVEVA Historian plugin configuration
                  when a mapping exists for this equipment.
                </p>

                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Tag FQN
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-72"
                      value={histTagFqn}
                      onChange={(e) => setHistTagFqn(e.target.value)}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    State
                    {fullModel ? (
                      <select
                        className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm"
                        value={histState}
                        onChange={(e) => setHistState(e.target.value)}
                      >
                        <option value="">— select —</option>
                        {fullModel.states
                          .filter((s) => validNextStates.has(s.name))
                          .map((s) => (
                            <option key={s.name} value={s.name}>
                              {s.name} ({s.dispatch_category})
                            </option>
                          ))}
                      </select>
                    ) : (
                      <input
                        className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-40"
                        value={histState}
                        onChange={(e) => setHistState(e.target.value)}
                        placeholder="e.g. Running"
                      />
                    )}
                  </label>

                  <button
                    className="px-4 py-1.5 bg-amber-600 text-white text-sm rounded hover:bg-amber-700 disabled:opacity-50"
                    onClick={simulateHistorian}
                    disabled={histBusy || !histState}
                  >
                    {histBusy ? "Sending…" : "Send Historian Event"}
                  </button>
                </div>

                {histResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {histResult}
                  </div>
                )}
                {histError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {histError}
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Production tab ────────────────────────────────────── */}
          {simTab === "production" && (
            <>
              {/* Production Counts */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Production Counts — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Enter processed (good), defective (reject), and rework counts.
                  Values are added as deltas to today's shift counter via the
                  PackML <code className="bg-gray-100 px-1 rounded">Admin.ProdProcessedCount</code>
                  {" / "}
                  <code className="bg-gray-100 px-1 rounded">Admin.ProdDefectiveCount</code> model.
                </p>

                {/* Today's running totals */}
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <p className="text-xs text-green-600 font-medium uppercase">Good</p>
                    <p className="text-2xl font-bold text-green-700">{todayCounter?.good_count ?? 0}</p>
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-xs text-red-600 font-medium uppercase">Reject</p>
                    <p className="text-2xl font-bold text-red-700">{todayCounter?.reject_count ?? 0}</p>
                  </div>
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <p className="text-xs text-amber-600 font-medium uppercase">Rework</p>
                    <p className="text-2xl font-bold text-amber-700">{todayCounter?.rework_count ?? 0}</p>
                  </div>
                </div>

                {/* Delta inputs */}
                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Processed (Good)
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={goodDelta}
                      onChange={(e) => setGoodDelta(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Defective (Reject)
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={rejectDelta}
                      onChange={(e) => setRejectDelta(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Rework
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={reworkDelta}
                      onChange={(e) => setReworkDelta(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <button
                    className="px-4 py-1.5 bg-teal-600 text-white text-sm rounded hover:bg-teal-700 disabled:opacity-50"
                    onClick={submitCounts}
                    disabled={counterBusy || (goodDelta === 0 && rejectDelta === 0 && reworkDelta === 0)}
                  >
                    {counterBusy ? "Submitting…" : "Submit Counts"}
                  </button>
                </div>

                {counterResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {counterResult}
                  </div>
                )}
                {counterError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {counterError}
                  </div>
                )}
              </div>

              {/* MQTT Production Counts Simulation */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Simulate MQTT Production Counts — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Simulates an MQTT JSON message on a count topic carrying PackML PackTag deltas.
                  Payload: <code className="bg-gray-100 px-1 rounded">
                  {`{"processed_count": ${mqttProcessed}, "defective_count": ${mqttDefective}, "rework_count": ${mqttRework}}`}
                  </code>
                </p>

                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    MQTT Topic
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-80"
                      value={mqttCountTopic}
                      onChange={(e) => setMqttCountTopic(e.target.value)}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Processed (Good)
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={mqttProcessed}
                      onChange={(e) => setMqttProcessed(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Defective (Reject)
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={mqttDefective}
                      onChange={(e) => setMqttDefective(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Rework
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={mqttRework}
                      onChange={(e) => setMqttRework(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <button
                    className="px-4 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50"
                    onClick={submitMqttCounts}
                    disabled={mqttCountBusy || (mqttProcessed === 0 && mqttDefective === 0 && mqttRework === 0)}
                  >
                    {mqttCountBusy ? "Sending…" : "Publish MQTT Counts"}
                  </button>
                </div>

                {mqttCountResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {mqttCountResult}
                  </div>
                )}
                {mqttCountError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {mqttCountError}
                  </div>
                )}
              </div>

              {/* AVEVA Historian Production Counts Simulation */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Simulate Historian Production Counts — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Simulates an AVEVA Historian tag data-change event carrying production count deltas,
                  as if the historian polling plugin detected incremented count tags.
                </p>

                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Tag FQN
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-80"
                      value={histCountTagFqn}
                      onChange={(e) => setHistCountTagFqn(e.target.value)}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Processed (Good)
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={histCountProcessed}
                      onChange={(e) => setHistCountProcessed(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Defective (Reject)
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={histCountDefective}
                      onChange={(e) => setHistCountDefective(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Rework
                    <input
                      type="number"
                      min={0}
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-28"
                      value={histCountRework}
                      onChange={(e) => setHistCountRework(Math.max(0, Number(e.target.value)))}
                    />
                  </label>

                  <button
                    className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
                    onClick={submitHistorianCounts}
                    disabled={histCountBusy || (histCountProcessed === 0 && histCountDefective === 0 && histCountRework === 0)}
                  >
                    {histCountBusy ? "Sending…" : "Submit Historian Counts"}
                  </button>
                </div>

                {histCountResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {histCountResult}
                  </div>
                )}
                {histCountError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {histCountError}
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Material Setup tab ──────────────────────────────────── */}
          {simTab === "material_setup" && (
            <>
              {/* Current Material Setup */}
              <div className="bg-white rounded-lg border p-4 space-y-3">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Current Material Setup
                </h2>
                {materialSetup?.equipment_material_id ? (
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    <div>
                      <span className="text-gray-500">Material:</span>{" "}
                      <span className="font-medium">{materialSetup.material_name ?? "—"}</span>
                      {materialSetup.material_code && (
                        <span className="text-gray-400 ml-1">({materialSetup.material_code})</span>
                      )}
                    </div>
                    <div>
                      <span className="text-gray-500">Job Number:</span>{" "}
                      <span className="font-medium">{materialSetup.job_number || "—"}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Design Speed:</span>{" "}
                      <span className="font-medium">
                        {materialSetup.design_speed != null ? materialSetup.design_speed : "—"}
                        {materialSetup.design_speed_uom ? ` ${materialSetup.design_speed_uom}` : ""}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Setup At:</span>{" "}
                      <span className="font-medium">
                        {materialSetup.setup_at
                          ? new Date(materialSetup.setup_at).toLocaleString()
                          : "—"}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 italic">No material is currently set up.</p>
                )}
                {materialSetup?.equipment_material_id && (
                  <button
                    className="text-xs text-red-600 hover:text-red-800 font-medium"
                    onClick={async () => {
                      if (!equipmentId) return;
                      setSetupBusy(true);
                      setSetupError(null);
                      try {
                        await clearMaterialSetup(equipmentId);
                        setMaterialSetup_(null);
                      } catch (err: unknown) {
                        setSetupError(err instanceof Error ? err.message : String(err));
                      } finally {
                        setSetupBusy(false);
                      }
                    }}
                    disabled={setupBusy}
                  >
                    Clear Setup
                  </button>
                )}
              </div>

              {/* Switch Material */}
              <div className="bg-white rounded-lg border p-4 space-y-3">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Switch Material
                </h2>
                {configuredMaterials.length === 0 ? (
                  <p className="text-sm text-gray-400 italic">
                    No materials configured for this equipment. Add material setups in the Design-Time client.
                  </p>
                ) : (
                  <div className="flex flex-wrap items-end gap-3">
                    <label className="flex flex-col text-xs font-medium text-gray-600">
                      Material
                      <select
                        className="mt-0.5 rounded border border-gray-300 px-2 py-1.5 text-sm min-w-[220px]"
                        value={selectedEmId}
                        onChange={(e) => setSelectedEmId(e.target.value)}
                      >
                        <option value="">— Select material —</option>
                        {configuredMaterials.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.material_name ?? m.material_code ?? m.material_id} (speed: {m.design_speed} {m.design_speed_uom})
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="flex flex-col text-xs font-medium text-gray-600">
                      Job Number
                      <input
                        type="text"
                        className="mt-0.5 rounded border border-gray-300 px-2 py-1.5 text-sm w-40"
                        placeholder="Optional"
                        value={jobNumber}
                        onChange={(e) => setJobNumber(e.target.value)}
                      />
                    </label>

                    <button
                      className="px-4 py-1.5 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700 disabled:opacity-50"
                      disabled={!selectedEmId || setupBusy}
                      onClick={async () => {
                        if (!equipmentId || !selectedEmId) return;
                        setSetupBusy(true);
                        setSetupError(null);
                        try {
                          const result = await setMaterialSetup(
                            equipmentId,
                            selectedEmId,
                            jobNumber || null,
                          );
                          setMaterialSetup_(result);
                          setSelectedEmId("");
                          setJobNumber("");
                        } catch (err: unknown) {
                          setSetupError(err instanceof Error ? err.message : String(err));
                        } finally {
                          setSetupBusy(false);
                        }
                      }}
                    >
                      {setupBusy ? "Switching…" : "Switch Material"}
                    </button>
                  </div>
                )}

                {setupError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {setupError}
                  </div>
                )}
              </div>

              {/* OPC-UA Material Setup Simulation */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Simulate OPC-UA Material Setup — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Simulates an OPC-UA data-change notification on a material-setup tag.
                  Select a material code configured for this equipment and fire the event.
                </p>

                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    OPC-UA Tag
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-72"
                      value={opcuaSetupTag}
                      onChange={(e) => setOpcuaSetupTag(e.target.value)}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Material
                    <select
                      className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm min-w-[180px]"
                      value={opcuaSetupCode}
                      onChange={(e) => setOpcuaSetupCode(e.target.value)}
                    >
                      <option value="">— select —</option>
                      {configuredMaterials.map((m) => (
                        <option key={m.id} value={m.material_code ?? ""}>
                          {m.material_code} — {m.material_name ?? m.material_id}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Job Number
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-32"
                      value={opcuaSetupJob}
                      onChange={(e) => setOpcuaSetupJob(e.target.value)}
                      placeholder="Optional"
                    />
                  </label>

                  <button
                    className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
                    disabled={opcuaSetupBusy || !opcuaSetupCode}
                    onClick={async () => {
                      if (!equipmentId || !opcuaSetupCode) return;
                      setOpcuaSetupBusy(true);
                      setOpcuaSetupError(null);
                      setOpcuaSetupResult(null);
                      try {
                        const result = await simulateOpcuaMaterialSetup(
                          equipmentId, opcuaSetupCode, opcuaSetupJob || null, opcuaSetupTag,
                        );
                        setMaterialSetup_(result);
                        setOpcuaSetupResult(
                          `OPC-UA → material="${result.material_name}" (${result.material_code}) tag=${opcuaSetupTag}${result.job_number ? ` job=${result.job_number}` : ""}`,
                        );
                      } catch (err: unknown) {
                        setOpcuaSetupError(err instanceof Error ? err.message : String(err));
                      } finally {
                        setOpcuaSetupBusy(false);
                      }
                    }}
                  >
                    {opcuaSetupBusy ? "Sending…" : "Send OPC-UA Event"}
                  </button>
                </div>

                {opcuaSetupResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {opcuaSetupResult}
                  </div>
                )}
                {opcuaSetupError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {opcuaSetupError}
                  </div>
                )}
              </div>

              {/* MQTT Material Setup Simulation */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Simulate MQTT Material Setup — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Simulates an MQTT JSON message on a material-setup topic.
                  Payload: <code className="bg-gray-100 px-1 rounded">
                  {`{"material_code": "${mqttSetupCode || "..."}", "job_number": ${mqttSetupJob ? `"${mqttSetupJob}"` : "null"}}`}
                  </code>
                </p>

                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    MQTT Topic
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-80"
                      value={mqttSetupTopic}
                      onChange={(e) => setMqttSetupTopic(e.target.value)}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Material
                    <select
                      className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm min-w-[180px]"
                      value={mqttSetupCode}
                      onChange={(e) => setMqttSetupCode(e.target.value)}
                    >
                      <option value="">— select —</option>
                      {configuredMaterials.map((m) => (
                        <option key={m.id} value={m.material_code ?? ""}>
                          {m.material_code} — {m.material_name ?? m.material_id}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Job Number
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-32"
                      value={mqttSetupJob}
                      onChange={(e) => setMqttSetupJob(e.target.value)}
                      placeholder="Optional"
                    />
                  </label>

                  <button
                    className="px-4 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50"
                    disabled={mqttSetupBusy || !mqttSetupCode}
                    onClick={async () => {
                      if (!equipmentId || !mqttSetupCode) return;
                      setMqttSetupBusy(true);
                      setMqttSetupError(null);
                      setMqttSetupResult(null);
                      try {
                        const result = await simulateMqttMaterialSetup(
                          equipmentId, mqttSetupCode, mqttSetupJob || null, mqttSetupTopic,
                        );
                        setMaterialSetup_(result);
                        const topic = mqttSetupTopic.replace("{equipment_id}", equipmentId);
                        setMqttSetupResult(
                          `MQTT → topic=${topic} material="${result.material_name}" (${result.material_code})${result.job_number ? ` job=${result.job_number}` : ""}`,
                        );
                      } catch (err: unknown) {
                        setMqttSetupError(err instanceof Error ? err.message : String(err));
                      } finally {
                        setMqttSetupBusy(false);
                      }
                    }}
                  >
                    {mqttSetupBusy ? "Sending…" : "Publish MQTT Message"}
                  </button>
                </div>

                {mqttSetupResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {mqttSetupResult}
                  </div>
                )}
                {mqttSetupError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {mqttSetupError}
                  </div>
                )}
              </div>

              {/* Historian Material Setup Simulation */}
              <div className="bg-white rounded-lg border p-4 space-y-4">
                <h2 className="text-sm font-semibold text-gray-600 uppercase">
                  Simulate Historian Material Setup — {selectedEquip.code}
                </h2>
                <p className="text-xs text-gray-500">
                  Simulates an AVEVA Historian tag value change that triggers a
                  material setup switch on the equipment.
                </p>

                <div className="flex flex-wrap items-end gap-4">
                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Tag FQN
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-72"
                      value={histSetupTagFqn}
                      onChange={(e) => setHistSetupTagFqn(e.target.value)}
                    />
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Material
                    <select
                      className="mt-0.5 rounded border border-gray-300 bg-white px-2 py-1 text-sm min-w-[180px]"
                      value={histSetupCode}
                      onChange={(e) => setHistSetupCode(e.target.value)}
                    >
                      <option value="">— select —</option>
                      {configuredMaterials.map((m) => (
                        <option key={m.id} value={m.material_code ?? ""}>
                          {m.material_code} — {m.material_name ?? m.material_id}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="flex flex-col text-xs font-medium text-gray-600">
                    Job Number
                    <input
                      className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm w-32"
                      value={histSetupJob}
                      onChange={(e) => setHistSetupJob(e.target.value)}
                      placeholder="Optional"
                    />
                  </label>

                  <button
                    className="px-4 py-1.5 bg-amber-600 text-white text-sm rounded hover:bg-amber-700 disabled:opacity-50"
                    disabled={histSetupBusy || !histSetupCode}
                    onClick={async () => {
                      if (!equipmentId || !histSetupCode) return;
                      setHistSetupBusy(true);
                      setHistSetupError(null);
                      setHistSetupResult(null);
                      try {
                        const result = await simulateHistorianMaterialSetup(
                          equipmentId, histSetupCode, histSetupJob || null, histSetupTagFqn,
                        );
                        setMaterialSetup_(result);
                        setHistSetupResult(
                          `Historian → tag=${histSetupTagFqn} material="${result.material_name}" (${result.material_code})${result.job_number ? ` job=${result.job_number}` : ""}`,
                        );
                      } catch (err: unknown) {
                        setHistSetupError(err instanceof Error ? err.message : String(err));
                      } finally {
                        setHistSetupBusy(false);
                      }
                    }}
                  >
                    {histSetupBusy ? "Sending…" : "Send Historian Event"}
                  </button>
                </div>

                {histSetupResult && (
                  <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg p-3">
                    {histSetupResult}
                  </div>
                )}
                {histSetupError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                    {histSetupError}
                  </div>
                )}
              </div>
            </>
          )}

          </div>
        </div>
      )}
    </div>
  );
}
