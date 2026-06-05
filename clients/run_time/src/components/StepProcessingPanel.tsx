import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { StepContext, Unit, Lot, DataDefinition, StepEquipmentStatus, BOMItem, Material, MaterialLot, MaterialConsumption, UnitHistory, LotHistory, DispositionCatalog, EquipmentCurrentState } from "../types";
import {
  startUnit, completeUnit, moveUnit, holdUnit, releaseHoldUnit, scrapUnit,
  startLot, completeLot, moveLot, holdLot, releaseHoldLot, scrapLot,
  collectDataBatch, fetchStepEquipment,
  fetchStepBomItems, fetchMaterials, fetchMaterialLots, consumeMaterial, fetchConsumedMaterials,
  fetchUnitHistory, fetchLotHistory, fetchDispositionCatalog,
  fetchEquipmentCurrentState, transitionEquipmentState,
} from "../api/runtime";

// State-model walker: drives a PackML / SEMI E10 equipment to the desired
// canonical state via sequential transition POSTs. Silently bails if the
// model is unknown or the current state is off the production path.
async function walkEquipmentToState(
  equipId: string,
  modelId: string,
  currentState: string,
  phase: "start" | "complete",
): Promise<void> {
  if (modelId === "semi_e10") {
    const target = phase === "start" ? "Productive" : "Standby";
    if (currentState !== target) {
      await transitionEquipmentState(equipId, target, `WIP ${phase}`);
    }
    return;
  }
  if (modelId === "packml") {
    const path = phase === "start"
      ? ["Stopped", "Resetting", "Idle", "Starting", "Execute"]
      : ["Execute", "Completing", "Complete", "Resetting", "Idle"];
    const idx = path.indexOf(currentState);
    if (idx < 0) return; // off the production path — no-op
    for (let i = idx + 1; i < path.length; i++) {
      await transitionEquipmentState(equipId, path[i], `WIP ${phase}`);
    }
  }
}

interface Props {
  context: StepContext;
  onRefresh: () => Promise<void>;
}

