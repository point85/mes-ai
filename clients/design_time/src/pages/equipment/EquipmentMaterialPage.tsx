/**
 * Equipment Material Setups Page — shows production material setups
 * for a specific piece of equipment (design speed, reject UoM, target OEE).
 */

import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { PlusIcon, PencilSquareIcon, TrashIcon, ArrowLeftIcon } from "@heroicons/react/24/outline";
import {
  useEquipmentMaterials,
  useDeleteEquipmentMaterial,
} from "../../hooks/usePhysicalModel";
import { useMaterials } from "../../hooks/useMaterial";
import type { EquipmentMaterial } from "../../types";
import EquipmentMaterialFormDialog from "./EquipmentMaterialFormDialog";

export default function EquipmentMaterialPage() {
  const { equipId } = useParams<{ equipId: string }>();
  const navigate = useNavigate();

  const [editing, setEditing] = useState<EquipmentMaterial | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading, error } = useEquipmentMaterials(equipId!);
  const { data: matData } = useMaterials();
  const deleteMut = useDeleteEquipmentMaterial();

  const materials: EquipmentMaterial[] = data?.data ?? [];
  const matMap = useMemo(() => {
    const map = new Map<string, { name: string; code: string }>();
    for (const m of matData?.data ?? []) {
      map.set(m.id, { name: m.name, code: m.code });
    }
    return map;
  }, [matData]);

  const filtered = useMemo(() => {
    if (!search) return materials;
    const q = search.toLowerCase();
    return materials.filter((em) => {
      const mat = matMap.get(em.material_id);
      return (
        mat?.name.toLowerCase().includes(q) ||
        mat?.code.toLowerCase().includes(q) ||
        em.design_speed_uom.toLowerCase().includes(q)
      );
    });
  }, [materials, search, matMap]);

  return (
    <div className="space-y-6">
      {/* Back link */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Back to Equipment
      </button>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Material Setups</h1>
          <p className="text-sm text-gray-500 mt-1">
            Define design speed, reject UoM, and target OEE for each material
            this equipment can produce.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          Add Material Setup
        </button>
      </div>

      {/* Search */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search by material name, code, or UoM…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-72"
        />
        <span className="text-xs text-gray-400">
          {filtered.length} setup{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && (
        <p className="text-sm text-gray-500">Loading material setups…</p>
      )}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load material setups.
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Material
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Code
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Design Speed
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Speed UoM
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Reject UoM
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Target OEE
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((em) => {
                const mat = matMap.get(em.material_id);
                return (
                  <tr
                    key={em.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-2.5 text-sm text-gray-700">
                      {mat?.name ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-900">
                      {mat?.code ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700 text-right tabular-nums">
                      {em.design_speed}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-500">
                      {em.design_speed_uom}
                    </td>
                    <td className="px-4 py-2.5 text-sm font-mono text-gray-500">
                      {em.reject_uom}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700 text-right tabular-nums">
                      {em.target_oee}%
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setEditing(em)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                          title="Edit"
                        >
                          <PencilSquareIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm("Delete this material setup?")) {
                              deleteMut.mutate(em.id);
                            }
                          }}
                          className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                          title="Delete"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center text-sm text-gray-400"
                  >
                    No material setups found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editing) && (
        <EquipmentMaterialFormDialog
          setup={editing}
          equipId={equipId!}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}
