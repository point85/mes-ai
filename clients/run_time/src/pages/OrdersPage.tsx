import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowPathIcon, ChevronDownIcon, ChevronRightIcon, PlusIcon,
  PencilSquareIcon, PlayIcon, CheckIcon, LockClosedIcon, XMarkIcon,
} from "@heroicons/react/24/outline";
import {
  fetchOrders, releaseOrder, completeOrder, closeOrder,
  createOrder, updateOrder,
  fetchUnits, fetchLots, createLot, createUnit,
  fetchProducts,
} from "../api/runtime";
import type { ProductionOrder, Product, Unit, Lot } from "../types";

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [expandedOrderId, setExpandedOrderId] = useState<string | null>(null);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingOrder, setEditingOrder] = useState<ProductionOrder | null>(null);

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders", statusFilter],
    queryFn: () => fetchOrders({ status: statusFilter || undefined }),
    refetchInterval: 10_000,
  });

  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => fetchProducts(),
  });

  const productMap = Object.fromEntries(products.map((p) => [p.id, p]));

  const selectedOrder = orders?.find((o) => o.id === selectedOrderId) ?? null;

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["orders"] });
    queryClient.invalidateQueries({ queryKey: ["lots"] });
    queryClient.invalidateQueries({ queryKey: ["units"] });
    queryClient.invalidateQueries({ queryKey: ["order-wip"] });
  };

  const toggleExpand = (id: string) =>
    setExpandedOrderId((prev) => (prev === id ? null : id));

  const handleSelect = (id: string) =>
    setSelectedOrderId((prev) => (prev === id ? null : id));

  const handleRelease = async () => {
    if (!selectedOrder) return;
    try { await releaseOrder(selectedOrder.id); refresh(); } catch { /* ignore */ }
  };

  const handleComplete = async () => {
    if (!selectedOrder) return;
    try { await completeOrder(selectedOrder.id); refresh(); } catch { /* ignore */ }
  };

  const handleClose = async () => {
    if (!selectedOrder) return;
    try { await closeOrder(selectedOrder.id); refresh(); } catch { /* ignore */ }
  };

  const canRelease = selectedOrder?.status === "created";
  const canComplete = selectedOrder?.status === "released" || selectedOrder?.status === "in_progress";
  const canEdit = !!selectedOrder && selectedOrder.status !== "closed";
  const canClose = !!selectedOrder && selectedOrder.status !== "closed";

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Production Orders</h2>

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setShowCreateDialog(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
        >
          <PlusIcon className="h-4 w-4" /> New
        </button>
        <button onClick={handleRelease} disabled={!canRelease}
          className="inline-flex items-center gap-1.5 rounded-md border border-blue-300 bg-white px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-40 disabled:cursor-not-allowed">
          <PlayIcon className="h-4 w-4" /> Release
        </button>
        <button onClick={handleComplete} disabled={!canComplete}
          className="inline-flex items-center gap-1.5 rounded-md border border-green-300 bg-white px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-50 disabled:opacity-40 disabled:cursor-not-allowed">
          <CheckIcon className="h-4 w-4" /> Complete
        </button>
        <button onClick={() => { if (selectedOrder) setEditingOrder(selectedOrder); }} disabled={!canEdit}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
          <PencilSquareIcon className="h-4 w-4" /> Edit
        </button>
        <button onClick={handleClose} disabled={!canClose}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
          <LockClosedIcon className="h-4 w-4" /> Close
        </button>
      </div>

      {/* Status filter */}
      <div className="flex gap-4 items-end">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Status</label>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field">
            <option value="">All</option>
            <option value="created">Created</option>
            <option value="released">Released</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <button onClick={refresh}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
          <ArrowPathIcon className="h-4 w-4" /> Refresh
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        {isLoading ? (
          <p className="p-5 text-gray-400">Loading…</p>
        ) : !orders || orders.length === 0 ? (
          <p className="p-5 text-gray-400">No orders found</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 px-3 w-6"></th>
                <th className="py-2 px-3">Order #</th>
                <th className="py-2 px-3">Product</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Priority</th>
                <th className="py-2 px-3">Ordered</th>
                <th className="py-2 px-3">Completed</th>
                <th className="py-2 px-3">Scrapped</th>
                <th className="py-2 px-3">ERP Ref</th>
                <th className="py-2 px-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const expanded = expandedOrderId === o.id;
                const selected = selectedOrderId === o.id;
                return (
                  <OrderRow
                    key={o.id} order={o} expanded={expanded} selected={selected}
                    productMap={productMap}
                    onToggle={() => toggleExpand(o.id)}
                    onSelect={() => handleSelect(o.id)}
                    onRefresh={refresh}
                  />
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Create dialog */}
      {showCreateDialog && (
        <OrderFormDialog
          onClose={() => setShowCreateDialog(false)}
          onSaved={() => { setShowCreateDialog(false); refresh(); }}
        />
      )}

      {/* Edit dialog */}
      {editingOrder && (
        <OrderFormDialog
          order={editingOrder}
          onClose={() => setEditingOrder(null)}
          onSaved={() => { setEditingOrder(null); refresh(); }}
        />
      )}
    </div>
  );
}

function OrderRow({ order: o, expanded, selected, productMap, onToggle, onSelect, onRefresh }: {
  order: ProductionOrder; expanded: boolean; selected: boolean;
  productMap: Record<string, Product>;
  onToggle: () => void; onSelect: () => void; onRefresh: () => void;
}) {
  const product = productMap[o.product_id];
  return (
    <>
      <tr
        className={`border-b cursor-pointer transition-colors ${selected ? "bg-indigo-50" : "hover:bg-gray-50"}`}
        onClick={onSelect}
      >
        <td className="py-2 px-3">
          <button onClick={(e) => { e.stopPropagation(); onToggle(); }} className="p-0.5">
            {expanded
              ? <ChevronDownIcon className="h-4 w-4 text-gray-400" />
              : <ChevronRightIcon className="h-4 w-4 text-gray-400" />}
          </button>
        </td>
        <td className="py-2 px-3 font-mono">{o.order_number}</td>
        <td className="py-2 px-3 text-gray-700">{product?.name ?? "—"}</td>
        <td className="py-2 px-3"><StatusBadge status={o.status} /></td>
        <td className="py-2 px-3">{o.priority}</td>
        <td className="py-2 px-3">{o.quantity_ordered}{product?.uom_symbol ? ` ${product.uom_symbol}` : ""}</td>
        <td className="py-2 px-3">{o.quantity_completed}{product?.uom_symbol ? ` ${product.uom_symbol}` : ""}</td>
        <td className="py-2 px-3">{o.quantity_scrapped}{product?.uom_symbol ? ` ${product.uom_symbol}` : ""}</td>
        <td className="py-2 px-3 text-xs text-gray-400">{o.erp_reference ?? "—"}</td>
        <td className="py-2 px-3 text-xs text-gray-400">
          {new Date(o.created_at).toLocaleString()}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-gray-50">
          <td colSpan={10} className="px-3 py-3">
            <OrderDetail order={o} product={product} onRefresh={onRefresh} />
          </td>
        </tr>
      )}
    </>
  );
}

