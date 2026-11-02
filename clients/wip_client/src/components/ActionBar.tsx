import { useEffect, useRef, useState, type MutableRefObject } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { StepContext } from "../types";
import {
  apiErrorMessage,
  completeLot,
  completeUnit,
  fetchTransferInfo,
  moveLot,
  moveUnit,
  scrapUnit,
  startLot,
  startUnit,
  transferToInventory,
} from "../api/wip";

export type CompleteResult = "pass" | "fail" | "rework";

interface Props {
  context: StepContext;
  equipmentOverride: string;
  completeResult: CompleteResult;
  onCompleteResultChange: (value: CompleteResult) => void;
  selectedDisposition: string;
  onSelectDispositionChange: (value: string) => void;
  /** Data Collection entries (raw text); hydrated from server on scan. */
  dataValues: Record<string, string>;
  savedValues: Record<string, string>;
  paramValues: Record<string, string>;
  /** Step-parameter actuals persisted on the server (hydrated on scan). */
  savedParamValues: Record<string, string>;
  /** Clears entry state for the next step (§6.8 step 5). */
  onAfterComplete: () => void;
  /** Re-fetches the step context after an action. */
  refreshContext: () => Promise<void>;
  /** Called when the user clicks the Complete button — opens the modal in App. */
  onRequestComplete: () => void;
  /**
   * App-owned ref that ActionBar populates with its complete handler, so the
   * Complete modal's Confirm button can invoke the transaction with the
   * confirmed values directly (no reliance on committed React state).
   */
  confirmCompleteRef: MutableRefObject<
    ((disposition: string, qtyScrapped: string, scrapReason: string, shouldScrapUnit: boolean) => void) | null
  >;
}

