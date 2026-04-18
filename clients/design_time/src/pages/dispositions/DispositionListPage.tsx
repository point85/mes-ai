/**
 * Disposition List Page — flat table CRUD for dispositions.
 *
 * Each disposition has a code, name, description, and category
 * (route / hold / scrap). Route steps reference a disposition by FK.
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  useDispositions,
  useDeleteDisposition,
} from "../../hooks/useProductDef";
import type { Disposition } from "../../types";
import DispositionFormDialog from "./DispositionFormDialog";

/* ── category colour badges ───────────────────────────────────────── */
const CATEGORY_COLORS: Record<string, string> = {
  route: "bg-green-100 text-green-700",
  hold: "bg-amber-100 text-amber-700",
  scrap: "bg-red-100 text-red-700",
};

export default function DispositionListPage() {
  const { data: listResp, isLoading } = useDispositions();
  const deleteMut = useDeleteDisposition();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Disposition | null>(null);

  const dispositions = useMemo(
    () => (listResp?.data ?? []).slice().sort((a, b) => a.code.localeCompare(b.code)),
    [listResp],
  );

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (d: Disposition) => {
    setEditing(d);
    setDialogOpen(true);
  };

  const handleDelete = async (d: Disposition) => {
    if (!window.confirm(`Delete disposition ${d.code} — ${d.name}?`)) return;
    await deleteMut.mutateAsync(d.id);
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dispositions</h1>
          <p className="mt-1 text-sm text-gray-500">
            Disposition codes that route, hold, or scrap WIP at each process step.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-1 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
        >
          <PlusIcon className="h-4 w-4" /> New Disposition
        </button>
      </div>

      {isLoading ? (
        <p className="mt-8 text-sm text-gray-400">Loading…</p>
      ) : dispositions.length === 0 ? (
        <p className="mt-8 text-sm text-gray-400">No dispositions defined yet.</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-left">
            <thead className="bg-gray-50">
              <tr>
                <th className="py-2 pl-4 pr-2 text-xs font-medium uppercase text-gray-500">
                  Code
                </th>
                <th className="py-2 px-2 text-xs font-medium uppercase text-gray-500">
                  Name
                </th>
                <th className="py-2 px-2 text-xs font-medium uppercase text-gray-500">
                  Description
                </th>
                <th className="py-2 px-2 text-xs font-medium uppercase text-gray-500">
                  Category
                </th>
                <th className="py-2 px-2 text-right text-xs font-medium uppercase text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {dispositions.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap py-2 pl-4 pr-2 text-sm font-mono">
                    {d.code}
                  </td>
                  <td className="py-2 px-2 text-sm text-gray-900">{d.name}</td>
                  <td className="py-2 px-2 text-sm text-gray-500">
                    {d.description ?? "—"}
                  </td>
                  <td className="py-2 px-2">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${CATEGORY_COLORS[d.category] ?? ""}`}
                    >
                      {d.category}
                    </span>
                  </td>
                  <td className="whitespace-nowrap py-2 px-2 text-right text-sm">
                    <button
                      title="Edit"
                      onClick={() => openEdit(d)}
                      className="mr-1 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-indigo-600"
                    >
                      <PencilSquareIcon className="h-4 w-4" />
                    </button>
                    <button
                      title="Delete"
                      onClick={() => handleDelete(d)}
                      className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-600"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialogOpen && (
        <DispositionFormDialog
          disposition={editing}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </div>
  );
}
