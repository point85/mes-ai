/**
 * Work Center List Page — shows work centers for a given line with drill-down to Equipment.
 */

import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  PlusIcon,
  PencilSquareIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";
import { useLine, useArea, useSite, useWorkCenters } from "../../hooks/usePhysicalModel";
import { Breadcrumb } from "../../components/layout";
import type { WorkCenter } from "../../types";
import WorkCenterFormDialog from "./WorkCenterFormDialog";

const TYPE_BADGE: Record<string, string> = {
  manual: "bg-blue-50 text-blue-700",
  automated: "bg-green-50 text-green-700",
  hybrid: "bg-purple-50 text-purple-700",
};

export default function WorkCenterListPage() {
  const { lineId } = useParams<{ lineId: string }>();
  const navigate = useNavigate();

  const [editingWC, setEditingWC] = useState<WorkCenter | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");

  const { data: line } = useLine(lineId!);
  const { data: area } = useArea(line?.area_id ?? "");
  const { data: site } = useSite(area?.site_id ?? "");
  const { data, isLoading, error } = useWorkCenters(lineId!);

  const workCenters: WorkCenter[] = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!search) return workCenters;
    const q = search.toLowerCase();
    return workCenters.filter(
      (wc) => wc.name.toLowerCase().includes(q) || wc.code.toLowerCase().includes(q),
    );
  }, [workCenters, search]);

  return (
    <div className="space-y-6">
      <Breadcrumb
        crumbs={[
          { label: "Sites", to: "/sites" },
          { label: site?.name ?? "…", to: site ? `/sites/${site.id}/areas` : undefined },
          { label: area?.name ?? "…", to: area ? `/areas/${area.id}/lines` : undefined },
          { label: line?.name ?? "…" },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Work Centers</h1>
          <p className="text-sm text-gray-500 mt-1">
            Work centers on line <span className="font-medium">{line?.name ?? "…"}</span>.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Work Center
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
          {filtered.length} work center{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="text-sm text-gray-500">Loading work centers…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load work centers.
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Code</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Type</th>
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
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_BADGE[wc.wc_type] ?? "bg-gray-100 text-gray-700"}`}>
                      {wc.wc_type}
                    </span>
                  </td>
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
                        onClick={() => navigate(`/work-centers/${wc.id}/equipment`)}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                        title="View Equipment"
                      >
                        <ChevronRightIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditingWC(wc)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
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
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                    No work centers found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editingWC) && (
        <WorkCenterFormDialog
          workCenter={editingWC}
          lineId={lineId!}
          onClose={() => {
            setShowCreate(false);
            setEditingWC(null);
          }}
        />
      )}
    </div>
  );
}
