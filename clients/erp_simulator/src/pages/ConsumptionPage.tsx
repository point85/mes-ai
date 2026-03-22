import { useState } from "react";
import { reportConsumption, type ERPConfirmation } from "../api/erp";

interface MaterialLine {
  material_code: string;
  quantity: number;
  uom: string;
  lot_number: string;
}

const defaultLine = (): MaterialLine => ({
  material_code: "RM-STEEL-1MM",
  quantity: 2.5,
  uom: "KG",
  lot_number: "",
});

export default function ConsumptionPage() {
  const [orderId, setOrderId] = useState("000001000100");
  const [lines, setLines] = useState<MaterialLine[]>([defaultLine()]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ERPConfirmation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateLine = (idx: number, field: keyof MaterialLine, value: string | number) => {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  };

  const addLine = () => setLines((prev) => [...prev, defaultLine()]);

  const removeLine = (idx: number) => {
    if (lines.length > 1) setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await reportConsumption({
        order_id: orderId,
        materials: lines.map((l) => ({
          material_code: l.material_code,
          quantity: l.quantity,
          uom: l.uom,
          lot_number: l.lot_number || undefined,
        })),
      });
      setResult(r);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Report failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-4">
      <p className="text-sm text-gray-600">
        Post a goods movement 261 (material consumption) to SAP.
      </p>
      <form onSubmit={handleSubmit} className="bg-white rounded-lg border p-4 space-y-4">
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
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">Materials</label>
            <button type="button" onClick={addLine} className="text-xs text-blue-600 hover:underline">
              + Add Line
            </button>
          </div>
          {lines.map((line, idx) => (
            <div key={idx} className="grid grid-cols-[1fr_80px_60px_1fr_32px] gap-2 items-end">
              <div>
                <label className="block text-xs text-gray-500">Material</label>
                <input
                  type="text"
                  value={line.material_code}
                  onChange={(e) => updateLine(idx, "material_code", e.target.value)}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Qty</label>
                <input
                  type="number"
                  value={line.quantity}
                  onChange={(e) => updateLine(idx, "quantity", Number(e.target.value))}
                  step="0.01"
                  min="0.01"
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">UoM</label>
                <input
                  type="text"
                  value={line.uom}
                  onChange={(e) => updateLine(idx, "uom", e.target.value)}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Lot #</label>
                <input
                  type="text"
                  value={line.lot_number}
                  onChange={(e) => updateLine(idx, "lot_number", e.target.value)}
                  placeholder="optional"
                  className="w-full border rounded px-2 py-1.5 text-sm"
                />
              </div>
              <button
                type="button"
                onClick={() => removeLine(idx)}
                className="text-red-400 hover:text-red-600 pb-1"
                title="Remove"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? "Posting…" : "Post Consumption (261)"}
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
            {result.success ? "Goods Movement Posted" : "SAP Rejected"}
          </div>
          {result.erp_doc_number && (
            <div className="text-sm">
              <strong>Material Doc:</strong> {result.erp_doc_number}
            </div>
          )}
          {result.message && <div className="text-sm text-gray-600 mt-1">{result.message}</div>}
        </div>
      )}
    </div>
  );
}
