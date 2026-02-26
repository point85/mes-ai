/**
 * Non-Conformance List Page — table with status badges, type filter, and workflow actions.
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
} from "@heroicons/react/24/outline";
import {
  useNonConformances,
  useUpdateNonConformance,
} from "../../hooks/useQuality";
import type { NonConformance } from "../../types";
import NCFormDialog from "./NCFormDialog";

const NC_STATUSES = ["open", "investigating", "resolved", "closed"];

const statusColors: Record<string, string> = {
  open: "bg-red-50 text-red-700",
  investigating: "bg-amber-50 text-amber-700",
  resolved: "bg-green-50 text-green-700",
  closed: "bg-gray-200 text-gray-500",
};

export default function NCListPage() {
  const [editing, setEditing] = useState<NonConformance | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading, error } = useNonConformances();
  const updateMut = useUpdateNonConformance();

  const ncs = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!statusFilter) return ncs;
    return ncs.filter((nc) => nc.status === statusFilter);
  }, [ncs, statusFilter]);

  const handleResolve = (nc: NonConformance) => {
    const disposition = prompt(
      "Enter disposition (rework, scrap, use_as_is, return):",
    );
    if (!disposition) return;
    updateMut.mutate({
      id: nc.id,
      status: "resolved",
      disposition,
    });
  };

  const handleClose = (nc: NonConformance) => {
    updateMut.mutate({ id: nc.id, status: "closed" });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Non-Conformances
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Track quality deviations through the investigation and resolution
            workflow.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New NC
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
          {NC_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {filtered.length} NC{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading non-conformances…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load non-conformances. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Disposition
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Description
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Created
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((nc) => (
                <tr
                  key={nc.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-2.5">
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                      {nc.nc_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        statusColors[nc.status] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {nc.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-600">
                    {nc.disposition ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500 max-w-xs truncate">
                    {nc.description}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {new Date(nc.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {nc.status !== "resolved" && nc.status !== "closed" && (
                        <button
                          onClick={() => handleResolve(nc)}
                          className="rounded px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-50 transition-colors"
                          title="Resolve"
                        >
                          Resolve
                        </button>
                      )}
                      {nc.status !== "closed" && (
                        <button
                          onClick={() => handleClose(nc)}
                          className="rounded px-2 py-1 text-xs font-medium text-gray-500 hover:bg-gray-100 transition-colors"
                          title="Close"
                        >
                          Close
                        </button>
                      )}
                      <button
                        onClick={() => setEditing(nc)}
                        disabled={nc.status === "closed"}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No non-conformances found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editing) && (
        <NCFormDialog
          nc={editing}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
