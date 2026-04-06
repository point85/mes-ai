import { useState } from "react";
import type { StepContext, Unit, Lot, DataDefinition } from "../types";
import {
  startUnit, completeUnit, moveUnit, holdUnit, releaseHoldUnit, scrapUnit,
  startLot, completeLot, moveLot, holdLot, releaseHoldLot, scrapLot,
  collectDataBatch, recordQualityResult,
} from "../api/runtime";
import RouteProgressBar from "./RouteProgressBar";

interface Props {
  context: StepContext;
  onRefresh: () => Promise<void>;
}

export default function StepProcessingPanel({ context, onRefresh }: Props) {
  const { wip_type, wip, step, step_parameters, data_definitions, quality_tests, dispositions, route_steps } = context;
  const isUnit = wip_type === "unit";
  const identifier = isUnit ? (wip as Unit).serial_number : (wip as Lot).lot_number;

  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Data collection form state
  const [dataValues, setDataValues] = useState<Record<string, string>>({});

  // Quality test results
  const [testResults, setTestResults] = useState<Record<string, "pass" | "fail">>({});

  // Hold/scrap reason
  const [holdReason, setHoldReason] = useState("");
  const [scrapReason, setScrapReason] = useState("");

  // Lot completion quantities
  const [qtyOut, setQtyOut] = useState<string>("");
  const [qtyScrapped, setQtyScrapped] = useState("0");

  // Disposition
  const [selectedDisposition, setSelectedDisposition] = useState("");

  // Complete result
  const [completeResult, setCompleteResult] = useState<"pass" | "fail" | "rework">("pass");

  const runAction = async (fn: () => Promise<unknown>, msg: string) => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await fn();
      setSuccessMsg(msg);
      await onRefresh();
    } catch (err: unknown) {
      const m = (err as { response?: { data?: { message?: string } } })?.response?.data?.message ?? "Action failed";
      setError(m);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = () =>
    runAction(
      () => isUnit ? startUnit(wip.id) : startLot(wip.id),
      "Started processing",
    );

  const handleComplete = async () => {
    // Collect data points if any
    if (data_definitions.length > 0) {
      const items = data_definitions.map((dd: DataDefinition) => {
        const val = dataValues[dd.id] ?? "";
        const base: Record<string, unknown> = {
          definition_id: dd.id,
          ...(isUnit ? { unit_id: wip.id } : { lot_id: wip.id }),
        };
        if (dd.data_type === "numeric") base.value_numeric = val ? parseFloat(val) : undefined;
        else if (dd.data_type === "boolean") base.value_boolean = val === "true";
        else base.value_string = val || undefined;
        return base as Parameters<typeof collectDataBatch>[0][number];
      }).filter((item) => {
        // Only submit items that have a value
        return item.value_numeric !== undefined || item.value_string !== undefined || item.value_boolean !== undefined;
      });
      if (items.length > 0) {
        await collectDataBatch(items);
      }
    }

    // Record quality test results
    for (const qt of quality_tests) {
      const result = testResults[qt.id];
      if (result) {
        await recordQualityResult({
          test_id: qt.id,
          ...(isUnit ? { unit_id: wip.id } : { lot_id: wip.id }),
          result,
          tested_at: new Date().toISOString(),
        });
      }
    }

    // Build data snapshot from collected values
    const snapshot: Record<string, unknown> = {};
    for (const dd of data_definitions) {
      const val = dataValues[dd.id];
      if (val !== undefined && val !== "") snapshot[dd.code] = dd.data_type === "numeric" ? parseFloat(val) : val;
    }

    await runAction(
      () => {
        if (isUnit) {
          return completeUnit(wip.id, completeResult, Object.keys(snapshot).length > 0 ? snapshot : undefined);
        } else {
          return completeLot(wip.id, qtyOut ? parseInt(qtyOut) : undefined, parseInt(qtyScrapped) || 0);
        }
      },
      "Step completed",
    );
  };

  const handleMove = () => {
    const opts: { disposition?: string; result?: string } = {};
    if (selectedDisposition) opts.disposition = selectedDisposition;
    opts.result = completeResult;
    runAction(
      () => isUnit ? moveUnit(wip.id, opts) : moveLot(wip.id, opts),
      "Moved to next step",
    );
  };

  const handleHold = () =>
    runAction(
      () => isUnit ? holdUnit(wip.id, holdReason) : holdLot(wip.id, holdReason),
      "Placed on hold",
    );

  const handleReleaseHold = () =>
    runAction(
      () => isUnit ? releaseHoldUnit(wip.id) : releaseHoldLot(wip.id),
      "Released from hold",
    );

  const handleScrap = () =>
    runAction(
      () => isUnit ? scrapUnit(wip.id, scrapReason) : scrapLot(wip.id, scrapReason),
      "Scrapped",
    );

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
        {!isUnit && <p className="text-sm text-gray-500 mt-1">Quantity: {(wip as Lot).quantity}</p>}
        {step && (
          <div className="mt-3 p-3 bg-indigo-50 rounded-md">
            <p className="text-sm text-indigo-800">
              <span className="font-semibold">Current Step:</span> {step.name}
              <span className="text-indigo-500 ml-2">({step.step_type}, seq {step.sequence})</span>
            </p>
          </div>
        )}
        {!step && wip.status !== "completed" && wip.status !== "scrapped" && (
          <p className="mt-3 text-sm text-gray-400">No current step assigned</p>
        )}
      </div>

      {/* Route Progress */}
      {route_steps.length > 0 && (
        <RouteProgressBar steps={route_steps} currentStepId={wip.current_step_id} />
      )}

      {/* Feedback Messages */}
      {error && <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg">{error}</div>}
      {successMsg && <div className="p-3 bg-green-50 text-green-700 text-sm rounded-lg">{successMsg}</div>}

      {/* Actions based on status */}
      {(wip.status === "queued") && (
        <div className="bg-white rounded-lg shadow p-5">
          <h4 className="font-semibold text-gray-700 mb-3">Start Processing</h4>
          <button onClick={handleStart} disabled={actionLoading} className="btn-primary">
            Start
          </button>
        </div>
      )}

      {wip.status === "in_process" && (
        <>
          {/* Data Collection */}
          {data_definitions.length > 0 && (
            <div className="bg-white rounded-lg shadow p-5">
              <h4 className="font-semibold text-gray-700 mb-3">Data Collection</h4>
              <div className="space-y-3">
                {data_definitions.map((dd) => (
                  <div key={dd.id} className="flex items-end gap-3">
                    <div className="flex-1">
                      <label className="block text-sm text-gray-600 mb-1">
                        {dd.name}
                        {dd.is_required && <span className="text-red-500 ml-1">*</span>}
                        {dd.uom && <span className="text-gray-400 ml-1">({dd.uom})</span>}
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

          {/* Step Parameters (spec limits display) */}
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
                  </tr>
                </thead>
                <tbody>
                  {step_parameters.map((p) => (
                    <tr key={p.id} className="border-b">
                      <td className="py-1 px-2">{p.name}</td>
                      <td className="py-1 px-2 font-mono">{p.target_value ?? "—"}</td>
                      <td className="py-1 px-2 font-mono">{p.lower_limit ?? "—"}</td>
                      <td className="py-1 px-2 font-mono">{p.upper_limit ?? "—"}</td>
                      <td className="py-1 px-2">{p.uom ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Quality Tests */}
          {quality_tests.length > 0 && (
            <div className="bg-white rounded-lg shadow p-5">
              <h4 className="font-semibold text-gray-700 mb-3">Quality Tests</h4>
              <div className="space-y-2">
                {quality_tests.map((qt) => (
                  <div key={qt.id} className="flex items-center justify-between border-b pb-2">
                    <div>
                      <p className="text-sm font-medium">{qt.name}</p>
                      <p className="text-xs text-gray-400">{qt.test_type} · {qt.code}</p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setTestResults({ ...testResults, [qt.id]: "pass" })}
                        className={`px-3 py-1 text-xs rounded-md font-medium ${
                          testResults[qt.id] === "pass"
                            ? "bg-green-600 text-white"
                            : "bg-green-50 text-green-700 hover:bg-green-100"
                        }`}
                      >
                        Pass
                      </button>
                      <button
                        onClick={() => setTestResults({ ...testResults, [qt.id]: "fail" })}
                        className={`px-3 py-1 text-xs rounded-md font-medium ${
                          testResults[qt.id] === "fail"
                            ? "bg-red-600 text-white"
                            : "bg-red-50 text-red-700 hover:bg-red-100"
                        }`}
                      >
                        Fail
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Complete Step */}
          <div className="bg-white rounded-lg shadow p-5">
            <h4 className="font-semibold text-gray-700 mb-3">Complete Step</h4>
            <div className="flex items-end gap-4 flex-wrap">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Result</label>
                <select
                  value={completeResult}
                  onChange={(e) => setCompleteResult(e.target.value as "pass" | "fail" | "rework")}
                  className="input-field"
                >
                  <option value="pass">Pass</option>
                  <option value="fail">Fail</option>
                  <option value="rework">Rework</option>
                </select>
              </div>
              {!isUnit && (
                <>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Qty Out</label>
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
                    <label className="block text-sm text-gray-600 mb-1">Qty Scrapped</label>
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
                Complete Step
              </button>
            </div>
          </div>

          {/* Move / Disposition */}
          <div className="bg-white rounded-lg shadow p-5">
            <h4 className="font-semibold text-gray-700 mb-3">Move to Next Step</h4>
            <div className="flex items-end gap-4 flex-wrap">
              {dispositions.length > 0 && (
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Disposition</label>
                  <select
                    value={selectedDisposition}
                    onChange={(e) => setSelectedDisposition(e.target.value)}
                    className="input-field"
                  >
                    <option value="">Auto (routing engine)</option>
                    {dispositions.map((d) => (
                      <option key={d.to_step_id} value={d.label}>{d.label}</option>
                    ))}
                  </select>
                </div>
              )}
              <button onClick={handleMove} disabled={actionLoading} className="btn-primary">
                Move
              </button>
            </div>
          </div>
        </>
      )}

      {/* Hold / Release Hold */}
      {wip.status === "on_hold" && (
        <div className="bg-white rounded-lg shadow p-5">
          <h4 className="font-semibold text-gray-700 mb-3">On Hold</h4>
          <button onClick={handleReleaseHold} disabled={actionLoading} className="btn-primary">
            Release Hold
          </button>
        </div>
      )}

      {wip.status !== "completed" && wip.status !== "scrapped" && wip.status !== "on_hold" && (
        <div className="bg-white rounded-lg shadow p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Hold */}
          <div>
            <h4 className="font-semibold text-gray-700 mb-2">Place on Hold</h4>
            <div className="flex gap-2">
              <input
                type="text"
                value={holdReason}
                onChange={(e) => setHoldReason(e.target.value)}
                placeholder="Reason…"
                className="input-field flex-1"
              />
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
              <input
                type="text"
                value={scrapReason}
                onChange={(e) => setScrapReason(e.target.value)}
                placeholder="Reason…"
                className="input-field flex-1"
              />
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