export default function StepProcessingPanel({ context, onRefresh }: Props) {
  const { wip_type, wip, step, step_parameters, data_definitions, dispositions, route_steps, outgoing_conditions } = context;
  const isUnit = wip_type === "unit";
  const identifier = isUnit ? (wip as Unit).serial_number : (wip as Lot).lot_number;
  const queryClient = useQueryClient();

  // Map step id → "Seq: Name" for destination labels in the disposition dropdown
  const stepNameById = useMemo(
    () => Object.fromEntries(
      route_steps.map((s) => [s.id, `${s.sequence}: ${s.name}`]),
    ),
    [route_steps],
  );

  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Data collection form state
  const [dataValues, setDataValues] = useState<Record<string, string>>({});
  // Tracks values already persisted via Save (or a prior auto-submit on
  // Complete). Used to avoid re-submitting the same values when the
  // operator hits Complete after Save — which would create duplicate
  // data points in the database.
  const [savedValues, setSavedValues] = useState<Record<string, string>>({});

  // Actual values entered by operator for step parameters (stored in data_snapshot)
  const [paramValues, setParamValues] = useState<Record<string, string>>({});

  // Hold/scrap reason
  const [holdReason, setHoldReason] = useState("");
  const [scrapReason, setScrapReason] = useState("");
  const [releaseReason, setReleaseReason] = useState("");

  // Lot completion quantities
  const [qtyOut, setQtyOut] = useState<string>("");
  const [qtyScrapped, setQtyScrapped] = useState("0");

  // Disposition
  const [selectedDisposition, setSelectedDisposition] = useState("");

  // When the step exposes exactly one disposition AND has no result-based
  // outgoing transitions (on_pass/on_fail/on_rework), auto-select it so the
  // submission carries the value even if the operator never opens the
  // dropdown. When result transitions also exist, the disposition is an
  // exception path and must be picked explicitly.
  useEffect(() => {
    const hasResultRouting = (outgoing_conditions ?? []).some(
      (c) => c === "on_pass" || c === "on_fail" || c === "on_rework",
    );
    if (dispositions.length >= 1 && !hasResultRouting) {
      const first = dispositions[0];
      const value = first.name ?? first.label ?? "";
      if (value && selectedDisposition !== value && !dispositions.some((d) => (d.name ?? d.label) === selectedDisposition)) {
        setSelectedDisposition(value);
      }
    }
    // Reset selection when the step changes and the new step has no
    // dispositions, so a stale label cannot leak across step contexts.
    if (dispositions.length === 0 && selectedDisposition !== "") {
      setSelectedDisposition("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispositions, outgoing_conditions, step?.id]);

  // Complete result
  const [completeResult, setCompleteResult] = useState<"pass" | "fail" | "rework">("pass");

  // Equipment override
  const [equipmentOverride, setEquipmentOverride] = useState("");

  // Transition equipment state on Start / Complete (default off)
  const [transitionOnStart, setTransitionOnStart] = useState(false);
  const [transitionOnComplete, setTransitionOnComplete] = useState(false);

  // Material consumption — per-BOM-item lot selection and quantity
  const [lotSelections, setLotSelections] = useState<Record<string, string>>({});
  const [qtyInputs, setQtyInputs] = useState<Record<string, string>>({});
  const [consumeLoading, setConsumeLoading] = useState<string | null>(null);

  // Fetch equipment status at this step
  const { data: stepEquipment = [] } = useQuery<StepEquipmentStatus[]>({
    queryKey: ["step-equipment", step?.id, wip.material_id, wip.current_equipment_id],
    queryFn: () => fetchStepEquipment(step!.id, wip.material_id, wip.current_equipment_id),
    enabled: !!step && (wip.status === "queued" || wip.status === "in_process"),
    refetchInterval: 10_000,
  });

  // Fetch the current PackML / E10 state of the assigned equipment (in_process)
  useQuery<EquipmentCurrentState>({
    queryKey: ["equipment-current-state", wip.current_equipment_id],
    queryFn: () => fetchEquipmentCurrentState(wip.current_equipment_id!),
    enabled: !!wip.current_equipment_id && wip.status === "in_process",
    refetchInterval: 10_000,
  });

  // Fetch BOM items for the current step
  const { data: bomItems = [] } = useQuery<BOMItem[]>({
    queryKey: ["step-bom-items", step?.id],
    queryFn: () => fetchStepBomItems(step!.id),
    enabled: !!step && wip.status === "in_process",
  });

  // Fetch material definitions (for code → id mapping)
  const { data: materials = [] } = useQuery<Material[]>({
    queryKey: ["materials"],
    queryFn: () => fetchMaterials(),
    enabled: wip.status === "in_process",
  });

  // Fetch available material lots for consumption
  const { data: materialLots = [] } = useQuery<MaterialLot[]>({
    queryKey: ["material-lots-available"],
    queryFn: () => fetchMaterialLots(undefined, "available"),
    enabled: wip.status === "in_process",
  });

  // Fetch already-consumed materials for this WIP
  const { data: consumedMaterials = [], refetch: refetchConsumed } = useQuery<MaterialConsumption[]>({
    queryKey: ["consumed-materials", wip_type, wip.id],
    queryFn: () => fetchConsumedMaterials(wip_type, wip.id),
    enabled: wip.status === "in_process",
  });

  // Fetch WIP processing history
  const { data: wipHistory = [] } = useQuery<UnitHistory[] | LotHistory[]>({
    queryKey: ["wip-history", wip_type, wip.id],
    queryFn: () => isUnit ? fetchUnitHistory(wip.id) : fetchLotHistory(wip.id),
  });

  // Fetch dispositions filtered by category for the hold/scrap dropdowns
  const { data: holdDispositions = [] } = useQuery<DispositionCatalog[]>({
    queryKey: ["dispositions", "hold"],
    queryFn: () => fetchDispositionCatalog("hold"),
  });
  const { data: scrapDispositions = [] } = useQuery<DispositionCatalog[]>({
    queryKey: ["dispositions", "scrap"],
    queryFn: () => fetchDispositionCatalog("scrap"),
  });
  const { data: releaseDispositions = [] } = useQuery<DispositionCatalog[]>({
    queryKey: ["dispositions", "release"],
    queryFn: () => fetchDispositionCatalog("release"),
  });

  // Build step lookup for history table
  const stepMap = Object.fromEntries(route_steps.map((s) => [s.id, s]));

  const runAction = async (fn: () => Promise<unknown>, msg: string) => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await fn();
      setSuccessMsg(msg);
      // Invalidate all related queries so other pages refresh immediately
      await queryClient.invalidateQueries({ queryKey: ["units"] });
      await queryClient.invalidateQueries({ queryKey: ["lots"] });
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      await queryClient.invalidateQueries({ queryKey: ["order-progress"] });
      await queryClient.invalidateQueries({ queryKey: ["shift-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["wip-history"] });
      await onRefresh();
    } catch (err: unknown) {
      const m = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ?? "Action failed";
      setError(m);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = () =>
    runAction(
      async () => {
        // If "Transition State" is checked, pre-walk any candidate equipment
        // that is otherwise eligible but blocked only by its dispatch state
        // (e.g. PackML "Stopped" → "Execute"). This unblocks the dispatch
        // call below.
        if (transitionOnStart) {
          const candidates = stepEquipment.filter(
            (e) =>
              e.has_spare_capacity
              && e.material_setup
              && e.dispatch_category
              && e.dispatch_category !== "available"
              && (equipmentOverride === "" || equipmentOverride === e.equipment_id),
          );
          for (const e of candidates) {
            try {
              const cs = await fetchEquipmentCurrentState(e.equipment_id);
              if (cs.state_model === "packml" || cs.state_model === "semi_e10") {
                await walkEquipmentToState(
                  e.equipment_id, cs.state_model, cs.state, "start",
                );
              }
            } catch (err) {
              console.warn(`Pre-start state walk failed for ${e.equipment_code}:`, err);
            }
          }
        }

        const updated = isUnit
          ? await startUnit(wip.id, equipmentOverride || undefined)
          : await startLot(wip.id, equipmentOverride || undefined);
        if (transitionOnStart && updated.current_equipment_id) {
          try {
            const cs = await fetchEquipmentCurrentState(updated.current_equipment_id);
            if (cs.state_model === "packml" || cs.state_model === "semi_e10") {
              await walkEquipmentToState(
                updated.current_equipment_id, cs.state_model, cs.state, "start",
              );
            }
          } catch (e) {
            console.warn("Equipment state transition on start failed:", e);
          }
        }
        return updated;
      },
      "Started processing",
    );

  // Build & submit data-collection batch from current dataValues. Returns
  // the number of items actually submitted. Only values that differ from
  // the last persisted snapshot (savedValues) are sent, so calling this
  // after Save will not duplicate already-saved points.
  const submitDataCollection = async (): Promise<number> => {
    if (data_definitions.length === 0) return 0;
    const pending = data_definitions.filter((dd) => {
      const cur = dataValues[dd.id] ?? "";
      const prev = savedValues[dd.id] ?? "";
      return cur !== "" && cur !== prev;
    });
    if (pending.length === 0) return 0;
    const items = pending.map((dd: DataDefinition) => {
      const val = dataValues[dd.id] ?? "";
      const base: Record<string, unknown> = {
        definition_id: dd.id,
        ...(isUnit ? { unit_id: wip.id } : { lot_id: wip.id }),
      };
      if (dd.data_type === "numeric") base.value_numeric = val ? parseFloat(val) : undefined;
      else if (dd.data_type === "boolean") base.value_boolean = val === "true";
      else base.value_string = val || undefined;
      return base as Parameters<typeof collectDataBatch>[0][number];
    });
    await collectDataBatch(items);
    // Mark these values as persisted so a subsequent Complete won't
    // re-submit them.
    setSavedValues((prev) => {
      const next = { ...prev };
      for (const dd of pending) next[dd.id] = dataValues[dd.id] ?? "";
      return next;
    });
    return items.length;
  };

  const handleSaveData = () => {
    // Pre-flight: any unsaved non-empty values entered?
    const hasPending = data_definitions.some((dd) => {
      const cur = dataValues[dd.id] ?? "";
      const prev = savedValues[dd.id] ?? "";
      return cur !== "" && cur !== prev;
    });
    if (!hasPending) {
      setError("No new data values to save");
      setSuccessMsg(null);
      return;
    }
    return runAction(async () => {
      await submitDataCollection();
    }, "Data values saved");
  };

  const handleComplete = async () => {
    // Collect data points if any
    await submitDataCollection();

    // Build data snapshot
    const snapshot: Record<string, unknown> = {};
    for (const dd of data_definitions) {
      const val = dataValues[dd.id];
      if (val !== undefined && val !== "") snapshot[dd.code] = dd.data_type === "numeric" ? parseFloat(val) : val;
    }
    for (const p of step_parameters) {
      const val = paramValues[p.id];
      if (val !== undefined && val !== "") snapshot[p.name] = p.data_type === "numeric" ? parseFloat(val) : val;
    }

    await runAction(
      async () => {
        const disp = selectedDisposition || undefined;
        const moveOpts: { disposition?: string; result?: string } = { result: completeResult };
        if (disp) moveOpts.disposition = disp;
        const snap = Object.keys(snapshot).length > 0 ? snapshot : undefined;
        const equipIdAtComplete = wip.current_equipment_id;
        if (isUnit) {
          await completeUnit(wip.id, completeResult, snap, disp);
          await moveUnit(wip.id, moveOpts);
        } else {
          await completeLot(wip.id, qtyOut ? parseInt(qtyOut) : undefined, parseInt(qtyScrapped) || 0, disp, snap);
          await moveLot(wip.id, moveOpts);
        }
        if (transitionOnComplete && equipIdAtComplete) {
          try {
            const cs = await fetchEquipmentCurrentState(equipIdAtComplete);
            if (cs.state_model === "packml" || cs.state_model === "semi_e10") {
              await walkEquipmentToState(
                equipIdAtComplete, cs.state_model, cs.state, "complete",
              );
            }
          } catch (e) {
            console.warn("Equipment state transition on complete failed:", e);
          }
        }
      },
      "Step completed",
    );
  };

  const handleHold = () =>
    runAction(
      () => isUnit ? holdUnit(wip.id, holdReason) : holdLot(wip.id, holdReason),
      "Placed on hold",
    );

  const handleReleaseHold = () =>
    runAction(
      () => isUnit ? releaseHoldUnit(wip.id, releaseReason) : releaseHoldLot(wip.id, releaseReason),
      "Released from hold",
    );

  const handleScrap = () =>
    runAction(
      () => isUnit ? scrapUnit(wip.id, scrapReason) : scrapLot(wip.id, scrapReason),
      "Scrapped",
    );

  const handleConsumeLine = async (bomItem: BOMItem) => {
    const lotId = lotSelections[bomItem.id];
    const qty = qtyInputs[bomItem.id];
    if (!lotId || !qty || parseFloat(qty) <= 0) return;
    setConsumeLoading(bomItem.id);
    setError(null);
    setSuccessMsg(null);
    try {
      await consumeMaterial(lotId, {
        ...(isUnit ? { unit_id: wip.id } : { lot_id: wip.id }),
        step_id: step?.id,
        quantity_consumed: parseFloat(qty),
      });
      setSuccessMsg(`Consumed ${qty} ${bomItem.uom_symbol ?? ""} of ${bomItem.material_code}`);
      // Keep the selected lot so the operator can consume more from the
      // same lot without re-selecting; only clear the quantity input.
      setQtyInputs((prev) => ({ ...prev, [bomItem.id]: "" }));
      await refetchConsumed();
      await queryClient.invalidateQueries({ queryKey: ["material-lots-available"] });
    } catch (err: unknown) {
      const m = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ?? "Consumption failed";
      setError(m);
    } finally {
      setConsumeLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* WIP Header */}
      <div className="bg-white rounded-lg shadow p-5">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs uppercase tracking-wider text-gray-400">{wip_type}</span>
            <h3 className="text-xl font-bold text-gray-800 font-mono">{identifier}</h3>
          </div>
          <WipStatusBadge status={wip.status} />
        </div>
        {!isUnit && <p className="text-sm text-gray-500 mt-1">Quantity: {(wip as Lot).quantity}{(wip as Lot).uom_symbol ? ` ${(wip as Lot).uom_symbol}` : ""}</p>}
      </div>

      {/* Step History */}
      <div className="bg-white rounded-lg shadow p-5">
        <h4 className="font-semibold text-gray-700 mb-3">Step History</h4>
        {(() => {
          // Build one row per history record, sorted by started time ascending
          const sorted = [...wipHistory].sort(
            (a, b) => new Date(a.entered_at).getTime() - new Date(b.entered_at).getTime(),
          );
          const rows = sorted.map((h) => {
            const rs = stepMap[h.step_id];
            return {
              sequence: rs?.sequence ?? 0,
              stepName: rs?.name ?? "Unknown",
              started: new Date(h.entered_at).toLocaleString(),
              completed: h.exited_at ? new Date(h.exited_at).toLocaleString() : "—",
              result: "result" in h ? (h.result ?? "") : "",
            };
          });

          // Current step if queued (not yet in history)
          if (step && wip.status === "queued") {
            rows.push({
              sequence: step.sequence,
              stepName: step.name,
              started: "—",
              completed: "—",
              result: "",
            });
          }

          if (rows.length === 0) {
            return <p className="text-sm text-gray-400">No history yet</p>;
          }

          return (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-1 px-2">Seq</th>
                    <th className="py-1 px-2">Step</th>
                    <th className="py-1 px-2">Started</th>
                    <th className="py-1 px-2">Completed</th>
                    <th className="py-1 px-2">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className={`border-b ${r.started === "—" ? "bg-indigo-50" : ""}`}>
                      <td className="py-1 px-2 font-mono">{r.sequence}</td>
                      <td className="py-1 px-2">{r.stepName}</td>
                      <td className="py-1 px-2 text-gray-500">{r.started}</td>
                      <td className="py-1 px-2 text-gray-500">{r.completed}</td>
                      <td className="py-1 px-2">
                        {r.result && (
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            r.result === "pass"
                              ? "bg-green-100 text-green-700"
                              : r.result === "fail" || r.result === "rework"
                                ? "bg-red-100 text-red-700"
                                : "bg-gray-100 text-gray-600"
                          }`}>
                            {r.result}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })()}
      </div>

      {/* Feedback Messages */}
      {error && <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg">{error}</div>}
      {successMsg && <div className="p-3 bg-green-50 text-green-700 text-sm rounded-lg">{successMsg}</div>}

      {/* Actions based on status */}
      {(wip.status === "queued") && (
        <div className="bg-white rounded-lg shadow p-5">
          <h4 className="font-semibold text-gray-700 mb-3">Start Processing</h4>

          {/* Equipment at this step */}
          {stepEquipment.length > 0 && (
            <div className="mb-4">
              <EquipmentStatusTable equipment={stepEquipment} />
              <div className="mt-3">
                <label className="block text-sm text-gray-600 mb-1">Equipment Override</label>
                <select
                  value={equipmentOverride}
                  onChange={(e) => setEquipmentOverride(e.target.value)}
                  className="input-field"
                >
                  <option value="">Auto (dispatch algorithm)</option>
                  {stepEquipment.filter((e) => e.material_setup).map((e) => (
                    <option key={e.equipment_id} value={e.equipment_id}>
                      {e.equipment_code}{e.equipment_name ? ` — ${e.equipment_name}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {(() => {
            // Check if any equipment is available for dispatch, and collect per-machine reasons when not.
            // When "Transition State" is checked, equipment blocked only by an
            // unavailable dispatch state is treated as eligible because the
            // start handler will walk PackML / SEMI E10 forward to Execute.
            const isStateBlockedOnly = (e: StepEquipmentStatus) =>
              e.has_spare_capacity
              && e.material_setup
              && e.dispatch_category !== null
              && e.dispatch_category !== "available";
            const isEligible = (e: StepEquipmentStatus) =>
              (e.dispatch_category === null || e.dispatch_category === "available")
              && e.has_spare_capacity
              && e.material_setup;
            const anyAvailable = stepEquipment.length === 0
              || stepEquipment.some(
                (e) => isEligible(e) || (transitionOnStart && isStateBlockedOnly(e)),
              );

            const reasonsFor = (e: StepEquipmentStatus): string[] => {
              const reasons: string[] = [];
              if (e.dispatch_category && e.dispatch_category !== "available") {
                const fixable = transitionOnStart && isStateBlockedOnly(e);
                reasons.push(
                  `dispatch state "${e.dispatch_category}"${e.state ? ` (${e.state})` : ""}`
                  + (fixable ? " — will transition to Execute on Start" : ""),
                );
              }
              if (!e.has_spare_capacity) {
                const cap = e.max_queue_depth != null ? `${e.queue_depth}/${e.max_queue_depth}` : `${e.queue_depth}`;
                reasons.push(`queue full (${cap})`);
              }
              if (!e.material_setup) {
                reasons.push("not set up for this material");
              }
              return reasons;
            };

            return (
              <>
                <div className="flex items-center gap-3">
                  <button onClick={handleStart} disabled={actionLoading || !anyAvailable} className="btn-primary">
                    Start
                  </button>
                  <label className="flex items-center gap-1.5 text-sm text-gray-700" title="If checked, transition the assigned equipment's PackML / SEMI E10 state to running">
                    <input
                      type="checkbox"
                      checked={transitionOnStart}
                      onChange={(e) => setTransitionOnStart(e.target.checked)}
                    />
                    Transition State
                  </label>
                </div>
                {!anyAvailable && (
                  <div className="mt-2 text-sm text-red-600">
                    {stepEquipment.length === 0 ? (
                      <p>No equipment is configured for this step.</p>
                    ) : (
                      <>
                        <p>No equipment can accept this unit:</p>
                        <ul className="list-disc list-inside mt-1 space-y-0.5">
                          {stepEquipment.map((e) => {
                            const reasons = reasonsFor(e);
                            return (
                              <li key={e.equipment_id}>
                                <span className="font-mono">{e.equipment_code}</span>
                                {": "}
                                {reasons.length > 0 ? reasons.join("; ") : "blocked"}
                              </li>
                            );
                          })}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </>
            );
          })()}
        </div>
      )}

      {wip.status === "in_process" && (
        <>
          {/* Equipment at this step */}
          {stepEquipment.length > 0 && (
            <div className="bg-white rounded-lg shadow p-5">
              <h4 className="font-semibold text-gray-700 mb-3">Equipment at Step</h4>
              <EquipmentStatusTable equipment={stepEquipment} />
            </div>
          )}

          {/* Data Collection */}
          {data_definitions.length > 0 && (
            <div className="bg-white rounded-lg shadow p-5">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-gray-700">Data Collection</h4>
                <button
                  onClick={handleSaveData}
                  disabled={actionLoading}
                  className="px-3 py-1 text-xs rounded-md font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
                  title="Save entered data values without completing the WIP"
                >
                  {actionLoading ? "Saving…" : "Save"}
                </button>
              </div>
              <div className="space-y-3">
                {data_definitions.map((dd) => (
                  <div key={dd.id} className="flex items-end gap-3">
                    <div className="flex-1">
                      <label className="block text-sm text-gray-600 mb-1">
                        {dd.name}
                        {dd.is_required && <span className="text-red-500 ml-1">*</span>}
                        {dd.uom_symbol && <span className="text-gray-400 ml-1">({dd.uom_symbol})</span>}
                      </label>
                      {dd.data_type === "boolean" ? (
                        <select
                          value={dataValues[dd.id] ?? ""}
                          onChange={(e) => setDataValues({ ...dataValues, [dd.id]: e.target.value })}
                          className="input-field"
                        >
                          <option value="">—</option>
                          <option value="true">True</option>
                          <option value="false">False</option>
                        </select>
                      ) : dd.data_type === "enum" && dd.enum_values ? (
                        <select
                          value={dataValues[dd.id] ?? ""}
                          onChange={(e) => setDataValues({ ...dataValues, [dd.id]: e.target.value })}
                          className="input-field"
                        >
                          <option value="">—</option>
                          {dd.enum_values.split(",").map((v) => (
                            <option key={v.trim()} value={v.trim()}>{v.trim()}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={dd.data_type === "numeric" ? "number" : "text"}
                          value={dataValues[dd.id] ?? ""}
                          onChange={(e) => setDataValues({ ...dataValues, [dd.id]: e.target.value })}
                          className="input-field"
                          placeholder={
                            dd.lower_limit != null && dd.upper_limit != null
                              ? `${dd.lower_limit} – ${dd.upper_limit}`
                              : ""
                          }
                        />
                      )}
                    </div>
                    {dd.lower_limit != null && dd.upper_limit != null && (
                      <span className="text-xs text-gray-400 pb-2">
                        Spec: {dd.lower_limit}–{dd.upper_limit}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step Parameters */}
          {step_parameters.length > 0 && (
            <div className="bg-white rounded-lg shadow p-5">
              <h4 className="font-semibold text-gray-700 mb-3">Step Parameters</h4>
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-1 px-2">Parameter</th>
                    <th className="py-1 px-2">Target</th>
                    <th className="py-1 px-2">Lower</th>
                    <th className="py-1 px-2">Upper</th>
                    <th className="py-1 px-2">UoM</th>
                    <th className="py-1 px-2">Actual</th>
                  </tr>
                </thead>
                <tbody>
                  {step_parameters.map((p) => {
                    const actual = paramValues[p.id] ?? "";
                    const numVal = actual !== "" && p.data_type === "numeric" ? parseFloat(actual) : null;
                    const outOfSpec = numVal !== null && (
                      (p.lower_limit != null && numVal < Number(p.lower_limit)) ||
                      (p.upper_limit != null && numVal > Number(p.upper_limit))
                    );
                    return (
                      <tr key={p.id} className="border-b">
                        <td className="py-1 px-2">
                          {p.name}
                          {p.is_required && <span className="text-red-500 ml-1">*</span>}
                        </td>
                        <td className="py-1 px-2 font-mono">{p.target_value ?? "—"}</td>
                        <td className="py-1 px-2 font-mono">{p.lower_limit ?? "—"}</td>
                        <td className="py-1 px-2 font-mono">{p.upper_limit ?? "—"}</td>
                        <td className="py-1 px-2">{p.uom_symbol ?? "—"}</td>
                        <td className="py-1 px-2">
                          {p.data_type === "boolean" ? (
                            <select
                              value={actual}
                              onChange={(e) => setParamValues((prev) => ({ ...prev, [p.id]: e.target.value }))}
                              disabled={wip.status !== "in_process"}
                              className="border rounded px-1.5 py-0.5 text-xs w-24"
                            >
                              <option value="">—</option>
                              <option value="true">True</option>
                              <option value="false">False</option>
                            </select>
                          ) : (
                            <input
                              type={p.data_type === "numeric" ? "number" : "text"}
                              step="any"
                              value={actual}
                              onChange={(e) => setParamValues((prev) => ({ ...prev, [p.id]: e.target.value }))}
                              disabled={wip.status !== "in_process"}
                              placeholder="Enter value"
                              className={`border rounded px-1.5 py-0.5 text-xs w-28 ${outOfSpec ? "border-red-400 bg-red-50" : ""}`}
                            />
                          )}
                          {outOfSpec && (
                            <span className="block text-xs text-red-500 mt-0.5">Out of spec</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Material Consumption */}
          {bomItems.length > 0 && (
          <div className="bg-white rounded-lg shadow p-5">
            <h4 className="font-semibold text-gray-700 mb-3">Material Consumption</h4>

            <table className="min-w-full text-sm mb-4">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-1 px-2">Material</th>
                  <th className="py-1 px-2">Required</th>
                  <th className="py-1 px-2">UOM</th>
                  <th className="py-1 px-2">Consumed</th>
                  <th className="py-1 px-2 min-w-[180px]">Material Lot</th>
                  <th className="py-1 px-2 w-28">Qty</th>
                  <th className="py-1 px-2"></th>
                </tr>
              </thead>
              <tbody>
                {bomItems.map((bi) => {
                  // Find the material_id for this BOM item's material_code
                  const mat = materials.find((m) => m.code === bi.material_code);
                  const matId = mat?.id;
                  // Filter lots to only those matching this material
                  const matchingLots = matId
                    ? materialLots.filter((ml) => ml.material_id === matId)
                    : [];
                  // Sum consumed quantity for this material at this step
                  const matchingLotIds = new Set(matchingLots.map((ml) => ml.id));
                  const totalConsumed = consumedMaterials
                    .filter((c) => matchingLotIds.has(c.material_lot_id))
                    .reduce((sum, c) => sum + c.quantity_consumed, 0);
                  const selectedLotId = lotSelections[bi.id] ?? "";
                  const qtyVal = qtyInputs[bi.id] ?? "";
                  return (
                    <tr key={bi.id} className="border-b">
                      <td className="py-2 px-2 font-mono font-medium">{bi.material_code}</td>
                      <td className="py-2 px-2 font-mono">{bi.quantity}</td>
                      <td className="py-2 px-2">{bi.uom_symbol}</td>
                      <td className={`py-2 px-2 font-mono ${totalConsumed >= bi.quantity ? "text-green-600" : "text-gray-500"}`}>
                        {totalConsumed > 0 ? totalConsumed : "—"}
                      </td>
                      <td className="py-2 px-2">
                        <select
                          value={selectedLotId}
                          onChange={(e) => setLotSelections({ ...lotSelections, [bi.id]: e.target.value })}
                          className="input-field text-sm"
                        >
                          <option value="">Select lot…</option>
                          {matchingLots.map((ml) => (
                            <option key={ml.id} value={ml.id}>
                              {ml.lot_number} (avail: {ml.quantity_on_hand})
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          min="0"
                          step="any"
                          value={qtyVal}
                          onChange={(e) => setQtyInputs({ ...qtyInputs, [bi.id]: e.target.value })}
                          placeholder={String(bi.quantity)}
                          className="input-field text-sm w-full"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <button
                          onClick={() => handleConsumeLine(bi)}
                          disabled={consumeLoading === bi.id || !selectedLotId || !qtyVal || parseFloat(qtyVal) <= 0}
                          className="bg-amber-600 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-amber-700 disabled:opacity-50 whitespace-nowrap"
                        >
                          {consumeLoading === bi.id ? "…" : "Consume"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Consumption history */}
            {consumedMaterials.length > 0 && (
              <div className="mt-3 pt-3 border-t">
                <p className="text-sm text-gray-500 mb-2">Consumption Log:</p>
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-gray-500">
                      <th className="py-1 px-2">Material Lot</th>
                      <th className="py-1 px-2">Qty</th>
                      <th className="py-1 px-2">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {consumedMaterials.map((c) => {
                      const lot = materialLots.find((ml) => ml.id === c.material_lot_id);
                      return (
                        <tr key={c.id} className="border-b">
                          <td className="py-1 px-2 font-mono">{lot?.lot_number ?? c.material_lot_id.slice(0, 8)}</td>
                          <td className="py-1 px-2 font-mono">{c.quantity_consumed}</td>
                          <td className="py-1 px-2 text-gray-500">{new Date(c.consumed_at).toLocaleString()}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          )}

          {/* Complete Step */}
          <div className="bg-white rounded-lg shadow p-5">
            <h4 className="font-semibold text-gray-700 mb-3">Complete Step</h4>
            <div className="flex items-end gap-4 flex-wrap">
              {(outgoing_conditions ?? []).some((c) => c === "on_pass" || c === "on_fail" || c === "on_rework") && (
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Result</label>
                  <select
                    value={completeResult}
                    onChange={(e) => setCompleteResult(e.target.value as "pass" | "fail" | "rework")}
                    className="input-field"
                  >
                    {(outgoing_conditions ?? []).includes("on_pass") && <option value="pass">Pass</option>}
                    {(outgoing_conditions ?? []).includes("on_fail") && <option value="fail">Fail</option>}
                    {(outgoing_conditions ?? []).includes("on_rework") && <option value="rework">Rework</option>}
                  </select>
                </div>
              )}
              {dispositions.length > 1 && (
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Disposition</label>
                  <select
                    value={selectedDisposition}
                    onChange={(e) => setSelectedDisposition(e.target.value)}
                    className="input-field"
                  >
                    {dispositions.map((d) => {
                      const destStep = d.to_step_id ? stepNameById[d.to_step_id] : undefined;
                      const destLabel = destStep ? ` → ${destStep}` : " → (terminal)";
                      const descLabel = d.description ? ` — ${d.description}` : "";
                      return (
                        <option key={d.id} value={d.name} title={d.description || undefined}>
                          {d.name}{destLabel}{descLabel}
                        </option>
                      );
                    })}
                  </select>
                </div>
              )}
              {!isUnit && (
                <>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Qty Out{(wip as Lot).uom_symbol ? ` (${(wip as Lot).uom_symbol})` : ""}</label>
                    <input
                      type="number"
                      min="0"
                      value={qtyOut}
                      onChange={(e) => setQtyOut(e.target.value)}
                      placeholder={String((wip as Lot).quantity)}
                      className="input-field w-24"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Qty Scrapped{(wip as Lot).uom_symbol ? ` (${(wip as Lot).uom_symbol})` : ""}</label>
                    <input
                      type="number"
                      min="0"
                      value={qtyScrapped}
                      onChange={(e) => setQtyScrapped(e.target.value)}
                      className="input-field w-24"
                    />
                  </div>
                </>
              )}
              <button onClick={handleComplete} disabled={actionLoading} className="btn-primary">
                Complete
              </button>
              <label className="flex items-center gap-1.5 text-sm text-gray-700" title="If checked, transition the assigned equipment's PackML / SEMI E10 state back to idle">
                <input
                  type="checkbox"
                  checked={transitionOnComplete}
                  onChange={(e) => setTransitionOnComplete(e.target.checked)}
                />
                Transition State
              </label>
            </div>
          </div>
        </>
      )}

      {/* Hold / Release Hold */}
      {wip.status === "on_hold" && (
        <div className="bg-white rounded-lg shadow p-5">
          <h4 className="font-semibold text-gray-700 mb-1">On Hold</h4>
          {wip.hold_reason && (
            <p className="text-sm text-gray-500 mb-3">Reason: {wip.hold_reason}</p>
          )}
          <div className="flex gap-2 items-center">
            <select
              value={releaseReason}
              onChange={(e) => setReleaseReason(e.target.value)}
              className="input-field flex-1"
            >
              <option value="">— Select release disposition —</option>
              {releaseDispositions.map((d) => (
                <option key={d.id} value={d.name}>
                  {d.name}{d.description ? ` — ${d.description}` : ""}
                </option>
              ))}
            </select>
            <button
              onClick={handleReleaseHold}
              disabled={actionLoading || !releaseReason}
              className="btn-primary disabled:opacity-50"
            >
              Release Hold
            </button>
          </div>
        </div>
      )}

      {wip.status !== "completed" && wip.status !== "scrapped" && wip.status !== "on_hold" && (
        <div className="bg-white rounded-lg shadow p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Hold */}
          <div>
            <h4 className="font-semibold text-gray-700 mb-2">Place on Hold</h4>
            <div className="flex gap-2">
              <select
                value={holdReason}
                onChange={(e) => setHoldReason(e.target.value)}
                className="input-field flex-1"
              >
                <option value="">— Select reason —</option>
                {holdDispositions.map((d) => (
                  <option key={d.id} value={d.name}>
                    {d.name}{d.description ? ` — ${d.description}` : ""}
                  </option>
                ))}
              </select>
              <button
                onClick={handleHold}
                disabled={actionLoading || !holdReason}
                className="bg-yellow-500 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-yellow-600 disabled:opacity-50"
              >
                Hold
              </button>
            </div>
          </div>

          {/* Scrap */}
          <div>
            <h4 className="font-semibold text-gray-700 mb-2">Scrap</h4>
            <div className="flex gap-2">
              <select
                value={scrapReason}
                onChange={(e) => setScrapReason(e.target.value)}
                className="input-field flex-1"
              >
                <option value="">— Select reason —</option>
                {scrapDispositions.map((d) => (
                  <option key={d.id} value={d.name}>
                    {d.name}{d.description ? ` — ${d.description}` : ""}
                  </option>
                ))}
              </select>
              <button
                onClick={handleScrap}
                disabled={actionLoading || !scrapReason}
                className="bg-red-500 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-red-600 disabled:opacity-50"
              >
                Scrap
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Completed/Scrapped terminal states */}
      {(wip.status === "completed" || wip.status === "scrapped") && (
        <div className="bg-white rounded-lg shadow p-5 text-center">
          <p className="text-lg font-semibold text-gray-500">
            {wip.status === "completed" ? "✅ All steps completed" : "❌ Scrapped"}
          </p>
        </div>
      )}
    </div>
  );
}

function EquipmentStatusTable({ equipment }: { equipment: StepEquipmentStatus[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="py-1 px-2">Equipment</th>
            <th className="py-1 px-2">Availability</th>
            <th className="py-1 px-2">State</th>
            <th className="py-1 px-2">Queue</th>
            <th className="py-1 px-2">Capacity</th>
            <th className="py-1 px-2">Material</th>
          </tr>
        </thead>
        <tbody>
          {equipment.map((e) => {
            // Dispatch blocking conditions
            const categoryBlocked = e.dispatch_category != null && e.dispatch_category !== "available";
            const capacityBlocked = !e.has_spare_capacity;
            const materialBlocked = !e.material_setup;
            const blocked = categoryBlocked || capacityBlocked || materialBlocked;
            return (
            <tr key={e.equipment_id} className={`border-b ${e.is_assigned ? "bg-indigo-50 font-semibold" : ""}`}>
              <td className="py-1 px-2 font-mono">
                {e.equipment_code}
                {e.is_assigned && <span className="ml-1 text-xs text-indigo-600">(assigned)</span>}
                {blocked && <span className="ml-1 text-xs text-red-500" title="Dispatch blocked">⊘</span>}
              </td>
              <td className={`py-1 px-2 ${categoryBlocked ? "bg-red-100" : ""}`}>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  e.dispatch_category === "available"
                    ? "bg-green-100 text-green-700"
                    : categoryBlocked
                      ? "bg-red-200 text-red-800"
                      : "bg-gray-100 text-gray-600"
                }`}>
                  {e.dispatch_category ?? "no model"}
                </span>
              </td>
              <td className="py-1 px-2">
                {e.state ? `${e.state}` : "—"}
                {e.state_model && <span className="text-xs text-gray-400 ml-1">({e.state_model})</span>}
              </td>
              <td className={`py-1 px-2 font-mono ${capacityBlocked ? "bg-red-100" : ""}`}>
                {e.queue_depth}{e.max_queue_depth != null ? ` / ${e.max_queue_depth}` : ""}
              </td>
              <td className={`py-1 px-2 ${capacityBlocked ? "bg-red-100" : ""}`}>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  e.has_spare_capacity
                    ? "bg-green-100 text-green-700"
                    : "bg-red-200 text-red-800"
                }`}>
                  {e.has_spare_capacity ? "Yes" : "Full"}
                </span>
              </td>
              <td className={`py-1 px-2 ${materialBlocked ? "bg-red-100" : ""}`}>
                {e.material_setup
                  ? <span className="text-green-600">✓</span>
                  : <span className="text-red-700 font-medium">✗</span>
                }
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function WipStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-blue-100 text-blue-700",
    in_process: "bg-yellow-100 text-yellow-700",
    completed: "bg-green-100 text-green-700",
    scrapped: "bg-red-100 text-red-700",
    on_hold: "bg-orange-100 text-orange-700",
  };
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {status.replace("_", " ")}
    </span>
  );
}
