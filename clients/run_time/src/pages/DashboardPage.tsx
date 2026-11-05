import { useMemo, useState, type FormEvent } from "react";
import axios from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowPathIcon, QuestionMarkCircleIcon } from "@heroicons/react/24/outline";
import {
  createDashboardAlertRule,
  deleteDashboardAlertRule,
  fetchDashboardAlerts,
  fetchDashboardAlertRules,
  fetchLineStatus,
  fetchLossBreakdown,
  fetchOrderProgress,
  fetchProductionTrends,
  fetchShiftSummary,
  setDashboardAlertRuleEnabled,
  testDashboardAlertRule,
  updateDashboardAlertRule,
} from "../api/runtime";
import type {
  DashboardAlert,
  DashboardAlertMetric,
  DashboardAlertRule,
  DashboardAlertTestInput,
  DashboardLossBreakdown,
  DashboardTrends,
} from "../types";

const METRICS: { value: DashboardAlertMetric; label: string; defaultThreshold: string }[] = [
  { value: "oee_below", label: "OEE below (%)", defaultThreshold: "60" },
  { value: "scrap_rate_above", label: "Scrap/rework rate above (%)", defaultThreshold: "5" },
  { value: "downtime_minutes_above", label: "Downtime in window above (minutes)", defaultThreshold: "30" },
  { value: "current_downtime_above", label: "Current continuous downtime above (minutes)", defaultThreshold: "30" },
];

const isMinutesMetric = (metric: DashboardAlertMetric) =>
  metric === "downtime_minutes_above" || metric === "current_downtime_above";

function AlertHelp({ onClose }: { onClose: () => void }) {
  return (
    <div role="dialog" aria-label="Alert settings help" className="absolute left-0 top-full z-20 mt-2 w-[28rem] max-w-[90vw] rounded-lg border bg-white p-4 text-sm text-gray-700 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="font-semibold">Alert rule settings</h4>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700" aria-label="Close help">✕</button>
      </div>
      <dl className="space-y-2">
        <div><dt className="font-medium">Rule name</dt><dd className="text-gray-600">Label shown on the alert banner.</dd></div>
        <div><dt className="font-medium">Metric</dt>
          <dd className="text-gray-600">
            <strong>OEE below</strong>: OEE for the window falls under the limit (needs an equipment and recorded counters).{" "}
            <strong>Scrap/rework rate above</strong>: (reject + rework) ÷ total counts exceeds the limit.{" "}
            <strong>Downtime in window above</strong>: total downtime minutes inside the window exceeds the limit; older downtime is not counted.{" "}
            <strong>Current continuous downtime above</strong>: equipment has been in a downtime state, uninterrupted, for longer than the limit, measured from when the state began.
          </dd></div>
        <div><dt className="font-medium">Limit</dt><dd className="text-gray-600">Percent for OEE and scrap rate; minutes for the downtime metrics. The alert fires when the value is beyond the limit.</dd></div>
        <div><dt className="font-medium">Window (minutes)</dt><dd className="text-gray-600">Look-back period for OEE, scrap rate and downtime-in-window. Not used by the current continuous downtime metric.</dd></div>
        <div><dt className="font-medium">Equipment</dt><dd className="text-gray-600">Limit the rule to one machine. Leave as "All equipment" to cover everything (required for OEE).</dd></div>
        <div><dt className="font-medium">Test / Edit</dt><dd className="text-gray-600">Test dry-runs a rule with sample values; Edit changes a saved rule. Alerts are re-evaluated every 30 seconds and clear on their own.</dd></div>
      </dl>
    </div>
  );
}