function OrderDetail({ order, product, onRefresh }: { order: ProductionOrder; product?: Product; onRefresh: () => void }) {
  const [showCreateLot, setShowCreateLot] = useState(false);
  const [showCreateUnit, setShowCreateUnit] = useState(false);
  const canCreate = order.status === "released" || order.status === "in_progress";
  const productType = product?.product_type;
  const showLotButton = productType !== "discrete";
  const showUnitButton = productType !== "process";

  const { data: units = [] } = useQuery<Unit[]>({
    queryKey: ["order-wip", "units", order.id],
    queryFn: () => fetchUnits({ order_id: order.id }),
  });

  const { data: lots = [] } = useQuery<Lot[]>({
    queryKey: ["order-wip", "lots", order.id],
    queryFn: () => fetchLots({ order_id: order.id }),
  });

  return (
    <div className="space-y-3">
      {/* Create buttons */}
      {canCreate && (
        <div className="flex gap-2">
          {showLotButton && (
            <button
              onClick={() => { setShowCreateLot(!showCreateLot); setShowCreateUnit(false); }}
              className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded-md px-2 py-1"
            >
              <PlusIcon className="h-3.5 w-3.5" /> Create Lot
            </button>
          )}
          {showUnitButton && (
            <button
              onClick={() => { setShowCreateUnit(!showCreateUnit); setShowCreateLot(false); }}
              className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded-md px-2 py-1"
            >
              <PlusIcon className="h-3.5 w-3.5" /> Create Unit
            </button>
          )}
        </div>
      )}

      {showCreateLot && <CreateLotForm order={order} uom={product?.uom_symbol ?? null} onCreated={onRefresh} />}
      {showCreateUnit && <CreateUnitForm order={order} onCreated={onRefresh} />}

      {/* Lots */}
      {lots.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Lots ({lots.length})</h5>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-left text-gray-400 border-b">
                <th className="py-1 px-2">Lot #</th>
                <th className="py-1 px-2">Qty</th>
                <th className="py-1 px-2">Status</th>
                <th className="py-1 px-2">Step</th>
              </tr>
            </thead>
            <tbody>
              {lots.map((l) => (
                <tr key={l.id} className="border-b">
                  <td className="py-1 px-2 font-mono">{l.lot_number}</td>
                  <td className="py-1 px-2">{l.quantity}{product?.uom_symbol ? ` ${product.uom_symbol}` : ""}</td>
                  <td className="py-1 px-2"><WipBadge status={l.status} /></td>
                  <td className="py-1 px-2 text-gray-500">{l.current_step_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Units */}
      {units.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Units ({units.length})</h5>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-left text-gray-400 border-b">
                <th className="py-1 px-2">Serial #</th>
                <th className="py-1 px-2">Status</th>
                <th className="py-1 px-2">Step</th>
              </tr>
            </thead>
            <tbody>
              {units.map((u) => (
                <tr key={u.id} className="border-b">
                  <td className="py-1 px-2 font-mono">{u.serial_number}</td>
                  <td className="py-1 px-2"><WipBadge status={u.status} /></td>
                  <td className="py-1 px-2 text-gray-500">{u.current_step_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {lots.length === 0 && units.length === 0 && !showCreateLot && !showCreateUnit && (
        <p className="text-xs text-gray-400">No lots or units for this order</p>
      )}
    </div>
  );
}

function CreateLotForm({ order, uom, onCreated }: { order: ProductionOrder; uom: string | null; onCreated: () => void }) {
  const remaining = order.quantity_ordered - order.quantity_completed - order.quantity_scrapped;
  const [quantity, setQuantity] = useState<string>(String(remaining > 0 ? remaining : 1));
  const [lotNumber, setLotNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const submittingRef = useRef(false);

  const handleCreate = async () => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const lot = await createLot({
        order_id: order.id,
        product_id: order.product_id,
        quantity: parseInt(quantity),
        ...(lotNumber ? { lot_number: lotNumber } : {}),
      });
      setSuccess(`Lot ${lot.lot_number} created`);
      setLotNumber("");
      onCreated();
    } catch (err: unknown) {
      const m = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ?? "Failed to create lot";
      setError(m);
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  };

  return (
    <div className="bg-indigo-50 rounded-md p-3 space-y-2">
      <p className="text-sm font-medium text-gray-700">Create Lot</p>
      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">
            Quantity{uom ? ` (${uom})` : ""}
          </label>
          <input type="number" min="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="input-field w-28" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Lot # (optional)</label>
          <input type="text" value={lotNumber} onChange={(e) => setLotNumber(e.target.value)} placeholder="Auto-generate" className="input-field w-48" />
        </div>
        <button onClick={handleCreate} disabled={loading || !quantity || parseInt(quantity) <= 0} className="btn-primary text-sm">
          {loading ? "Creating…" : "Create Lot"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {success && <p className="text-xs text-green-600">{success}</p>}
    </div>
  );
}

function CreateUnitForm({ order, onCreated }: { order: ProductionOrder; onCreated: () => void }) {
  const [serialNumber, setSerialNumber] = useState("");
  const [count, setCount] = useState("1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const submittingRef = useRef(false);

  const handleCreate = async () => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const n = parseInt(count) || 1;
      const created: string[] = [];
      for (let i = 0; i < n; i++) {
        const unit = await createUnit({
          order_id: order.id,
          product_id: order.product_id,
          ...(n === 1 && serialNumber ? { serial_number: serialNumber } : {}),
        });
        created.push(unit.serial_number);
      }
      setSuccess(`Created ${created.length} unit(s): ${created.join(", ")}`);
      setSerialNumber("");
      onCreated();
    } catch (err: unknown) {
      const m = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ?? "Failed to create unit";
      setError(m);
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  };

  return (
    <div className="bg-indigo-50 rounded-md p-3 space-y-2">
      <p className="text-sm font-medium text-gray-700">Create Unit(s)</p>
      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">How many</label>
          <input type="number" min="1" max="100" value={count} onChange={(e) => setCount(e.target.value)} className="input-field w-20" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Serial # (single unit only)</label>
          <input
            type="text"
            value={serialNumber}
            onChange={(e) => setSerialNumber(e.target.value)}
            placeholder="Auto-generate"
            className="input-field w-48"
            disabled={parseInt(count) > 1}
          />
        </div>
        <button onClick={handleCreate} disabled={loading || !count || parseInt(count) <= 0} className="btn-primary text-sm">
          {loading ? "Creating…" : "Create Unit(s)"}
        </button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {success && <p className="text-xs text-green-600">{success}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    created: "bg-gray-100 text-gray-700",
    released: "bg-blue-100 text-blue-700",
    in_progress: "bg-yellow-100 text-yellow-700",
    completed: "bg-green-100 text-green-700",
    closed: "bg-purple-100 text-purple-700",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function WipBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "bg-blue-100 text-blue-700",
    in_process: "bg-yellow-100 text-yellow-700",
    completed: "bg-green-100 text-green-700",
    scrapped: "bg-red-100 text-red-700",
    on_hold: "bg-orange-100 text-orange-700",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {status.replace("_", " ")}
    </span>
  );
}

/* ── Order Create / Edit Dialog ─────────────────────────────────── */

function OrderFormDialog({ order, onClose, onSaved }: {
  order?: ProductionOrder;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!order;
  const [orderNumber, setOrderNumber] = useState(order?.order_number ?? "");
  const [productId, setProductId] = useState(order?.product_id ?? "");
  const [quantityOrdered, setQuantityOrdered] = useState(String(order?.quantity_ordered ?? ""));
  const [priority, setPriority] = useState(String(order?.priority ?? 0));
  const [erpReference, setErpReference] = useState(order?.erp_reference ?? "");
  const [notes, setNotes] = useState(order?.notes ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: products = [] } = useQuery<Product[]>({
    queryKey: ["products"],
    queryFn: fetchProducts,
  });

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      if (isEdit) {
        await updateOrder(order.id, {
          order_number: orderNumber,
          product_id: productId,
          quantity_ordered: parseInt(quantityOrdered),
          priority: parseInt(priority) || 0,
          erp_reference: erpReference || null,
          notes: notes || null,
        });
      } else {
        await createOrder({
          order_number: orderNumber,
          product_id: productId,
          quantity_ordered: parseInt(quantityOrdered),
          priority: parseInt(priority) || 0,
          erp_reference: erpReference || null,
          notes: notes || null,
        });
      }
      onSaved();
    } catch (err: unknown) {
      const m = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ?? "Failed to save order";
      setError(m);
    } finally {
      setLoading(false);
    }
  };

  const selectedProduct = products.find((p) => p.id === productId);
  const selectedUom = selectedProduct?.uom_symbol ?? null;

  const valid = orderNumber.trim() && productId && quantityOrdered && parseInt(quantityOrdered) > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">
            {isEdit ? "Edit Order" : "New Production Order"}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* Order Number */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Order Number</label>
            <input type="text" value={orderNumber} onChange={(e) => setOrderNumber(e.target.value)}
              className="input-field w-full" placeholder="e.g. ORD-001" />
          </div>

          {/* Product */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Product</label>
            <select value={productId} onChange={(e) => setProductId(e.target.value)} className="input-field w-full">
              <option value="">Select a product…</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
              ))}
            </select>
          </div>

          {/* Quantity & Priority */}
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Quantity{selectedUom ? ` (${selectedUom})` : ""}
              </label>
              <input type="number" min="1" value={quantityOrdered} onChange={(e) => setQuantityOrdered(e.target.value)}
                className="input-field w-full" />
            </div>
            <div className="w-28">
              <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <input type="number" min="0" value={priority} onChange={(e) => setPriority(e.target.value)}
                className="input-field w-full" />
            </div>
          </div>

          {/* ERP Reference */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ERP Reference</label>
            <input type="text" value={erpReference} onChange={(e) => setErpReference(e.target.value)}
              className="input-field w-full" placeholder="Optional" />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)}
              className="input-field w-full" rows={2} placeholder="Optional" />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t bg-gray-50 rounded-b-lg">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900">
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={!valid || loading}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? "Saving…" : isEdit ? "Save Changes" : "Create Order"}
          </button>
        </div>
      </div>
    </div>
  );
}