export default function ActionBar({
  context,
  equipmentOverride,
  completeResult,
  onCompleteResultChange,
  selectedDisposition,
  onSelectDispositionChange,
  dataValues,
  savedValues,
  paramValues,
  savedParamValues,
  onAfterComplete,
  refreshContext,
  onRequestComplete,
  confirmCompleteRef,
}: Props) {
  const queryClient = useQueryClient();
  const { wip, wip_type, step, step_parameters, dispositions } = context;
  const isUnit = wip_type === "unit";
  const outgoing = context.outgoing_conditions ?? [];

  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const loading = actionLoading;

  // Derived (recomputed every render, so it updates the instant a Save lands):
  // the list of required step-parameter / data-collection names with no value.
  // This drives the "required value(s) missing" warning directly so it clears
  // itself once everything is satisfied — no stale error state to reset.
  const missingRequiredNames = (() => {
    const missing = step_parameters
      .filter(
        (p) =>
          p.is_required &&
          (paramValues[p.id] ?? "").trim() === "" &&
          (savedParamValues[p.id] ?? "").trim() === "",
      )
      .map((p) => p.name);
    const missingData = context.data_definitions
      .filter(
        (d) =>
          d.is_required &&
          (savedValues[d.id] ?? "").trim() === "" &&
          (dataValues[d.id] ?? "").trim() === "",
      )
      .map((d) => d.name);
    return [...new Set([...missing, ...missingData])];
  })();
  const hasMissing = missingRequiredNames.length > 0;

  // Auto-select when the step exposes exactly one disposition and no
  // result-based transitions (mirrors run_time behavior).
  useEffect(() => {
    const hasResultRouting =
      outgoing.includes("on_pass") ||
      outgoing.includes("on_fail") ||
      outgoing.includes("on_rework");
    if (dispositions.length === 1 && !hasResultRouting) {
      const name = dispositions[0].name ?? dispositions[0].label ?? "";
      if (name && selectedDisposition !== name) onSelectDispositionChange(name);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispositions, outgoing]);

  /** Shared wrapper: in-flight gating, banners, invalidate + refresh. */
  const runAction = async (
    fn: () => Promise<void>,
    msg: string,
    after?: () => void,
  ) => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await fn();
      setSuccessMsg(msg);
      await queryClient.invalidateQueries({ queryKey: ["step-equipment"] });
      await refreshContext();
      after?.();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = () =>
    runAction(async () => {
      if (isUnit) await startUnit(wip.id, equipmentOverride || undefined);
      else await startLot(wip.id, equipmentOverride || undefined);
    }, "Started processing");

  // Transfer to inventory: offered when the step the WIP last completed
  // defines a transfer location (configured in the route step editor).
  const isCompleted = wip.status === "completed";
  const { data: transferInfo } = useQuery({
    queryKey: ["transfer-info", wip_type, wip.id, wip.status, wip.current_step_id],
    queryFn: () => fetchTransferInfo(wip_type, wip.id),
    enabled: wip.status === "queued" || isCompleted,
  });
  const canTransfer = !!transferInfo?.available;

  const handleTransfer = () => {
    let msg = "Transferred to inventory";
    return runAction(
      async () => {
        const result = await transferToInventory(wip_type, wip.id);
        msg = `Transferred ${result.lot_number} to ${transferInfo?.location_code ?? "inventory"}`;
        await queryClient.invalidateQueries({ queryKey: ["transfer-info"] });
      },
      msg,
      () => setSuccessMsg(msg),
    );
  };

  /**
   * Runs the complete transaction.
   * qtyScrapped is passed explicitly so the modal can pre-populate its
   * default (0) before the user confirms. quantity_out is left for the
   * server to derive as (current quantity - qtyScrapped).
   */
  // Guards against the complete transaction running twice (e.g. a double
  // click on the modal's Confirm). A ref is set synchronously at entry, so the
  // second invocation is dropped before the async work begins.
  const completeRunning = useRef(false);

  /**
   * Runs the complete transaction with the modal's confirmed values, passed
   * explicitly so we never read stale `qtyScrapped`/`scrapReason`/
   * `selectedDisposition` state from a closure.
   */
  const runComplete = (
    qtyScrappedNum: number,
    disp: string,
    scrapReasonText: string,
    shouldScrapUnit: boolean,
  ) => {
    if (completeRunning.current) return;
    // Client-side guard: block Complete while any required value is missing.
    // The live derived warning (rendered above) already names them, so here we
    // simply refuse to run — no imperative error state to leave stale.
    if (hasMissing) return;

    completeRunning.current = true;
    return runAction(
      async () => {
        // Snapshot: saved DC codes → parsed values, plus non-empty parameter
        //    actuals keyed by parameter name (§6.8 step 2).
        const snapshot: Record<string, unknown> = {};
        for (const dd of context.data_definitions) {
          const raw = ((savedValues[dd.id] ?? "") || (dataValues[dd.id] ?? "")).trim();
          if (raw === "") continue;
          snapshot[dd.code] =
            dd.data_type === "numeric"
              ? Number(raw)
              : dd.data_type === "boolean"
                ? raw === "true"
                : raw;
        }
        for (const p of step_parameters) {
          const raw = ((savedParamValues[p.id] ?? "") || (paramValues[p.id] ?? "")).trim();
          if (raw === "") continue;
          snapshot[p.name] =
            p.data_type === "numeric" ? Number(raw) : raw;
        }
        const snap = Object.keys(snapshot).length > 0 ? snapshot : undefined;

        // 3–4. Complete, then move along the route.
        const disposition = disp || undefined;
        const moveOpts: { result?: string; disposition?: string } = {
          result: completeResult,
        };
        if (disposition) moveOpts.disposition = disposition;

        if (isUnit) {
          if (shouldScrapUnit) {
            await scrapUnit(wip.id, scrapReasonText, disposition);
            return;
          }
          await completeUnit(wip.id, completeResult, snap, disposition);
          await moveUnit(wip.id, moveOpts);
        } else {
          await completeLot(
            wip.id,
            qtyScrappedNum || 0,
            disposition,
            snap,
            scrapReasonText || undefined,
          );
          await moveLot(wip.id, moveOpts);
        }
      },
      shouldScrapUnit ? "Unit scrapped" : "Step completed",
      // 5. Clear entry state for the next step.
      onAfterComplete,
    )?.finally(() => {
      completeRunning.current = false;
    });
  };

  // Expose the complete handler to App's Complete modal via the provided ref.
  // The modal calls this with its confirmed values directly, so the
  // transaction never reads stale `qtyScrapped`/`scrapReason` state from a
  // closure (the modal keeps those in its own local state until Confirm).
  useEffect(() => {
    confirmCompleteRef.current = (
      disposition: string,
      qtyScrappedStr: string,
      scrapReasonText: string,
      shouldScrapUnit: boolean,
    ) => {
      onSelectDispositionChange(disposition);
      runComplete(Number(qtyScrappedStr) || 0, disposition, scrapReasonText, shouldScrapUnit);
    };
    return () => {
      confirmCompleteRef.current = null;
    };
  });

  // Result select only when outgoing conditions include result routing.
  const resultOptions = [
    { value: "pass", label: "Pass", cond: "on_pass" },
    { value: "fail", label: "Fail", cond: "on_fail" },
    { value: "rework", label: "Rework", cond: "on_rework" },
  ].filter((o) => outgoing.includes(o.cond));

  if (!step && wip.status !== "queued" && !isCompleted) return null;

  return (
    <div className="bg-white rounded-lg shadow-md p-4 space-y-3">
      {/* Complete options row */}
      {wip.status === "in_process" && (
        <div className="flex items-end gap-3 flex-wrap">
          {resultOptions.length > 0 && (
            <div>
              <label
                htmlFor="complete-result"
                className="block text-xs uppercase tracking-wide text-gray-400 mb-1"
              >
                Result
              </label>
              <select
                id="complete-result"
                value={completeResult}
                onChange={(e) =>
                  onCompleteResultChange(e.target.value as CompleteResult)
                }
                className="input-field w-auto"
              >
                {resultOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          )}

        </div>
      )}

      {/* Live required-values warning — derived from current props, so it
          updates the instant a Save lands (no stale error state). */}
      {wip.status === "in_process" && hasMissing && (
        <div role="alert" className="p-3 bg-amber-50 text-amber-800 text-sm rounded-md">
          Required value(s) missing: {missingRequiredNames.join(", ")}
        </div>
      )}
      {wip.status === "in_process" && !hasMissing && !error && !successMsg && (
        <div role="status" className="p-3 bg-green-50 text-green-700 text-sm rounded-md">
          All required values saved — ready to complete.
        </div>
      )}

      {error && (
        <div role="alert" className="p-3 bg-red-50 text-red-700 text-sm rounded-md">
          {error}
        </div>
      )}
      {successMsg && !error && (
        <div role="status" className="p-3 bg-green-50 text-green-700 text-sm rounded-md">
          {successMsg}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleStart}
          disabled={loading || wip.status !== "queued"}
          className="btn-primary"
        >
          {loading ? "Working…" : "Start"}
        </button>
        <button
          onClick={onRequestComplete}
          disabled={loading || wip.status !== "in_process"}
          className="btn-success"
        >
          {loading ? "Working…" : "Complete"}
        </button>
        {canTransfer && (
          <button
            onClick={handleTransfer}
            disabled={loading}
            className="btn-primary"
          >
            {loading ? "Working…" : "Transfer"}
          </button>
        )}
        <span className="text-xs text-gray-400">
          {wip.status === "completed" && "WIP is completed."}
          {wip.status === "finished" && "WIP is finished and in inventory."}
          {wip.status === "scrapped" && "WIP is scrapped."}
          {wip.status === "on_hold" && "WIP is on hold."}
        </span>
      </div>
    </div>
  );
}

