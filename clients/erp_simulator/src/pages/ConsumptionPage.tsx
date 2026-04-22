import { useState, useEffect } from "react";
import {
  reportConsumption,
  readProductionOrders,
  readProductBoms,
  readBomItems,
  readProductRoutes,
  readRouteSteps,
  type ERPConfirmation,
  type DBProductionOrder,
  type DBBomItem,
  type DBRouteStep,
} from "../api/erp";

interface ConsumptionLine {
  material_code: string;
  quantity: number;
  uom: string;
  lot_number: string;
}

export default function ConsumptionPage() {
  const [orders, setOrders] = useState<DBProductionOrder[]>([]);
  const [orderId, setOrderId] = useState("");
  const [bomItems, setBomItems] = useState<DBBomItem[]>([]);
  const [steps, setSteps] = useState<DBRouteStep[]>([]);
  const [selectedBomItemId, setSelectedBomItemId] = useState("");
  const [lines, setLines] = useState<ConsumptionLine[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ERPConfirmation | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load orders on mount
  useEffect(() => {
    readProductionOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  // When order changes, load its BOM items and route steps
  useEffect(() => {
    setBomItems([]);
    setSteps([]);
    setLines([]);
    setSelectedBomItemId("");
    const order = orders.find((o) => o.id === orderId);
    if (!order) return;

    // Load BOM items for this order's product
    readProductBoms(order.product_id)
      .then(async (boms) => {
        const activeBom = boms.find((b) => b.is_active);
        if (activeBom) {
          const items = await readBomItems(activeBom.id);
          setBomItems(items.filter((i) => i.is_active));
        }
      })
      .catch(() => setBomItems([]));

    // Load route steps (for display context)
    if (order.route_id) {
      readRouteSteps(order.route_id)
        .then(setSteps)
        .catch(() => setSteps([]));
    } else {
      readProductRoutes(order.product_id)
        .then(async (routes) => {
          const dflt = routes.find((r) => r.is_default) ?? routes[0];
          if (dflt) {
            const s = await readRouteSteps(dflt.id);
            setSteps(s);
          }
        })
        .catch(() => setSteps([]));
    }
  }, [orderId, orders]);

  const stepMap = new Map(steps.map((s) => [s.id, s]));

  const addFromBom = () => {
    const item = bomItems.find((b) => b.id === selectedBomItemId);
    if (!item) return;
    setLines((prev) => [
      ...prev,
      {
        material_code: item.material_code,
        quantity: item.quantity,
        uom: item.uom,
        lot_number: "",
      },
    ]);
    setSelectedBomItemId("");
  };

  const updateLine = (idx: number, field: keyof ConsumptionLine, value: string | number) => {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  };

  const removeLine = (idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (lines.length === 0) return;
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

        {/* BOM material picker */}
        {bomItems.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Add BOM Material</label>
            <div className="flex gap-2">
              <select
                value={selectedBomItemId}
                onChange={(e) => setSelectedBomItemId(e.target.value)}
                className="flex-1 border rounded px-3 py-2 text-sm"
              >
                <option value="">— pick a material —</option>
                {bomItems.map((item) => {
                  const step = item.process_segment_id ? stepMap.get(item.process_segment_id) : null;
                  return (
                    <option key={item.id} value={item.id}>
                      {item.material_code} — {item.quantity} {item.uom}
                      {step
                        ? ` [Step ${step.sequence}: ${step.name}]`
                        : ""}
                    </option>
                  );
                })}
              </select>
              <button
                type="button"
                onClick={addFromBom}
                disabled={!selectedBomItemId}
                className="px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Add
              </button>
            </div>
          </div>
        )}

        {/* Consumption lines */}
        {lines.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Materials to Consume</label>
            {lines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_80px_60px_1fr_32px] gap-2 items-end">
                <div>
                  <label className="block text-xs text-gray-500">Material</label>
                  <input
                    type="text"
                    value={line.material_code}
                    readOnly
                    className="w-full border rounded px-2 py-1.5 text-sm bg-gray-50"
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
                    readOnly
                    className="w-full border rounded px-2 py-1.5 text-sm bg-gray-50"
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
        )}

        <button
          type="submit"
          disabled={loading || !orderId || lines.length === 0}
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
