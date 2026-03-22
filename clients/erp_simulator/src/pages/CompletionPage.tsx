import { useState } from "react";
import { reportCompletion, type ERPConfirmation } from "../api/erp";

export default function CompletionPage() {
  const [orderId, setOrderId] = useState("000001000100");
  const [qtyGood, setQtyGood] = useState(95);
  const [qtyReject, setQtyReject] = useState(5);
  const [stepId, setStepId] = useState("0010");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ERPConfirmation | null>(null);
  const [error, setError] = useState<string | null>(null);

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
          <label className="block text-sm font-medium text-gray-700">Manufacturing Order</label>
          <input
            type="text"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            className="mt-1 w-full border rounded px-3 py-2 text-sm"
            required
          />
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
          <label className="block text-sm font-medium text-gray-700">Operation (Step ID)</label>
          <input
            type="text"
            value={stepId}
            onChange={(e) => setStepId(e.target.value)}
            placeholder="e.g. 0010"
            className="mt-1 w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
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
