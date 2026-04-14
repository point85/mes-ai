import { useState } from "react";
import { reportQualityResult, type ERPConfirmation } from "../../api/erp";

export default function ERPQualityPage() {
  const [orderId, setOrderId] = useState("000001000200");
  const [testId, setTestId] = useState("FUNC-TEST-001");
  const [testResult, setTestResult] = useState("PASS");
  const [detailsStr, setDetailsStr] = useState('{"voltage": 3.31, "current_ma": 250}');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ERPConfirmation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let details: Record<string, unknown> = {};
      if (detailsStr.trim()) {
        details = JSON.parse(detailsStr);
      }
      setResult(
        await reportQualityResult({
          order_id: orderId,
          test_id: testId,
          result: testResult,
          details,
        })
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Report failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <p className="text-sm text-gray-600">Post a QM results recording to SAP.</p>
      <form onSubmit={handleSubmit} className="bg-white rounded-lg border p-4 space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Manufacturing Order</label>
          <input type="text" value={orderId} onChange={(e) => setOrderId(e.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Inspection Characteristic (Test ID)</label>
          <input type="text" value={testId} onChange={(e) => setTestId(e.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Result</label>
          <select value={testResult} onChange={(e) => setTestResult(e.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm">
            <option value="PASS">PASS</option>
            <option value="FAIL">FAIL</option>
            <option value="CONDITIONAL">CONDITIONAL</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Details (JSON)</label>
          <textarea value={detailsStr} onChange={(e) => setDetailsStr(e.target.value)} rows={3} className="mt-1 w-full border rounded px-3 py-2 text-sm font-mono" />
        </div>
        <button type="submit" disabled={loading} className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50">
          {loading ? "Posting\u2026" : "Post QM Result"}
        </button>
      </form>
      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>}
      {result && (
        <div className={`p-4 rounded-lg border ${result.success ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
          <div className="text-sm font-medium mb-1">{result.success ? "QM Result Recorded" : "SAP Rejected"}</div>
          {result.erp_doc_number && <div className="text-sm"><strong>Inspection Lot #:</strong> {result.erp_doc_number}</div>}
          {result.message && <div className="text-sm text-gray-600 mt-1">{result.message}</div>}
        </div>
      )}
    </div>
  );
}
