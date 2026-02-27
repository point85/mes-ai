/**
 * Production Line List Page — shows lines for a given area with drill-down to Work Cells.
 */

import { useState, useMemo } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  PlusIcon,
  PencilSquareIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";
import { useArea, useSite, useLines } from "../../hooks/usePhysicalModel";
import { Breadcrumb } from "../../components/layout";
import type { ProductionLine } from "../../types";
import LineFormDialog from "./LineFormDialog";

interface LocationState {
  siteName?: string;
  siteId?: string;
  areaName?: string;
}

export default function LineListPage() {
  const { areaId } = useParams<{ areaId: string }>();
  const navigate = useNavigate();
  const { state } = useLocation();
  const locState = (state ?? {}) as LocationState;

  const [editingLine, setEditingLine] = useState<ProductionLine | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState("");

  const { data: area } = useArea(areaId!);
  const { data: site } = useSite(area?.site_id ?? locState.siteId ?? "");
  const { data, isLoading, error } = useLines(areaId!);

  const siteName = site?.name ?? locState.siteName ?? "…";
  const siteId = site?.id ?? area?.site_id ?? locState.siteId ?? "";
  const areaName = area?.name ?? locState.areaName ?? "…";
  const lines: ProductionLine[] = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!search) return lines;
    const q = search.toLowerCase();
    return lines.filter(
      (l) => l.name.toLowerCase().includes(q) || l.code.toLowerCase().includes(q),
    );
  }, [lines, search]);

  return (
    <div className="space-y-6">
      <Breadcrumb
        crumbs={[
          { label: "Sites", to: "/sites" },
          { label: siteName, to: siteId ? `/sites/${siteId}/areas` : undefined },
          { label: areaName },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production Lines</h1>
          <p className="text-sm text-gray-500 mt-1">
            Lines within area <span className="font-medium">{areaName}</span>.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          New Line
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
          {filtered.length} line{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="text-sm text-gray-500">Loading lines…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load production lines.
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
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Description</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">Active</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((line) => (
                <tr key={line.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">{line.code}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-700">{line.name}</td>
                  <td className="px-4 py-2.5 text-sm text-gray-500 max-w-xs truncate">{line.description ?? "—"}</td>
                  <td className="px-4 py-2.5 text-center">
                    {line.is_active ? (
                      <span className="text-xs text-green-600 font-medium">✓</span>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => navigate(`/lines/${line.id}/work-cells`, { state: { siteName, siteId, areaName, areaId, lineName: line.name } })}
                        className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                        title="View Work Cells"
                      >
                        <ChevronRightIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setEditingLine(line)}
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
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                    No production lines found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editingLine) && (
        <LineFormDialog
          line={editingLine}
          areaId={areaId!}
          onClose={() => {
            setShowCreate(false);
            setEditingLine(null);
          }}
        />
      )}
    </div>
  );
}
