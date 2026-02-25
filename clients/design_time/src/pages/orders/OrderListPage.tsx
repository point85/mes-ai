/**
 * Production Order List Page — table with status badges, filters, and workflow actions.
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  TrashIcon,
  PencilSquareIcon,
  PlayIcon,
  CheckIcon,
  LockClosedIcon,
} from "@heroicons/react/24/outline";
import {
  useOrders,
  useDeleteOrder,
  useReleaseOrder,
  useCompleteOrder,
  useCloseOrder,
} from "../../hooks/useProduction";
import type { ProductionOrder } from "../../types";
import OrderFormDialog from "./OrderFormDialog";

const ORDER_STATUSES = [
  "created",
  "released",
  "in_progress",
  "completed",
  "closed",
];

const statusColors: Record<string, string> = {
  created: "bg-gray-100 text-gray-700",
  released: "bg-blue-50 text-blue-700",
  in_progress: "bg-amber-50 text-amber-700",
  completed: "bg-green-50 text-green-700",
  closed: "bg-gray-200 text-gray-500",
};

export default function OrderListPage() {
  const [editing, setEditing] = useState<ProductionOrder | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading, error } = useOrders();
  const deleteMut = useDeleteOrder();
  const releaseMut = useReleaseOrder();
  const completeMut = useCompleteOrder();
  const closeMut = useCloseOrder();

  const orders = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!statusFilter) return orders;
    return orders.filter((o) => o.status === statusFilter);
  }, [orders, statusFilter]);

  const handleDelete = (o: ProductionOrder) => {
    if (!confirm(`Delete order "${o.order_number}"?`)) return;
    deleteMut.mutate(o.id);
  };

  const handleRelease = (o: ProductionOrder) => {
    releaseMut.mutate({ id: o.id });
  };

  const handleComplete = (o: ProductionOrder) => {
    completeMut.mutate({ id: o.id });
  };

  const handleClose = (o: ProductionOrder) => {
    closeMut.mutate({ id: o.id });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Production Orders
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Create and manage production orders — release, complete, and close
            workflow.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Order
        </button>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">
          Filter by status:
        </label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All statuses</option>
          {ORDER_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {filtered.length} order{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading orders…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load orders. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Order #
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Qty Ordered
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Completed
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Scrapped
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Priority
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((o) => (
                <tr
                  key={o.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                    {o.order_number}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        statusColors[o.status] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {o.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-700">
                    {o.quantity_ordered}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-700">
                    {o.quantity_completed}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-700">
                    {o.quantity_scrapped}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-600">
                    {o.priority}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {/* Workflow actions based on status */}
                      {o.status === "created" && (
                        <button
                          onClick={() => handleRelease(o)}
                          className="rounded p-1 text-blue-500 hover:bg-blue-50 transition-colors"
                          title="Release"
                        >
                          <PlayIcon className="h-4 w-4" />
                        </button>
                      )}
                      {(o.status === "released" ||
                        o.status === "in_progress") && (
                        <button
                          onClick={() => handleComplete(o)}
                          className="rounded p-1 text-green-600 hover:bg-green-50 transition-colors"
                          title="Complete"
                        >
                          <CheckIcon className="h-4 w-4" />
                        </button>
                      )}
                      {o.status !== "closed" && (
                        <button
                          onClick={() => handleClose(o)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                          title="Close"
                        >
                          <LockClosedIcon className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => setEditing(o)}
                        disabled={o.status === "closed"}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(o)}
                        disabled={
                          o.status === "in_progress" ||
                          o.status === "completed"
                        }
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Delete"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No orders found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editing) && (
        <OrderFormDialog
          order={editing}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
