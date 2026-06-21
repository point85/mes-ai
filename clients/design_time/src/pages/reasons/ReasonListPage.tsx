/**
 * Reason List Page — hierarchical tree view for OEE reason-codes.
 *
 * Displays reasons as an indented tree and lets users create, edit, or
 * soft-delete individual nodes.  Accessible from the Dashboard link.
 */

import { useState, useMemo } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  DocumentDuplicateIcon,
} from "@heroicons/react/24/outline";
import {
  useReasons,
  useDeleteReason,
  useCreateReason,
} from "../../hooks/usePerformance";
import type { Reason } from "../../types";
import ReasonFormDialog from "./ReasonFormDialog";
import CloneDialog from "../../components/CloneDialog";

/* ── bucket colour badges ─────────────────────────────────────────── */
const BUCKET_COLORS: Record<string, string> = {
  downtime_unplanned: "bg-red-100 text-red-800",
  downtime_planned: "bg-amber-100 text-amber-800",
  uptime_non_value: "bg-yellow-100 text-yellow-800",
  uptime_value_add: "bg-green-100 text-green-800",
  excluded: "bg-gray-100 text-gray-600",
};

const BUCKET_LABELS: Record<string, string> = {
  downtime_unplanned: "Unplanned DT",
  downtime_planned: "Planned DT",
  uptime_non_value: "Non-Value",
  uptime_value_add: "Value-Add",
  excluded: "Excluded",
};

/* ── tree helper ──────────────────────────────────────────────────── */
interface TreeNode extends Reason {
  children: TreeNode[];
}

function buildTree(reasons: Reason[]): TreeNode[] {
  const map = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];

  for (const r of reasons) {
    map.set(r.id, { ...r, children: [] });
  }
  for (const node of map.values()) {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

/* ── tree row ─────────────────────────────────────────────────────── */
interface RowProps {
  node: TreeNode;
  depth: number;
  onEdit: (r: Reason) => void;
  onDelete: (r: Reason) => void;
  onAddChild: (parentId: string) => void;
  onClone: (r: Reason) => void;
}

function TreeRow({ node, depth, onEdit, onDelete, onAddChild, onClone }: RowProps) {
  return (
    <>
      <tr className="hover:bg-gray-50">
        <td
          className="whitespace-nowrap py-2 pl-4 pr-2 text-sm font-mono"
          style={{ paddingLeft: `${depth * 1.5 + 1}rem` }}
        >
          {node.code}
        </td>
        <td className="py-2 px-2 text-sm text-gray-900">{node.name}</td>
        <td className="py-2 px-2 text-sm text-gray-500">
          {node.description ?? "—"}
        </td>
        <td className="py-2 px-2">
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${BUCKET_COLORS[node.oee_bucket] ?? ""}`}
          >
            {BUCKET_LABELS[node.oee_bucket] ?? node.oee_bucket}
          </span>
        </td>
        <td className="whitespace-nowrap py-2 px-2 text-right text-sm">
          <button
            title="Add child reason"
            onClick={() => onAddChild(node.id)}
            className="mr-1 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-indigo-600"
          >
            <PlusIcon className="h-4 w-4" />
          </button>
          <button
            title="Clone"
            onClick={() => onClone(node)}
            className="mr-1 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-indigo-600"
          >
            <DocumentDuplicateIcon className="h-4 w-4" />
          </button>
          <button
            title="Edit"
            onClick={() => onEdit(node)}
            className="mr-1 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-indigo-600"
          >
            <PencilSquareIcon className="h-4 w-4" />
          </button>
          <button
            title="Delete"
            onClick={() => onDelete(node)}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-600"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </td>
      </tr>
      {node.children.map((child) => (
        <TreeRow
          key={child.id}
          node={child}
          depth={depth + 1}
          onEdit={onEdit}
          onDelete={onDelete}
          onAddChild={onAddChild}
          onClone={onClone}
        />
      ))}
    </>
  );
}

/* ── page component ───────────────────────────────────────────────── */
export default function ReasonListPage() {
  const { data: reasons, isLoading } = useReasons();
  const deleteMut = useDeleteReason();
  const createMut = useCreateReason();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Reason | null>(null);
  const [addChildParentId, setAddChildParentId] = useState<string | null>(null);
  const [cloneTarget, setCloneTarget] = useState<Reason | null>(null);

  const tree = useMemo(() => buildTree(reasons ?? []), [reasons]);

  const openCreate = () => {
    setEditing(null);
    setAddChildParentId(null);
    setDialogOpen(true);
  };

  const openEdit = (r: Reason) => {
    setEditing(r);
    setAddChildParentId(null);
    setDialogOpen(true);
  };

  const openAddChild = (parentId: string) => {
    setEditing(null);
    setAddChildParentId(parentId);
    setDialogOpen(true);
  };

  const handleDelete = async (r: Reason) => {
    if (!window.confirm(`Delete reason ${r.code} — ${r.name}?`)) return;
    await deleteMut.mutateAsync(r.id);
  };

  const handleClone = async (newCode: string) => {
    const r = cloneTarget!;
    await createMut.mutateAsync({
      code: newCode,
      name: r.name,
      description: r.description,
      oee_bucket: r.oee_bucket,
      parent_id: r.parent_id,
    });
    setCloneTarget(null);
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reason Codes</h1>
          <p className="mt-1 text-sm text-gray-500">
            Hierarchical loss and downtime reason codes for OEE availability tracking.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-1 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
        >
          <PlusIcon className="h-4 w-4" /> New Reason
        </button>
      </div>

      {isLoading ? (
        <p className="mt-8 text-sm text-gray-400">Loading…</p>
      ) : tree.length === 0 ? (
        <p className="mt-8 text-sm text-gray-400">No reason codes defined yet.</p>
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
                  OEE Bucket
                </th>
                <th className="py-2 px-2 text-right text-xs font-medium uppercase text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tree.map((root) => (
                <TreeRow
                  key={root.id}
                  node={root}
                  depth={0}
                  onEdit={openEdit}
                  onDelete={handleDelete}
                  onAddChild={openAddChild}
                  onClone={setCloneTarget}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialogOpen && (
        <ReasonFormDialog
          reason={editing}
          parentId={addChildParentId}
          onClose={() => setDialogOpen(false)}
        />
      )}

      {/* Clone dialog */}
      {cloneTarget && (
        <CloneDialog
          title={`Clone Reason — ${cloneTarget.code}`}
          label="New Code"
          initialValue={cloneTarget.code}
          onClose={() => setCloneTarget(null)}
          onConfirm={handleClone}
        />
      )}
    </div>
  );
}
