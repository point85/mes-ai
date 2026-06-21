/**
 * Area List Page — shows areas for a given site with drill-down to Lines.
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
import { useSite, useAreas, useDeleteArea, useCreateArea } from "../../hooks/usePhysicalModel";
import { Breadcrumb } from "../../components/layout";
import type { Area } from "../../types";
import AreaFormDialog from "./AreaFormDialog";
import CloneDialog from "../../components/CloneDialog";

interface LocationState {
  siteName?: string;
}

export default function AreaListPage() {
  const { siteId } = useParams<{ siteId: string }>();
  const navigate = useNavigate();
  const { state } = useLocation();
  const locState = (state ?? {}) as LocationState;

  const [editingArea, setEditingArea] = useState<Area | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [cloneTarget, setCloneTarget] = useState<Area | null>(null);
  const [search, setSearch] = useState("");

  const { data: site } = useSite(siteId!);
  const { data, isLoading, error } = useAreas(siteId!);
  const deleteMut = useDeleteArea();
  const createMut = useCreateArea();

  const siteName = site?.name ?? locState.siteName ?? "…";
  const areas: Area[] = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!search) return areas;
    const q = search.toLowerCase();
    return areas.filter(
      (a) => a.name.toLowerCase().includes(q) || a.code.toLowerCase().includes(q),
    );
  }, [areas, search]);

  const handleDelete = (area: Area) => {
    if (!confirm(`Delete area "${area.name}"?`)) return;
    deleteMut.mutate(area.id);
  };

  const handleClone = async (newCode: string) => {
    const a = cloneTarget!;
    await createMut.mutateAsync({
      siteId: siteId!,
      name: a.name,
      code: newCode,
      description: a.description,
      work_schedule_id: a.work_schedule_id,
    });
    setCloneTarget(null);
  };

  return (
    <div className="space-y-6">
      <Breadcrumb
        crumbs={[
          { label: "Sites", to: "/sites" },
          { label: siteName },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Areas</h1>
          <p className="text-sm text-gray-500 mt-1">
            Areas within <span className="font-medium">{siteName}</span>.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Area
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
          {filtered.length} area{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="text-sm text-gray-500">Loading areas…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load areas.
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
              {filtered.map((area) => (
                <tr key={area.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">{area.code}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">{area.name}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-500 max-w-xs truncate">{area.description ?? "—"}</td>
                  <td className="px-4 py-2.5 text-center">
                    {area.is_active ? (
                      <span className="text-xs text-green-600 font-medium">✓</span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => navigate(`/areas/${area.id}/lines`, { state: { siteName, siteId, areaName: area.name } })}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                        title="View Lines"
                      >
                        <ChevronRightIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setCloneTarget(area)}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                        title="Clone"
                      >
                        <DocumentDuplicateIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditingArea(area)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(area)}
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
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                    No areas found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editingArea) && (
        <AreaFormDialog
          area={editingArea}
          siteId={siteId!}
          onClose={() => {
            setShowCreate(false);
            setEditingArea(null);
          }}
        />
      )}

      {/* Clone dialog */}
      {cloneTarget && (
        <CloneDialog
          title={`Clone Area — ${cloneTarget.code}`}
          label="New Code"
          initialValue={cloneTarget.code}
          onClose={() => setCloneTarget(null)}
          onConfirm={handleClone}
        />
      )}
    </div>
  );
}