function CounterHelp({ onClose }: { onClose: () => void }) {
  return (
    <div role="dialog" aria-label="Production counters help" className="absolute left-0 top-full z-20 mt-2 w-96 rounded-lg border bg-white p-4 text-sm text-gray-700 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="font-semibold">Recording production counters</h4>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-700" aria-label="Close help">✕</button>
      </div>
      <p className="mb-2">
        Trends are built from daily production counters (good, reject and rework counts per
        equipment, shift date and order). Without counters, they fall back to counts derived
        from WIP units, and OEE accuracy is limited.
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          <strong>Incremental:</strong> <code>POST /api/v1/performance/counters/increment</code> with
          {" "}<code>equipment_id</code>, <code>good_delta</code>, <code>reject_delta</code>,
          {" "}<code>rework_delta</code> and optional <code>order_id</code> adds to today&apos;s counter.
        </li>
        <li>
          <strong>Absolute:</strong> <code>POST /api/v1/performance/counters</code> upserts totals
          per equipment, date and order.
        </li>
        <li>
          <strong>Automated:</strong> enable the MQTT or PackML/OPC-UA counter plugins to report
          counts from machines.
        </li>
        <li>
          <strong>Testing:</strong> the <code>simulate-mqtt-counts</code>,
          {" "}<code>simulate-stomp-counts</code> and <code>simulate-historian-counts</code> endpoints
          under <code>/performance/equipment/&#123;id&#125;/</code> generate sample counts.
        </li>
      </ul>
      <p className="mt-2 text-xs text-gray-500">
        Set an ideal cycle time on the equipment or counter so OEE performance can be calculated.
        Use Refresh after posting counts.
      </p>
    </div>
  );
}

type Period = "8h" | "24h" | "today" | "7d" | "30d" | "90d";

const PERIODS: { id: Period; label: string }[] = [
  { id: "8h", label: "Last 8 hours" },
  { id: "24h", label: "Last 24 hours" },
  { id: "today", label: "Today (since midnight)" },
  { id: "7d", label: "Last 7 days" },
  { id: "30d", label: "Last 30 days" },
  { id: "90d", label: "Last 90 days" },
];

// Counters use an exact look-back in hours; trends and losses are bucketed by day.
function periodHours(period: Period): number {
  switch (period) {
    case "8h": return 8;
    case "24h": return 24;
    case "7d": return 168;
    case "30d": return 720;
    case "90d": return 2160;
    case "today": {
      const midnight = new Date();
      midnight.setHours(0, 0, 0, 0);
      return Math.max(1, Math.ceil((Date.now() - midnight.getTime()) / 3_600_000));
    }
  }
}

function periodDays(period: Period): number {
  switch (period) {
    case "8h":
    case "today": return 1;
    case "24h": return 2;
    case "7d": return 7;
    case "30d": return 30;
    case "90d": return 90;
  }
}

type SubTab = "trends" | "losses" | "alerts";

