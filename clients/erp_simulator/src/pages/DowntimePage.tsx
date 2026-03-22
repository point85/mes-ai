import { useState } from "react";
import { reportDowntime, type ERPConfirmation } from "../api/erp";

export default function DowntimePage() {
  const [equipmentId, setEquipmentId] = useState("WC-SMT-01");
  const [duration, setDuration] = useState(120);
  const [reasonCode, setReasonCode] = useState("CONVEYOR_JAM");
  const [startedAt, setStartedAt] = useState(new Date().toISOString().slice(0, 16));
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
        await reportDowntime({
          equipment_id: equipmentId,
          duration_minutes: duration,
          reason_code: reasonCode,
          started_at: new Date(startedAt).toISOString(),
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
      <p className="text-sm text-gray-600">Post a Plant Maintenance notification (M2) to SAP.</p>
      <form onSubmit={handleSubmit} className="bg-white rounded-lg border p-4 space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">Equipment / Work Center</label>
          <input type="text" value={equipmentId} onChange={(e) => setEquipmentId(e.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Duration (minutes)</label>
          <input type="number" value={duration} onChange={(e) => setDuration(Number(e.target.value))} min={1} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Reason Code</label>
          <input type="text" value={reasonCode} onChange={(e) => setReasonCode(e.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Started At</label>
          <input type="datetime-local" value={startedAt} onChange={(e) => setStartedAt(e.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm" required />
        </div>
        <button type="submit" disabled={loading} className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50">
          {loading ? "Posting…" : "Post PM Notification"}
        </button>
      </form>
      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>}
      {result && (
        <div className={`p-4 rounded-lg border ${result.success ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
          <div className="text-sm font-medium mb-1">{result.success ? "PM Notification Created" : "SAP Rejected"}</div>
          {result.erp_doc_number && <div className="text-sm"><strong>Notification #:</strong> {result.erp_doc_number}</div>}
          {result.message && <div className="text-sm text-gray-600 mt-1">{result.message}</div>}
        </div>
      )}
    </div>
  );
}
