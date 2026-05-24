/**
 * Equipment List Page — leaf level of the ISA-95 hierarchy.
 * Shows equipment for a given work cell with status badges.
 */

import { useState, useMemo } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { PlusIcon, PencilSquareIcon, TrashIcon, Cog6ToothIcon, BoltIcon } from "@heroicons/react/24/outline";
import {
  useWorkCell,
  useLine,
  useArea,
  useSite,
  useEquipment,
  useEquipmentClasses,
  useDeleteEquipment,
} from "../../hooks/usePhysicalModel";
import { Breadcrumb } from "../../components/layout";
import type { Equipment } from "../../types";
import EquipmentFormDialog from "./EquipmentFormDialog";

interface LocationState {
  siteName?: string;
  siteId?: string;
  areaName?: string;
  areaId?: string;
  lineName?: string;
  lineId?: string;
  wcName?: string;
}

export default function EquipmentListPage() {
  const { wcId } = useParams<{ wcId: string }>();
  const { state } = useLocation();
  const navigate = useNavigate();
  const locState = (state ?? {}) as LocationState;

  const [editingEquip, setEditingEquip] = useState<Equipment | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");

  const { data: wc } = useWorkCell(wcId!);
  const { data: line } = useLine(wc?.line_id ?? locState.lineId ?? "");
  const { data: area } = useArea(line?.area_id ?? locState.areaId ?? "");
  const { data: site } = useSite(area?.site_id ?? locState.siteId ?? "");
  const { data, isLoading, error } = useEquipment(wcId!);
  const { data: classesResp } = useEquipmentClasses();
  const deleteMut = useDeleteEquipment();

  const classMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of classesResp?.data ?? []) {
      map.set(c.id, `${c.name} (${c.code})`);
    }
    return map;
  }, [classesResp]);

  const siteName = site?.name ?? locState.siteName ?? "…";
  const siteId = site?.id ?? area?.site_id ?? locState.siteId ?? "";
  const areaName = area?.name ?? locState.areaName ?? "…";
  const areaId = area?.id ?? line?.area_id ?? locState.areaId ?? "";
  const lineName = line?.name ?? locState.lineName ?? "…";
  const lineId = line?.id ?? wc?.line_id ?? locState.lineId ?? "";
  const wcName = wc?.name ?? locState.wcName ?? "…";
  const equipmentList: Equipment[] = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!search) return equipmentList;
    const q = search.toLowerCase();
    return equipmentList.filter(
      (e) => e.name.toLowerCase().includes(q) || e.code.toLowerCase().includes(q),
    );
  }, [equipmentList, search]);

  const handleDelete = (eq: Equipment) => {
    if (!confirm(`Delete equipment "${eq.name}"?`)) return;
    deleteMut.mutate(eq.id);
  };

  return (
    <div className="space-y-6">
      <Breadcrumb
        crumbs={[
          { label: "Sites", to: "/sites" },
          { label: siteName, to: siteId ? `/sites/${siteId}/areas` : undefined },
          { label: areaName, to: areaId ? `/areas/${areaId}/lines` : undefined },
          { label: lineName, to: lineId ? `/lines/${lineId}/work-cells` : undefined },
          { label: wcName },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Equipment</h1>
          <p className="text-sm text-gray-500 mt-1">
            Equipment in work cell{" "}
            <span className="font-medium">{wcName}</span>.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Equipment
        </button>
      </div>

      {/* Search */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search by name or code…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-64"
        />
        <span className="text-xs text-gray-400">
          {filtered.length} item{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="text-sm text-gray-500">Loading equipment…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load equipment.
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Code</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Class</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">State Model</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">Active</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((eq) => (
                <tr key={eq.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">{eq.code}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">{eq.name}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {eq.equipment_class_id ? classMap.get(eq.equipment_class_id) ?? "—" : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {eq.state_model_id ?? <span className="text-gray-400 italic">none</span>}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {eq.is_active ? (
                      <span className="text-xs text-green-600 font-medium">✓</span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => navigate(`/equipment/${eq.id}/capabilities`)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Capabilities"
                      >
                        <BoltIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => navigate(`/equipment/${eq.id}/materials`)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Material Setups"
                      >
                        <Cog6ToothIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditingEquip(eq)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(eq)}
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
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                    No equipment found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editingEquip) && (
        <EquipmentFormDialog
          equipment={editingEquip}
          wcId={wcId!}
          onClose={() => {
            setShowCreate(false);
            setEditingEquip(null);
          }}
        />
      )}
    </div>
  );
}