const SUB_TABS: { id: SubTab; label: string }[] = [
  { id: "trends", label: "Production trends" },
  { id: "losses", label: "Loss drill-down" },
  { id: "alerts", label: "Configurable alerts" },
];

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [subTab, setSubTab] = useState<SubTab>("trends");
  const isLoss = subTab === "losses";
  const [testRule, setTestRule] = useState<DashboardAlertRule | null>(null);
  const [showCounterHelp, setShowCounterHelp] = useState(false);
  const [showAlertHelp, setShowAlertHelp] = useState(false);
  const [period, setPeriod] = useState<Period>("30d");
  const days = periodDays(period);
  const [equipmentId, setEquipmentId] = useState("");
  const [orderId, setOrderId] = useState("");
  const [lossPeriod, setLossPeriod] = useState<Period>("30d");
  const lossDays = periodDays(lossPeriod);
  const [lossEquipmentId, setLossEquipmentId] = useState("");
  const [lossOrderId, setLossOrderId] = useState("");
  const [alertName, setAlertName] = useState("");
  const [alertMetric, setAlertMetric] = useState<DashboardAlertMetric>("downtime_minutes_above");
  const [alertThreshold, setAlertThreshold] = useState("30");
  const [alertEquipmentId, setAlertEquipmentId] = useState("");
  const [alertWindow, setAlertWindow] = useState(60);

  const ordersQuery = useQuery({
    queryKey: ["order-progress", isLoss ? lossPeriod : period],
    queryFn: () => fetchOrderProgress(undefined, true, periodHours(isLoss ? lossPeriod : period)),
    refetchInterval: 30_000,
  });
  const linesQuery = useQuery({
    queryKey: ["dashboard-line-status"],
    queryFn: () => fetchLineStatus(),
    refetchInterval: 30_000,
  });
  const shiftQuery = useQuery({
    queryKey: ["dashboard-shift-summary", period, equipmentId, orderId],
    queryFn: () => fetchShiftSummary(periodHours(period), equipmentId || undefined, orderId || undefined),
    refetchInterval: 30_000,
  });
  const trendQuery = useQuery({
    queryKey: ["dashboard-production-trends", days, equipmentId, orderId],
    queryFn: () => fetchProductionTrends({
      days,
      ...(equipmentId ? { equipment_id: equipmentId } : {}),
      ...(orderId ? { order_id: orderId } : {}),
    }),
    refetchInterval: 60_000,
  });
  const lossesQuery = useQuery({
    queryKey: ["dashboard-loss-breakdown", lossDays, lossEquipmentId, lossOrderId],
    queryFn: () => fetchLossBreakdown({
      days: lossDays,
      ...(lossEquipmentId ? { equipment_id: lossEquipmentId } : {}),
      ...(lossOrderId ? { order_id: lossOrderId } : {}),
    }),
    refetchInterval: 60_000,
  });
  const rulesQuery = useQuery({
    queryKey: ["dashboard-alert-rules"],
    queryFn: fetchDashboardAlertRules,
  });
  const alertsQuery = useQuery({
    queryKey: ["dashboard-alerts"],
    queryFn: fetchDashboardAlerts,
    refetchInterval: 30_000,
  });

  const refresh = () => {
    void queryClient.invalidateQueries({
      predicate: (q) => {
        const key = String(q.queryKey[0]);
        return key.startsWith("dashboard-") || key === "order-progress";
      },
    });
  };
  const equipment = useMemo(() => {
    const lines = linesQuery.data ?? [];
    return lines.flatMap((line) => line.equipment.map((item) => ({
      ...item,
      line_name: line.line_name,
    })));
  }, [linesQuery.data]);
  const orders = ordersQuery.data ?? [];

  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  const resetRuleForm = () => {
    setEditingRuleId(null);
    setAlertName("");
    setAlertMetric("downtime_minutes_above");
    setAlertThreshold("30");
    setAlertEquipmentId("");
    setAlertWindow(60);
  };

  const startEditing = (rule: DashboardAlertRule) => {
    setEditingRuleId(rule.id);
    setAlertName(rule.name);
    setAlertMetric(rule.metric);
    setAlertThreshold(String(isMinutesMetric(rule.metric)
      ? rule.threshold
      : Number((rule.threshold * 100).toFixed(4))));
    setAlertEquipmentId(rule.equipment_id ?? "");
    setAlertWindow(rule.window_minutes);
  };

  const refreshRules = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard-alert-rules"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard-alerts"] });
  };

  const saveRule = useMutation({
    mutationFn: (payload: Parameters<typeof createDashboardAlertRule>[0]) =>
      editingRuleId ? updateDashboardAlertRule(editingRuleId, payload) : createDashboardAlertRule(payload),
    onSuccess: () => {
      refreshRules();
      resetRuleForm();
    },
  });
  const toggleRule = useMutation({
    mutationFn: ({ ruleId, enabled }: { ruleId: string; enabled: boolean }) =>
      setDashboardAlertRuleEnabled(ruleId, enabled),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard-alert-rules"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-alerts"] });
    },
  });
  const removeRule = useMutation({
    mutationFn: deleteDashboardAlertRule,
    onSuccess: (_data, ruleId) => {
      refreshRules();
      if (editingRuleId === ruleId) resetRuleForm();
    },
  });

  const submitRule = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const thresholdInput = Number(alertThreshold);
    if (!alertName.trim() || !Number.isFinite(thresholdInput)) return;
    const threshold = isMinutesMetric(alertMetric)
      ? thresholdInput
      : thresholdInput / 100;
    saveRule.mutate({
      name: alertName.trim(),
      metric: alertMetric,
      threshold,
      window_minutes: alertWindow,
      ...(alertEquipmentId ? { equipment_id: alertEquipmentId } : {}),
    });
  };

  const changeMetric = (metric: DashboardAlertMetric) => {
    setAlertMetric(metric);
    const config = METRICS.find((item) => item.value === metric);
    if (config) setAlertThreshold(config.defaultThreshold);
  };

  const shift = shiftQuery.data;
  const trend = trendQuery.data as DashboardTrends | undefined;
  const losses = lossesQuery.data as DashboardLossBreakdown | undefined;
  const activeAlerts = (alertsQuery.data ?? []) as DashboardAlert[];
  const rules = (rulesQuery.data ?? []) as DashboardAlertRule[];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Shop Floor Dashboard</h2>
          <p className="text-sm text-gray-500">Production, equipment health, losses, and active alerts</p>
        </div>
        <button onClick={refresh} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
          <ArrowPathIcon className="h-4 w-4" /> Refresh
        </button>
      </div>

      <section aria-label="Active alerts" className="space-y-2">
        {activeAlerts.map((alert) => (
          <div key={alert.rule_id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900">
            <span className="font-semibold">{alert.rule_name}: {alert.message}</span>
            <span className="text-sm">
              Threshold {formatMetric(alert.metric, alert.threshold)} · {new Date(alert.window_start).toLocaleString()}–now
            </span>
          </div>
        ))}
        {alertsQuery.isError && <QueryError message="Unable to evaluate dashboard alerts." />}
        {!alertsQuery.isLoading && activeAlerts.length === 0 && (
          <p className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">No active alerts</p>
        )}
      </section>

      <nav className="flex gap-1 border-b" role="tablist" aria-label="Dashboard sections">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={subTab === tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${subTab === tab.id ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {(subTab === "trends" || subTab === "losses") && (
        <div className="flex flex-wrap items-center gap-2" aria-label="Range filters">
          <label className="sr-only" htmlFor="trend-days">Time period</label>
          <select id="trend-days" value={isLoss ? lossPeriod : period} onChange={(e) => {
            if (isLoss) { setLossPeriod(e.target.value as Period); setLossOrderId(""); }
            else { setPeriod(e.target.value as Period); setOrderId(""); }
          }} className="rounded border px-2 py-1 text-sm">
            {PERIODS.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
          </select>
          <label className="sr-only" htmlFor="trend-equipment">Filter by equipment</label>
          <select id="trend-equipment" value={isLoss ? lossEquipmentId : equipmentId} onChange={(e) => (isLoss ? setLossEquipmentId : setEquipmentId)(e.target.value)} className="max-w-56 rounded border px-2 py-1 text-sm">
            <option value="">All equipment</option>
            {equipment.map((item) => <option key={item.equipment_id} value={item.equipment_id}>{item.line_name} / {item.name}</option>)}
          </select>
          <label className="sr-only" htmlFor="trend-order">Filter by order</label>
          <select id="trend-order" value={isLoss ? lossOrderId : orderId} onChange={(e) => (isLoss ? setLossOrderId : setOrderId)(e.target.value)} className="max-w-56 rounded border px-2 py-1 text-sm">
            <option value="">All orders</option>
            {orders.map((order) => <option key={order.order_id} value={order.order_id}>{order.order_number}</option>)}
          </select>
        </div>
      )}

      {subTab === "trends" && (
        <section className="grid gap-4 sm:grid-cols-2" aria-label="Unit and lot counters">
          <SummaryCard label="Started (units + lots)" value={shift ? shift.units_started + shift.lots_started : undefined} loading={shiftQuery.isLoading} />
          <SummaryCard label="Completed (units + lots)" value={shift ? shift.units_completed + shift.lots_completed : undefined} loading={shiftQuery.isLoading} />
        </section>
      )}

      {subTab === "trends" && (
      <section className="rounded-lg bg-white p-5 shadow" role="tabpanel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="relative flex items-center gap-1">
              <h3 className="text-lg font-semibold text-gray-700">Production trends</h3>
              <button
                type="button"
                aria-label="How to record production counters"
                aria-expanded={showCounterHelp}
                onClick={() => setShowCounterHelp((open) => !open)}
                className="text-gray-400 hover:text-blue-600"
              >
                <QuestionMarkCircleIcon className="h-5 w-5" />
              </button>
              {showCounterHelp ? <CounterHelp onClose={() => setShowCounterHelp(false)} /> : null}
            </div>
            <p className="text-xs text-gray-500">Daily shift-counter totals; OEE is shown when an equipment is selected.</p>
          </div>
        </div>
        {trendQuery.isError ? <QueryError message="Unable to load production trends." /> : null}
        {trendQuery.isLoading ? <p className="text-sm text-gray-400">Loading trends…</p> : trend && (
          <>
            {trend.source === "none" ? (
              <p className="mb-2 rounded bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
                No production counters or completed WIP recorded in this range.
              </p>
            ) : null}
            {trend.source === "wip" ? (
              <p className="mb-2 rounded bg-blue-50 px-3 py-2 text-sm text-blue-800">
                No production counters recorded in this range; counts are derived from WIP
                (completed, scrapped and reworked units).
              </p>
            ) : null}
            <TrendChart trend={trend} />
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b text-left text-gray-500">
                  <th className="px-3 py-2">Date</th><th className="px-3 py-2">Good</th>
                  <th className="px-3 py-2">Reject</th><th className="px-3 py-2">Rework</th>
                  <th className="px-3 py-2">OEE</th>
                </tr></thead>
                <tbody>{trend.series.slice().reverse()
                  .filter((point) => point.good + point.reject + point.rework > 0 || point.oee !== null)
                  .map((point) => (
                  <tr key={point.date} className="border-b">
                    <td className="px-3 py-2">{new Date(`${point.date}T00:00:00`).toLocaleDateString()}</td>
                    <td className="px-3 py-2 text-green-700">{point.good}</td>
                    <td className="px-3 py-2 text-red-700">{point.reject}</td>
                    <td className="px-3 py-2 text-orange-700">{point.rework}</td>
                    <td className="px-3 py-2">{point.oee === null ? "—" : `${(point.oee * 100).toFixed(1)}%`}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </>
        )}
      </section>
      )}

      {subTab === "losses" && (
      <section role="tabpanel">
        <div className="rounded-lg bg-white p-5 shadow">
          <h3 className="mb-1 text-lg font-semibold text-gray-700">Loss drill-down</h3>
          <p className="mb-3 text-xs text-gray-500">Downtime by reason, rejected/reworked counts by order, and output by production date.</p>
          {lossesQuery.isError ? <QueryError message="Unable to load loss breakdown." /> : null}
          {lossesQuery.isLoading ? <p className="text-sm text-gray-400">Loading losses…</p> : losses && (
            <div className="space-y-5">
              {losses.source === "wip" ? (
                <p className="rounded bg-blue-50 px-3 py-2 text-sm text-blue-800">
                  No production counters recorded in this range; quality loss and output are derived from WIP
                  (completed, scrapped and reworked units).
                </p>
              ) : null}
              <LossTable title="Downtime by reason" headers={["Reason", "Type", "Minutes"]} rows={
                losses.by_reason.map((item) => [item.reason_code ? `${item.reason_code} · ${item.reason_name}` : item.reason_name, labelFor(item.loss_type), item.minutes.toFixed(1)])
              } empty="No recorded downtime in this range." />
              <LossTable title="Quality loss by order" headers={["Order", "Date Created", "Good", "Reject", "Rework"]} rows={
                losses.by_order.map((item) => [item.order_number, item.created_at ? new Date(item.created_at).toLocaleDateString() : "—", String(item.good), String(item.reject), String(item.rework)])
              } empty="No production counter data in this range." />
              <LossTable title="Production by shift date" headers={["Date", "Good", "Reject", "Rework"]} rows={
                losses.by_shift_date.map((item) => [new Date(`${item.date}T00:00:00`).toLocaleDateString(), String(item.good), String(item.reject), String(item.rework)])
              } empty="No shift totals in this range." />
            </div>
          )}
        </div>
      </section>
      )}

      {subTab === "alerts" && (
      <section role="tabpanel">
        <div className="rounded-lg bg-white p-5 shadow">
          <div className="relative mb-1 flex items-center gap-1">
            <h3 className="text-lg font-semibold text-gray-700">Configurable alerts</h3>
            <button
              type="button"
              aria-label="Alert settings help"
              aria-expanded={showAlertHelp}
              onClick={() => setShowAlertHelp((open) => !open)}
              className="text-gray-400 hover:text-blue-600"
            >
              <QuestionMarkCircleIcon className="h-5 w-5" />
            </button>
            {showAlertHelp ? <AlertHelp onClose={() => setShowAlertHelp(false)} /> : null}
          </div>
          <p className="mb-4 text-xs text-gray-500">Rules persist in MES. Alerts are re-evaluated every 30 seconds and clear when the metric returns to range. OEE and scrap/rework use production counters recorded by shift date.</p>
          <form onSubmit={submitRule} className={`space-y-3 rounded border p-3 ${editingRuleId ? "border-indigo-300 bg-indigo-50" : "bg-gray-50"}`}>
            {editingRuleId && <p className="text-sm font-medium text-indigo-800">Editing alert rule</p>}
            <label className="block text-sm">Rule name
              <input required value={alertName} onChange={(e) => setAlertName(e.target.value)} className="mt-1 w-full rounded border px-3 py-2" maxLength={255} />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">Metric
                <select value={alertMetric} onChange={(e) => changeMetric(e.target.value as DashboardAlertMetric)} className="mt-1 w-full rounded border px-3 py-2">
                  {METRICS.map((metric) => <option key={metric.value} value={metric.value}>{metric.label}</option>)}
                </select>
              </label>
              <label className="block text-sm">{isMinutesMetric(alertMetric) ? "Limit (minutes)" : "Limit (%)"}
                <input required type="number" min="0" step="any" value={alertThreshold} onChange={(e) => setAlertThreshold(e.target.value)} className="mt-1 w-full rounded border px-3 py-2" />
              </label>
              <label className="block text-sm">Window (minutes){alertMetric === "current_downtime_above" ? " – not used" : ""}
                <input required disabled={alertMetric === "current_downtime_above"} type="number" min="1" max="10080" value={alertWindow} onChange={(e) => setAlertWindow(Number(e.target.value))} className="mt-1 w-full rounded border px-3 py-2 disabled:bg-gray-100 disabled:text-gray-400" />
              </label>
              <label className="block text-sm">Equipment {alertMetric === "oee_below" ? "(required)" : "(optional)"}
                <select required={alertMetric === "oee_below"} value={alertEquipmentId} onChange={(e) => setAlertEquipmentId(e.target.value)} className="mt-1 w-full rounded border px-3 py-2">
                  <option value="">All equipment</option>
                  {equipment.map((item) => <option key={item.equipment_id} value={item.equipment_id}>{item.line_name} / {item.name}</option>)}
                </select>
              </label>
            </div>
            <div className="flex items-center gap-3">
              <button disabled={saveRule.isPending} className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                {saveRule.isPending ? "Saving…" : editingRuleId ? "Save changes" : "Add alert rule"}
              </button>
              {editingRuleId && (
                <button type="button" onClick={resetRuleForm} className="rounded border px-4 py-2 text-sm">Cancel edit</button>
              )}
            </div>
            {saveRule.isError && <p role="alert" className="text-sm text-red-700">Could not save the alert rule.</p>}
            {(toggleRule.isError || removeRule.isError) && <p role="alert" className="text-sm text-red-700">Could not update the alert rules.</p>}
          </form>
          <div className="mt-4 space-y-2">
            {rulesQuery.isError && <QueryError message="Unable to load alert rules." />}
            {rules.map((rule) => (
              <AlertRuleRow
                key={rule.id}
                rule={rule}
                equipmentName={equipment.find((item) => item.equipment_id === rule.equipment_id)?.name}
                active={activeAlerts.some((alert) => alert.rule_id === rule.id)}
                onToggle={() => toggleRule.mutate({ ruleId: rule.id, enabled: !rule.is_enabled })}
                onDelete={() => removeRule.mutate(rule.id)}
                onTest={() => setTestRule(rule)}
                onEdit={() => startEditing(rule)}
              />
            ))}
            {!rulesQuery.isLoading && rules.length === 0 && <p className="text-sm text-gray-400">No alert rules configured.</p>}
          </div>
        </div>
      </section>
      )}

      {testRule && <AlertTestDialog rule={testRule} onClose={() => setTestRule(null)} />}
    </div>
  );
}

function TrendChart({ trend }: { trend: DashboardTrends }) {
  const max = Math.max(1, ...trend.series.map((point) => point.good + point.reject + point.rework));
  const points = trend.series.map((point, index) => {
    const x = trend.series.length < 2 ? 0 : (index / (trend.series.length - 1)) * 600;
    const y = 110 - ((point.good + point.reject + point.rework) / max) * 100;
    return `${x},${y}`;
  }).join(" ");
  return (
    <div>
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span className="inline-block h-2.5 w-2.5 rounded-full bg-indigo-500" /> Good + reject + rework count
        {trend.equipment_id && <span>· OEE available in daily table</span>}
      </div>
      <div className="mt-2 overflow-hidden rounded border bg-gray-50 px-2 py-3">
        <svg viewBox="0 0 600 120" role="img" aria-label={`Daily production counts over ${trend.days} days`} className="h-32 w-full">
          <line x1="0" y1="110" x2="600" y2="110" stroke="#d1d5db" />
          {trend.series.length > 1 && <polyline points={points} fill="none" stroke="#6366f1" strokeWidth="3" vectorEffect="non-scaling-stroke" />}
        </svg>
        <div className="flex justify-between px-1 text-xs text-gray-500">
          <span>{trend.period_start}</span><span>{trend.period_end}</span>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, loading }: { label: string; value?: number; loading: boolean }) {
  return (
    <div className="rounded-lg bg-white p-4 shadow">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-800">{loading ? "…" : value ?? "—"}</p>
    </div>
  );
}

function LossTable({ title, headers, rows, empty }: {
  title: string;
  headers: string[];
  rows: string[][];
  empty: string;
}) {
  return (
    <div>
      <h4 className="mb-1 text-sm font-semibold text-gray-700">{title}</h4>
      {rows.length === 0 ? <p className="text-xs text-gray-400">{empty}</p> : (
        <div className="max-h-48 overflow-auto">
          <table className="min-w-full text-xs">
            <thead><tr className="border-b text-left text-gray-500">{headers.map((header) => <th key={header} className="px-2 py-1">{header}</th>)}</tr></thead>
            <tbody>{rows.map((row, i) => <tr key={`${row[0]}-${i}`} className="border-b">{row.map((cell, j) => <td key={j} className="px-2 py-1">{cell}</td>)}</tr>)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const TEST_FIELDS: Record<DashboardAlertMetric, { key: keyof DashboardAlertTestInput; label: string; step?: string }[]> = {
  downtime_minutes_above: [
    { key: "downtime_minutes", label: "Downtime in window (minutes)", step: "any" },
  ],
  current_downtime_above: [
    { key: "downtime_minutes", label: "Current continuous downtime (minutes)", step: "any" },
  ],
  scrap_rate_above: [
    { key: "good_count", label: "Good count" },
    { key: "reject_count", label: "Reject count" },
    { key: "rework_count", label: "Rework count" },
  ],
  oee_below: [
    { key: "run_minutes", label: "Run time (minutes)", step: "any" },
    { key: "downtime_minutes", label: "Downtime (minutes)", step: "any" },
    { key: "ideal_cycle_time_sec", label: "Ideal cycle time (sec/unit)", step: "any" },
    { key: "good_count", label: "Good count" },
    { key: "reject_count", label: "Reject count" },
    { key: "rework_count", label: "Rework count" },
  ],
};

function AlertTestDialog({ rule, onClose }: { rule: DashboardAlertRule; onClose: () => void }) {
  const fields = TEST_FIELDS[rule.metric];
  const [values, setValues] = useState<Record<string, string>>({});
  const test = useMutation({ mutationFn: (payload: DashboardAlertTestInput) => testDashboardAlertRule(rule.id, payload) });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const payload: Record<string, number> = {};
    for (const field of fields) {
      const raw = values[field.key];
      if (raw !== undefined && raw !== "") payload[field.key] = Number(raw);
    }
    test.mutate(payload);
  };

  const hint = isMinutesMetric(rule.metric)
    ? `Enter more than ${rule.threshold} minutes of ${rule.metric === "current_downtime_above" ? "continuous " : ""}downtime to trigger.`
    : rule.metric === "scrap_rate_above"
      ? `Enter counts where (reject + rework) / total exceeds ${(rule.threshold * 100).toFixed(1)}%.`
      : `Enter run time, downtime, cycle time and counts that give an OEE below ${(rule.threshold * 100).toFixed(1)}%.`;
  const serverError = axios.isAxiosError(test.error)
    ? (test.error.response?.data as { error?: { message?: string } } | undefined)?.error?.message
    : undefined;

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label={`Test alert rule ${rule.name}`}>
      <form onSubmit={submit} className="w-full max-w-md space-y-3 rounded-lg bg-white p-5 shadow-xl">
        <div className="flex items-center justify-between">
          <h4 className="text-lg font-semibold text-gray-800">Test: {rule.name}</h4>
          <button type="button" onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-700">✕</button>
        </div>
        <p className="text-sm text-gray-600">
          Enter sample data to check whether this rule would fire. This is a dry run: nothing is saved and no real alert is raised.
        </p>
        <p className="text-xs text-gray-500">{hint}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {fields.map((field) => (
            <label key={field.key} className="block text-sm">{field.label}
              <input
                required
                type="number"
                min="0"
                step={field.step ?? "1"}
                value={values[field.key] ?? ""}
                onChange={(e) => setValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                className="mt-1 w-full rounded border px-3 py-2"
              />
            </label>
          ))}
        </div>
        {test.isError && <p role="alert" className="text-sm text-red-700">{serverError ?? "Could not run the test."}</p>}
        {test.data && (
          <p role="status" className={`rounded px-3 py-2 text-sm ${test.data.would_trigger ? "bg-amber-50 text-amber-900" : "bg-green-50 text-green-800"}`}>
            {test.data.would_trigger ? "Alert WOULD trigger" : "Alert would NOT trigger"}: {test.data.message}
            {" "}(threshold {formatMetric(rule.metric, test.data.threshold)})
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded border px-4 py-2 text-sm">Close</button>
          <button disabled={test.isPending} className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            {test.isPending ? "Testing…" : "Run test"}
          </button>
        </div>
      </form>
    </div>
  );
}

function AlertRuleRow({ rule, equipmentName, active, onToggle, onDelete, onTest, onEdit }: {
  rule: DashboardAlertRule;
  equipmentName?: string;
  active: boolean;
  onToggle: () => void;
  onDelete: () => void;
  onTest: () => void;
  onEdit: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-2 text-sm">
      <span>
        <strong>{rule.name}</strong> · {labelFor(rule.metric)} {formatMetric(rule.metric, rule.threshold)}
        {equipmentName ? ` · ${equipmentName}` : " · all equipment"} · {rule.window_minutes} min
        {active && <span className="ml-2 rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800">Active</span>}
        {!rule.is_enabled && <span className="ml-2 text-xs text-gray-400">Disabled</span>}
      </span>
      <span className="flex gap-3">
        <button onClick={onEdit} className="text-indigo-600 hover:underline">Edit</button>
        <button onClick={onTest} className="text-indigo-600 hover:underline">Test</button>
        <button onClick={onToggle} className="text-indigo-600 hover:underline">{rule.is_enabled ? "Disable" : "Enable"}</button>
        <button onClick={onDelete} className="text-red-600 hover:underline">Delete</button>
      </span>
    </div>
  );
}

function QueryError({ message }: { message: string }) {
  return <p role="alert" className="text-sm text-red-700">{message}</p>;
}

function labelFor(value: string) {
  return value.replace(/_/g, " ");
}

function formatMetric(metric: DashboardAlertMetric, value: number) {
  return isMinutesMetric(metric) ? `${value} min` : `${(value * 100).toFixed(1)}%`;
}
