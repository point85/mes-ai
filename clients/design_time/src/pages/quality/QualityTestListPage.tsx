/**
 * Quality Test List Page — table of quality test definitions with type filter and CRUD.
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { useQualityTests, useDeleteQualityTest } from "../../hooks/useQuality";
import type { QualityTest } from "../../types";
import QualityTestFormDialog from "./QualityTestFormDialog";

const TEST_TYPES = ["inline", "offline", "destructive"];

const typeColors: Record<string, string> = {
  inline: "bg-green-50 text-green-700",
  offline: "bg-blue-50 text-blue-700",
  destructive: "bg-red-50 text-red-700",
};

export default function QualityTestListPage() {
  const [editing, setEditing] = useState<QualityTest | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");

  const { data, isLoading, error } = useQualityTests();
  const deleteMut = useDeleteQualityTest();

  const tests = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!typeFilter) return tests;
    return tests.filter((t) => t.test_type === typeFilter);
  }, [tests, typeFilter]);

  const handleDelete = (t: QualityTest) => {
    if (!confirm(`Delete quality test "${t.name}"?`)) return;
    deleteMut.mutate(t.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quality Tests</h1>
          <p className="text-sm text-gray-500 mt-1">
            Define inline, offline, and destructive quality test specifications.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Test
        </button>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">
          Filter by type:
        </label>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All types</option>
          {TEST_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {filtered.length} test{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading quality tests…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load quality tests. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
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
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Description
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((t) => (
                <tr
                  key={t.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                    {t.code}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">
                    {t.name}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        typeColors[t.test_type] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {t.test_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500 max-w-xs truncate">
                    {t.description ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditing(t)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(t)}
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
                    colSpan={5}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No quality tests found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editing) && (
        <QualityTestFormDialog
          qualityTest={editing}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
