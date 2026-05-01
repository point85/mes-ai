/**
 * Material Lot List Page — lists material lots with filters (material, status)
 * and CRUD via MaterialLotFormDialog.
 *
 * Lots are inbound inventory: the materials *available* for consumption.
 * Distinct from InventoryBalances (which show quantities at storage locations)
 * and InventoryTransactions (which are the audit log).
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
} from "@heroicons/react/24/outline";
import { useMaterialLots, useMaterials } from "../../hooks/useMaterial";
import type { MaterialLot } from "../../types";
import MaterialLotFormDialog from "./MaterialLotFormDialog";

const LOT_STATUSES = ["available", "reserved", "consumed", "expired"];

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return iso.slice(0, 10);
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "available":
      return "bg-green-50 text-green-700";
    case "reserved":
      return "bg-blue-50 text-blue-700";
    case "consumed":
      return "bg-gray-100 text-gray-600";
    case "expired":
      return "bg-red-50 text-red-700";
    default:
      return "bg-gray-50 text-gray-600";
  }
}

export default function MaterialLotListPage() {
  const [editing, setEditing] = useState<MaterialLot | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [materialFilter, setMaterialFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data: matResp } = useMaterials();
  const materials = (matResp?.data ?? [])
    .slice()
    .sort((a, b) => a.code.localeCompare(b.code));
  const matMap = useMemo(
    () => new Map(materials.map((m) => [m.id, m])),
    [materials],
  );

  const { data, isLoading, error } = useMaterialLots(
    materialFilter || undefined,
    statusFilter || undefined,
  );
  const lots = data?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Material Lots</h1>
          <p className="text-sm text-gray-500 mt-1">
            Inbound inventory lots of raw, intermediate, and finished materials.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Lot
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm font-medium text-gray-700">Material:</label>
        <select
          value={materialFilter}
          onChange={(e) => setMaterialFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All materials</option>
          {materials.map((m) => (
            <option key={m.id} value={m.id}>
              {m.code} — {m.name}
            </option>
          ))}
        </select>

        <label className="text-sm font-medium text-gray-700">Status:</label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">All statuses</option>
          {LOT_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <span className="text-xs text-gray-400">
          {lots.length} lot{lots.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="text-sm text-gray-500">Loading lots…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load material lots. Is the server running?
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Lot #
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Material
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  On Hand
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Reserved
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Received
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Expiry
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Supplier
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {lots.map((lot) => {
                const mat = matMap.get(lot.material_id);
                return (
                  <tr key={lot.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                      {lot.lot_number}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">
                      {mat ? (
                        <>
                          <span className="font-mono text-gray-900">
                            {mat.code}
                          </span>{" "}
                          <span className="text-gray-500">— {mat.name}</span>
                        </>
                      ) : (
                        <span className="text-gray-400">(unknown)</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-900">
                      {lot.quantity_on_hand}{" "}
                      <span className="text-xs text-gray-400">
                        {mat?.uom_symbol ?? ""}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-right font-mono text-gray-600">
                      {lot.quantity_reserved}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusBadgeClass(lot.status)}`}
                      >
                        {lot.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-600">
                      {formatDate(lot.received_date)}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-600">
                      {formatDate(lot.expiry_date)}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-600">
                      {lot.supplier ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setEditing(lot)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                          title="Edit"
                        >
                          <PencilSquareIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {lots.length === 0 && (
                <tr>
                  <td
                    colSpan={9}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No material lots found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editing) && (
        <MaterialLotFormDialog
          lot={editing}
          defaultMaterialId={materialFilter || undefined}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
