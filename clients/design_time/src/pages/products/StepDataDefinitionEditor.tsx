/**
 * Step Data Definition sub-editor — binds DataDefinition catalog entries
 * to a ProcessSegment.
 *
 * DataDefinitions are a flat catalog (created on /data-definitions) whose
 * `step_id` FK points at a ProcessSegment. This editor shows the defs
 * attached to the given step and lets the user attach an existing
 * catalog entry (either currently unassigned or already bound to another
 * step) or detach one.
 */

import { useState } from "react";
import { TrashIcon, PlusIcon, LinkIcon } from "@heroicons/react/24/outline";
import {
  useDataDefinitionsForStep,
  useUnassignedDataDefinitions,
  useUpdateDataDefinition,
} from "../../hooks/useDataCollection";
import type { DataDefinition } from "../../types";

interface Props {
  stepId: string;
}

export default function StepDataDefinitionEditor({ stepId }: Props) {
  const { data: attachedResp, isLoading } = useDataDefinitionsForStep(stepId);
  const attached: DataDefinition[] = (attachedResp?.data ?? [])
    .slice()
    .sort((a, b) => a.code.localeCompare(b.code));

  const { data: unassignedResp } = useUnassignedDataDefinitions();
  const unassigned: DataDefinition[] = (unassignedResp?.data ?? [])
    .slice()
    .sort((a, b) => a.code.localeCompare(b.code));

  const updateMut = useUpdateDataDefinition();

  const [pickerId, setPickerId] = useState<string>("");
  const [formError, setFormError] = useState<string | null>(null);

  const handleAttach = async () => {
    setFormError(null);
    if (!pickerId) {
      setFormError("Select a data definition first.");
      return;
    }
    try {
      await updateMut.mutateAsync({ id: pickerId, step_id: stepId });
      setPickerId("");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setFormError(detail ?? "Failed to attach data definition.");
    }
  };

  const handleDetach = async (d: DataDefinition) => {
    if (!confirm(`Detach "${d.code}" from this step?`)) return;
    try {
      await updateMut.mutateAsync({ id: d.id, step_id: null });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      alert(detail ?? "Failed to detach data definition.");
    }
  };

  const dataTypeBadge = (dt: string) => {
    const styles: Record<string, string> = {
      numeric: "bg-blue-100 text-blue-800",
      string: "bg-gray-100 text-gray-700",
      boolean: "bg-green-100 text-green-800",
      enum: "bg-purple-100 text-purple-800",
    };
    return (
      <span
        className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
          styles[dt] ?? "bg-gray-100 text-gray-700"
        }`}
      >
        {dt}
      </span>
    );
  };

  const sourceBadge = (src: string) => {
    const styles: Record<string, string> = {
      manual: "bg-amber-100 text-amber-800",
      equipment: "bg-indigo-100 text-indigo-800",
      sensor: "bg-teal-100 text-teal-800",
    };
    return (
      <span
        className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
          styles[src] ?? "bg-gray-100 text-gray-700"
        }`}
      >
        {src}
      </span>
    );
  };

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-gray-800">
            Data Definitions
          </h4>
          <p className="text-xs text-gray-500">
            Catalog entries collected at this step (numeric readings, strings,
            booleans, enums — manual, equipment, or sensor).
          </p>
        </div>
        <a
          href="/data-definitions"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-500"
          title="Open data definition catalog in a new tab"
        >
          <LinkIcon className="h-3.5 w-3.5" />
          Catalog
        </a>
      </div>

      {isLoading ? (
        <p className="text-xs text-gray-500">Loading…</p>
      ) : attached.length === 0 ? (
        <p className="rounded border border-dashed border-gray-300 bg-white px-3 py-2 text-xs text-gray-500">
          No data definitions attached. Pick one from the catalog below or
          create a new one on the data-definition catalog page.
        </p>
      ) : (
        <ul className="space-y-1">
          {attached.map((d) => (
            <li
              key={d.id}
              className="flex items-center gap-2 rounded border border-gray-200 bg-white px-2 py-1.5 text-xs"
            >
              <span className="flex-1 truncate">
                <span className="font-mono font-medium text-gray-900">
                  {d.code}
                </span>
                <span className="ml-2 text-gray-600">{d.name}</span>
                {d.uom && (
                  <span className="ml-1.5 text-gray-400">[{d.uom}]</span>
                )}
              </span>
              {dataTypeBadge(d.data_type)}
              {sourceBadge(d.source)}
              {d.is_required && (
                <span className="inline-block rounded bg-red-50 px-1.5 py-0.5 text-xs font-medium text-red-700">
                  required
                </span>
              )}
              <button
                type="button"
                onClick={() => handleDetach(d)}
                className="rounded p-1 text-gray-400 hover:text-red-600"
                aria-label="Detach data definition"
                disabled={updateMut.isPending}
              >
                <TrashIcon className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Attach existing */}
      <div className="mt-3 rounded border border-gray-200 bg-white p-2">
        <div className="mb-1 text-xs font-semibold text-gray-700">
          Attach existing catalog entry
        </div>
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <select
            value={pickerId}
            onChange={(e) => setPickerId(e.target.value)}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-xs"
          >
            <option value="">
              — Select an unassigned data definition —
            </option>
            {unassigned.map((d) => (
              <option key={d.id} value={d.id}>
                {d.code} — {d.name} ({d.data_type})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleAttach}
            disabled={updateMut.isPending || !pickerId}
            className="inline-flex items-center gap-1 rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            <PlusIcon className="h-3.5 w-3.5" />
            Attach
          </button>
        </div>
        {unassigned.length === 0 && (
          <p className="mt-1 text-xs text-gray-400">
            All catalog entries are already bound to a step. Create a new one
            on the{" "}
            <a
              href="/data-definitions"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 hover:text-indigo-500"
            >
              data-definition catalog
            </a>
            .
          </p>
        )}
        {formError && <p className="mt-1 text-xs text-red-600">{formError}</p>}
      </div>
    </div>
  );
}
