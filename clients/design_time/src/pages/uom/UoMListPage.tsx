/**
 * UoM List Page — table of all units with type filter,
 * create/edit dialog, delete, and conversion panel.
 */

import { useState, useMemo } from "react";
import { PlusIcon, TrashIcon, PencilSquareIcon } from "@heroicons/react/24/outline";
import { useUoMs, useDeleteUoM } from "../../hooks/useUoM";
import type { UoM } from "../../types";
import { UOM_TYPES } from "../../types";
import UoMFormDialog from "./UoMFormDialog";
import UoMConvertPanel from "./UoMConvertPanel";

const TYPE_LABELS: Record<string, string> = {
  mass: "Mass",
  length: "Length",
  time: "Time",
  temperature: "Temperature",
  electrical: "Electrical",
  force: "Force",
  amount_of_substance: "Amount of Substance",
  luminous_intensity: "Luminous Intensity",
  other: "Other",
};

const CLASS_BADGE: Record<string, string> = {
  scalar: "bg-blue-100 text-blue-700",
  quotient: "bg-purple-100 text-purple-700",
  product: "bg-amber-100 text-amber-700",
  power: "bg-green-100 text-green-700",
};

function uomFormula(uom: UoM): string {
  if (uom.uom_class === "quotient" && uom.left_uom_symbol && uom.right_uom_symbol)
    return `${uom.left_uom_symbol} ÷ ${uom.right_uom_symbol}`;
  if (uom.uom_class === "product" && uom.left_uom_symbol && uom.right_uom_symbol)
    return `${uom.left_uom_symbol} × ${uom.right_uom_symbol}`;
  if (uom.uom_class === "power" && uom.left_uom_symbol && uom.exponent)
    return `${uom.left_uom_symbol}^${uom.exponent}`;
  return "—";
}

export default function UoMListPage() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [editingUoM, setEditingUoM] = useState<UoM | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading, error } = useUoMs();
  const deleteMut = useDeleteUoM();

  const uoms = data?.data ?? [];

  // Apply client-side type filter
  const filtered = useMemo(
    () => (typeFilter ? uoms.filter((u) => u.uom_type === typeFilter) : uoms),
    [uoms, typeFilter],
  );

  const handleDelete = (uom: UoM) => {
    if (uom.is_builtin) return;
    if (!confirm(`Delete unit "${uom.symbol}"?`)) return;
    deleteMut.mutate(uom.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Units of Measure</h1>
          <p className="text-sm text-gray-500 mt-1">
            Define units, conversion factors, and composite units.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Unit
        </button>
      </div>

      {/* Type filter — fixed 5 types */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">Filter by type:</label>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All types</option>
          {UOM_TYPES.map((t) => (
            <option key={t} value={t}>{TYPE_LABELS[t] ?? t}</option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {filtered.length} unit{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error states */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading units…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 space-y-1">
          <p className="font-semibold">Failed to load units of measure</p>
          <p className="text-xs text-red-600 font-mono break-all">
            {(() => {
              const e = error as { response?: { status?: number; data?: { error?: { code?: string; message?: string; details?: Record<string, unknown> } } }; message?: string };
              if (e.response) {
                const { status, data } = e.response;
                const errObj = data?.error;
                return `${status} — ${errObj?.code ?? "UNKNOWN"}: ${errObj?.message ?? "No message"}`
                  + (errObj?.details ? ` (${JSON.stringify(errObj.details)})` : "");
              }
              return e.message ?? String(error);
            })()}
          </p>
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Symbol
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Class
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Formula
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Multiplier
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Offset
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Built-in
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((uom) => (
                <tr
                  key={uom.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                    {uom.symbol}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">
                    {uom.name}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                      {TYPE_LABELS[uom.uom_type] ?? uom.uom_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${CLASS_BADGE[uom.uom_class] ?? "bg-gray-100 text-gray-600"}`}>
                      {uom.uom_class}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-sm font-mono text-gray-700">
                    {uomFormula(uom)}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-700">
                    {uom.uom_class === "scalar" ? uom.multiplier : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-700">
                    {uom.uom_class === "scalar" ? uom.offset : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {uom.is_builtin ? (
                      <span className="text-xs text-green-600 font-medium">✓</span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditingUoM(uom)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(uom)}
                        disabled={uom.is_builtin}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        title={uom.is_builtin ? "Built-in units cannot be deleted" : "Delete"}
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-sm text-gray-400">
                    No units found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Conversion panel */}
      <UoMConvertPanel uoms={uoms} />

      {/* Create / Edit dialog */}
      {(showCreate || editingUoM) && (
        <UoMFormDialog
          uom={editingUoM}
          onClose={() => {
            setShowCreate(false);
            setEditingUoM(null);
          }}
        />
      )}
    </div>
  );
}

