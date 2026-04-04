import { useState, useEffect } from "react";
import {
  reportCompletion,
  readProductionOrders,
  readRouteSteps,
  type ERPConfirmation,
  type DBProductionOrder,
  type DBRouteStep,
} from "../api/erp";

export default function CompletionPage() {
  const [orders, setOrders] = useState<DBProductionOrder[]>([]);
  const [orderId, setOrderId] = useState("");
  const [steps, setSteps] = useState<DBRouteStep[]>([]);
  const [stepId, setStepId] = useState("");
  const [qtyGood, setQtyGood] = useState(0);
  const [qtyReject, setQtyReject] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ERPConfirmation | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load orders on mount
  useEffect(() => {
    readProductionOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  // When selected order changes, load its route steps
  useEffect(() => {
    setSteps([]);
    setStepId("");
    const order = orders.find((o) => o.id === orderId);
    if (order?.route_id) {
      readRouteSteps(order.route_id)
        .then((s) => {
          setSteps(s);
          if (s.length > 0) setStepId(s[0].id);
        })
        .catch(() => setSteps([]));
    }
  }, [orderId, orders]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await reportCompletion({
        order_id: orderId,
        qty_good: qtyGood,
        qty_reject: qtyReject,
        step_id: stepId || undefined,
      });
      setResult(r);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Report failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <p className="text-sm text-gray-600">
        Post a production completion confirmation to SAP (MB31 equivalent).
      </p>
      <form onSubmit={handleSubmit} className="bg-white rounded-lg border p-4 space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Production Order</label>
          <select
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            className="mt-1 w-full border rounded px-3 py-2 text-sm"
            required
          >
            <option value="">— select an order —</option>
            {orders.map((o) => (
              <option key={o.id} value={o.id}>
                {o.order_number}{o.erp_reference ? ` (${o.erp_reference})` : ""} — {o.status}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700">Qty Good</label>
            <input
              type="number"
              value={qtyGood}
              onChange={(e) => setQtyGood(Number(e.target.value))}
              min={0}
              className="mt-1 w-full border rounded px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Qty Reject</label>
            <input
              type="number"
              value={qtyReject}
              onChange={(e) => setQtyReject(Number(e.target.value))}
              min={0}
              className="mt-1 w-full border rounded px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Operation Step</label>
          <select
            value={stepId}
            onChange={(e) => setStepId(e.target.value)}
            className="mt-1 w-full border rounded px-3 py-2 text-sm"
            disabled={steps.length === 0}
          >
            {steps.length === 0 ? (
              <option value="">— select an order first —</option>
            ) : (
              steps.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.sequence}. {s.name} ({s.step_type}){s.erp_operation_number ? ` [Op ${s.erp_operation_number}]` : ""}
                </option>
              ))
            )}
          </select>
        </div>
        <button
          type="submit"
          disabled={loading || !orderId}
          className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? "Posting…" : "Post Completion"}
        </button>
      </form>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
      )}
      {result && (
        <div
          className={`p-4 rounded-lg border ${
            result.success ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
          }`}
        >
          <div className="text-sm font-medium mb-1">
            {result.success ? "SAP Confirmation Posted" : "SAP Rejected"}
          </div>
          {result.erp_doc_number && (
            <div className="text-sm">
              <strong>Doc Number:</strong> {result.erp_doc_number}
            </div>
          )}
          {result.message && <div className="text-sm text-gray-600 mt-1">{result.message}</div>}
        </div>
      )}
    </div>
  );
}
