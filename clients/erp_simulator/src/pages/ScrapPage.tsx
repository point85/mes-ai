import { useState } from "react";
import { reportScrap, type ERPConfirmation } from "../api/erp";

export default function ScrapPage() {
  const [orderId, setOrderId] = useState("000001000100");
  const [qtyScrapped, setQtyScrapped] = useState(3);
  const [reasonCode, setReasonCode] = useState("DEFECTIVE_PCB");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ERPConfirmation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await reportScrap({ order_id: orderId, qty_scrapped: qtyScrapped, reason_code: reasonCode })
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Report failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <p className="text-sm text-gray-600">Post a goods movement 531 (scrap posting) to SAP.</p>
      <form onSubmit={handleSubmit} className="bg-white rounded-lg border p-4 space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Manufacturing Order</label>
          <input type="text" value={orderId} onChange={(e) => setOrderId(e.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Qty Scrapped</label>
          <input type="number" value={qtyScrapped} onChange={(e) => setQtyScrapped(Number(e.target.value))} min={1} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Reason Code</label>
          <input type="text" value={reasonCode} onChange={(e) => setReasonCode(e.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <button type="submit" disabled={loading} className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50">
          {loading ? "Posting…" : "Post Scrap (531)"}
        </button>
      </form>
      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>}
      {result && (
        <div className={`p-4 rounded-lg border ${result.success ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
          <div className="text-sm font-medium mb-1">{result.success ? "Scrap Posted" : "SAP Rejected"}</div>
          {result.erp_doc_number && <div className="text-sm"><strong>Material Doc:</strong> {result.erp_doc_number}</div>}
          {result.message && <div className="text-sm text-gray-600 mt-1">{result.message}</div>}
        </div>
      )}
    </div>
  );
}
