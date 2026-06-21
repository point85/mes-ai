/**
 * Work Cell List Page — shows work cells for a given line with drill-down to Equipment.
 */

import { useState, useMemo } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  ChevronRightIcon,
  DocumentDuplicateIcon,
} from "@heroicons/react/24/outline";
import { useLine, useArea, useSite, useWorkCells, useDeleteWorkCell, useCreateWorkCell } from "../../hooks/usePhysicalModel";
import { Breadcrumb } from "../../components/layout";
import type { WorkCell } from "../../types";
import WorkCellFormDialog from "./WorkCellFormDialog";
import CloneDialog from "../../components/CloneDialog";

interface LocationState {
  siteName?: string;
  siteId?: string;
  areaName?: string;
  areaId?: string;
  lineName?: string;
}

export default function WorkCellListPage() {
  const { lineId } = useParams<{ lineId: string }>();
  const navigate = useNavigate();
  const { state } = useLocation();
  const locState = (state ?? {}) as LocationState;

  const [editingWC, setEditingWC] = useState<WorkCell | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [cloneTarget, setCloneTarget] = useState<WorkCell | null>(null);
  const [search, setSearch] = useState("");

  const { data: line } = useLine(lineId!);
  const { data: area } = useArea(line?.area_id ?? locState.areaId ?? "");
  const { data: site } = useSite(area?.site_id ?? locState.siteId ?? "");
  const { data, isLoading, error } = useWorkCells(lineId!);
  const deleteMut = useDeleteWorkCell();
  const createMut = useCreateWorkCell();

  const siteName = site?.name ?? locState.siteName ?? "…";
  const siteId = site?.id ?? area?.site_id ?? locState.siteId ?? "";
  const areaName = area?.name ?? locState.areaName ?? "…";
  const areaId = area?.id ?? line?.area_id ?? locState.areaId ?? "";
  const lineName = line?.name ?? locState.lineName ?? "…";
  const workCells: WorkCell[] = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!search) return workCells;
    const q = search.toLowerCase();
    return workCells.filter(
      (wc) => wc.name.toLowerCase().includes(q) || wc.code.toLowerCase().includes(q),
    );
  }, [workCells, search]);

  const handleDelete = (wc: WorkCell) => {
    if (!confirm(`Delete work cell "${wc.name}"?`)) return;
    deleteMut.mutate(wc.id);
  };

  const handleClone = async (newCode: string) => {
    const wc = cloneTarget!;
    await createMut.mutateAsync({
      lineId: lineId!,
      name: wc.name,
      code: newCode,
      description: wc.description,
      work_schedule_id: wc.work_schedule_id,
      default_dispatch_strategy: wc.default_dispatch_strategy,
      custom_strategy_prompt: wc.custom_strategy_prompt,
    });
    setCloneTarget(null);
  };

  return (
    <div className="space-y-6">
      <Breadcrumb
        crumbs={[
          { label: "Sites", to: "/sites" },
          { label: siteName, to: siteId ? `/sites/${siteId}/areas` : undefined },
          { label: areaName, to: areaId ? `/areas/${areaId}/lines` : undefined },
          { label: lineName },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Work Cells</h1>
          <p className="text-sm text-gray-500 mt-1">
            Work cells on line <span className="font-medium">{lineName}</span>.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Work Cell
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
          {filtered.length} work cell{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="text-sm text-gray-500">Loading work cells…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load work cells.
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
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Description</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">Active</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((wc) => (
                <tr key={wc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">{wc.code}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">{wc.name}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-500 max-w-xs truncate">{wc.description ?? "—"}</td>
                  <td className="px-4 py-2.5 text-center">
                    {wc.is_active ? (
                      <span className="text-xs text-green-600 font-medium">✓</span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => navigate(`/work-cells/${wc.id}/equipment`, { state: { siteName, siteId, areaName, areaId, lineName, lineId, wcName: wc.name } })}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                        title="View Equipment"
                      >
                        <ChevronRightIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setCloneTarget(wc)}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                        title="Clone"
                      >
                        <DocumentDuplicateIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditingWC(wc)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(wc)}
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
                    No work cells found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editingWC) && (
        <WorkCellFormDialog
          workCell={editingWC}
          lineId={lineId!}
          onClose={() => {
            setShowCreate(false);
            setEditingWC(null);
          }}
        />
      )}

      {/* Clone dialog */}
      {cloneTarget && (
        <CloneDialog
          title={`Clone Work Cell — ${cloneTarget.code}`}
          label="New Code"
          initialValue={cloneTarget.code}
          onClose={() => setCloneTarget(null)}
          onConfirm={handleClone}
        />
      )}
    </div>
  );
}
