/**
 * Data Definition List Page — table of data collection definitions with CRUD.
 * Supports filtering by data type and source.
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  TrashIcon,
  PencilSquareIcon,
} from "@heroicons/react/24/outline";
import {
  useDataDefinitions,
  useDeleteDataDefinition,
} from "../../hooks/useDataCollection";
import type { DataDefinition } from "../../types";
import DataDefFormDialog from "./DataDefFormDialog";

const DATA_TYPES = ["numeric", "string", "boolean", "enum"];
const DATA_SOURCES = ["manual", "equipment", "sensor"];

export default function DataDefListPage() {
  const [editing, setEditing] = useState<DataDefinition | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");

  const { data, isLoading, error } = useDataDefinitions();
  const deleteMut = useDeleteDataDefinition();

  const defs = data?.data ?? [];

  const filtered = useMemo(() => {
    let result = defs;
    if (typeFilter) result = result.filter((d) => d.data_type === typeFilter);
    if (sourceFilter)
      result = result.filter((d) => d.source === sourceFilter);
    return result;
  }, [defs, typeFilter, sourceFilter]);

  const handleDelete = (d: DataDefinition) => {
    if (!confirm(`Delete definition "${d.code}"?`)) return;
    deleteMut.mutate(d.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Data Definitions
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Define data collection points — what to measure, limits, and
            validation rules.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Definition
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Type:</label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All</option>
            {DATA_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Source:</label>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All</option>
            {DATA_SOURCES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <span className="text-xs text-gray-400">
          {filtered.length} definition{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading definitions…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load data definitions. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Code
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Data Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Source
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  UoM
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Limits
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Req
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((d) => (
                <tr
                  key={d.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                    {d.code}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">
                    {d.name}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                      {d.data_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        d.source === "manual"
                          ? "bg-gray-100 text-gray-600"
                          : d.source === "equipment"
                            ? "bg-blue-50 text-blue-700"
                            : "bg-purple-50 text-purple-700"
                      }`}
                    >
                      {d.source}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm font-mono text-gray-600">
                    {d.uom_symbol ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-center text-xs font-mono text-gray-500">
                    {d.lower_limit != null || d.upper_limit != null
                      ? `${d.lower_limit ?? "—"} – ${d.upper_limit ?? "—"}`
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {d.is_required ? (
                      <span className="text-xs text-green-600 font-medium">
                        ✓
                      </span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditing(d)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(d)}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
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
                    colSpan={8}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No data definitions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editing) && (
        <DataDefFormDialog
          definition={editing}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
