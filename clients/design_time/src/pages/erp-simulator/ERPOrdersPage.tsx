import { useEffect, useState } from "react";
import {
  readProductionOrders,
  createProductionOrder,
  updateProductionOrder,
  deleteProductionOrder,
  readProducts,
  readProductRoutes,
  type DBProductionOrder,
  type DBProduct,
  type DBRoute,
} from "../../api/erp";

interface CreateForm {
  product_id: string;
  route_id: string;
  count: number;
  quantity_ordered: number;
  priority: number;
}

const defaultCreate: CreateForm = {
  product_id: "",
  route_id: "",
  count: 3,
  quantity_ordered: 100,
  priority: 0,
};

interface EditDraft {
  order_number: string;
  quantity_ordered: number;
  priority: number;
  erp_reference: string;
  notes: string;
}

export default function ERPOrdersPage() {
  const [data, setData] = useState<DBProductionOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [products, setProducts] = useState<DBProduct[]>([]);
  const [routes, setRoutes] = useState<DBRoute[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateForm>(defaultCreate);
  const [creating, setCreating] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    loadOrders();
    readProducts()
      .then(setProducts)
      .catch(() => {});
  }, []);

  const loadOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await readProductionOrders());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!form.product_id) {
      setRoutes([]);
      setForm((f) => ({ ...f, route_id: "" }));
      return;
    }
    readProductRoutes(form.product_id)
      .then((r) => {
        setRoutes(r);
        const def = r.find((rt) => rt.is_default);
        setForm((f) => ({ ...f, route_id: def?.id ?? r[0]?.id ?? "" }));
      })
      .catch(() => setRoutes([]));
  }, [form.product_id]);

  const handleCreate = async () => {
    if (!form.product_id) return;
    setCreating(true);
    setError(null);
    const product = products.find((p) => p.id === form.product_id);
    const prefix = product ? product.code : "PO";
    const ts = Date.now().toString(36).toUpperCase();
    try {
      const created: DBProductionOrder[] = [];
      for (let i = 1; i <= form.count; i++) {
        const order = await createProductionOrder({
          order_number: `${prefix}-${ts}-${String(i).padStart(3, "0")}`,
          product_id: form.product_id,
          route_id: form.route_id || null,
          quantity_ordered: form.quantity_ordered,
          priority: form.priority,
        });
        created.push(order);
      }
      setData((prev) => [...created, ...prev]);
      setShowCreate(false);
      setForm(defaultCreate);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (row: DBProductionOrder) => {
    setEditId(row.id);
    setEditDraft({
      order_number: row.order_number,
      quantity_ordered: row.quantity_ordered,
      priority: row.priority,
      erp_reference: row.erp_reference ?? "",
      notes: row.notes ?? "",
    });
  };

  const cancelEdit = () => {
    setEditId(null);
    setEditDraft(null);
  };

  const handleSave = async () => {
    if (!editId || !editDraft) return;
    setSaving(editId);
    setError(null);
    try {
      const updated = await updateProductionOrder(editId, {
        order_number: editDraft.order_number,
        quantity_ordered: editDraft.quantity_ordered,
        priority: editDraft.priority,
        erp_reference: editDraft.erp_reference || null,
        notes: editDraft.notes || null,
      });
      setData((prev) => prev.map((o) => (o.id === editId ? updated : o)));
      cancelEdit();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(null);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    setError(null);
    try {
      await deleteProductionOrder(id);
      setData((prev) => prev.filter((o) => o.id !== id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  };

  const fmtDate = (v: string | null) =>
    v ? new Date(v).toLocaleDateString() : "\u2014";

  const inp =
    "px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={loadOrders}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Loading\u2026" : "Refresh"}
        </button>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700"
        >
          {showCreate ? "Cancel" : "+ Create Orders"}
        </button>
        {data.length > 0 && (
          <span className="text-sm text-gray-500">{data.length} orders</span>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>
      )}

      {showCreate && (
        <div className="p-4 bg-white rounded-lg border space-y-3">
          <h3 className="font-medium text-sm text-gray-700">Create Production Orders</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <label className="space-y-1">
              <span className="text-xs text-gray-500">Product *</span>
              <select
                value={form.product_id}
                onChange={(e) => setForm((f) => ({ ...f, product_id: e.target.value }))}
                className={inp + " w-full"}
              >
                <option value="">&mdash; select &mdash;</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} &mdash; {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs text-gray-500">Route</span>
              <select
                value={form.route_id}
                onChange={(e) => setForm((f) => ({ ...f, route_id: e.target.value }))}
                className={inp + " w-full"}
                disabled={routes.length === 0}
              >
                <option value="">&mdash; none &mdash;</option>
                {routes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} v{r.version}
                    {r.is_default ? " (default)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs text-gray-500"># Orders</span>
              <input
                type="number"
                min={1}
                max={50}
                value={form.count}
                onChange={(e) => setForm((f) => ({ ...f, count: Math.max(1, parseInt(e.target.value) || 1) }))}
                className={inp + " w-full"}
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-gray-500">Qty per Order</span>
              <input
                type="number"
                min={1}
                value={form.quantity_ordered}
                onChange={(e) => setForm((f) => ({ ...f, quantity_ordered: Math.max(1, parseInt(e.target.value) || 1) }))}
                className={inp + " w-full"}
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-gray-500">Priority</span>
              <input
                type="number"
                min={0}
                value={form.priority}
                onChange={(e) => setForm((f) => ({ ...f, priority: Math.max(0, parseInt(e.target.value) || 0) }))}
                className={inp + " w-full"}
              />
            </label>
          </div>
          <button
            onClick={handleCreate}
            disabled={!form.product_id || creating}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
          >
            {creating ? "Creating\u2026" : `Create ${form.count} Order${form.count !== 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {data.length === 0 && !loading ? (
        <div className="text-center py-8 text-gray-500 bg-white rounded-lg border">
          No production orders yet. Click &lsquo;+ Create Orders&rsquo; to add some.
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg border">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Order #", "ERP Ref", "Status", "Qty Ordered", "Qty Done", "Qty Scrap", "Priority", "Planned Start", "Planned End", "Actions"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data.map((row) => {
                const isEditing = editId === row.id;
                const busyDel = deleting === row.id;
                const busySave = saving === row.id;

                if (isEditing && editDraft) {
                  return (
                    <tr key={row.id} className="bg-yellow-50">
                      <td className="px-3 py-2">
                        <input value={editDraft.order_number} onChange={(e) => setEditDraft((d) => d ? { ...d, order_number: e.target.value } : d)} className={inp + " w-28"} />
                      </td>
                      <td className="px-3 py-2">
                        <input value={editDraft.erp_reference} onChange={(e) => setEditDraft((d) => d ? { ...d, erp_reference: e.target.value } : d)} className={inp + " w-24"} />
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">{row.status}</td>
                      <td className="px-3 py-2">
                        <input type="number" min={1} value={editDraft.quantity_ordered} onChange={(e) => setEditDraft((d) => d ? { ...d, quantity_ordered: parseInt(e.target.value) || 1 } : d)} className={inp + " w-20"} />
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">{row.quantity_completed}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{row.quantity_scrapped}</td>
                      <td className="px-3 py-2">
                        <input type="number" min={0} value={editDraft.priority} onChange={(e) => setEditDraft((d) => d ? { ...d, priority: parseInt(e.target.value) || 0 } : d)} className={inp + " w-16"} />
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">{fmtDate(row.planned_start)}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{fmtDate(row.planned_end)}</td>
                      <td className="px-3 py-2 whitespace-nowrap space-x-1">
                        <button onClick={handleSave} disabled={busySave} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50">
                          {busySave ? "\u2026" : "Save"}
                        </button>
                        <button onClick={cancelEdit} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
                          Cancel
                        </button>
                      </td>
                    </tr>
                  );
                }

                return (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 whitespace-nowrap">{row.order_number}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.erp_reference ?? "\u2014"}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.status}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.quantity_ordered}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.quantity_completed}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.quantity_scrapped}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{row.priority}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{fmtDate(row.planned_start)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{fmtDate(row.planned_end)}</td>
                    <td className="px-3 py-2 whitespace-nowrap space-x-1">
                      <button onClick={() => startEdit(row)} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200">Edit</button>
                      <button onClick={() => handleDelete(row.id)} disabled={busyDel} className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50">
                        {busyDel ? "\u2026" : "Delete"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
