/**
 * Equipment Requirements sub-editor — manages the many-side of a
 * ProcessSegment's EquipmentSegmentSpecification (ISA-95 Part 2).
 *
 * Each requirement targets EITHER an EquipmentClass OR a specific
 * Equipment (enforced server-side by CHECK ck_segment_equip_req_one_target).
 */

import { useState } from "react";
import { TrashIcon, PlusIcon } from "@heroicons/react/24/outline";
import {
  useStepEquipmentRequirements,
  useCreateStepEquipmentRequirement,
  useUpdateStepEquipmentRequirement,
  useDeleteStepEquipmentRequirement,
  useUpdateRouteStep,
} from "../../hooks/useProductDef";
import { useEquipmentClasses, useAllEquipment } from "../../hooks/usePhysicalModel";
import type { EquipmentRequirementUseType } from "../../types";

interface Props {
  stepId: string;
  primaryEquipmentClassId?: string | null;
}

type TargetMode = "class" | "equipment";

export default function EquipmentRequirementsEditor({
  stepId,
  primaryEquipmentClassId = null,
}: Props) {
  const { data: reqsResp, isLoading } = useStepEquipmentRequirements(stepId);
  const reqs = reqsResp?.data ?? [];
  const createMut = useCreateStepEquipmentRequirement(stepId);
  const updateMut = useUpdateStepEquipmentRequirement(stepId);
  const deleteMut = useDeleteStepEquipmentRequirement(stepId);
  const updateStepMut = useUpdateRouteStep();

  const { data: ecResp } = useEquipmentClasses();
  const equipmentClasses = (ecResp?.data ?? []).slice().sort((a, b) => a.code.localeCompare(b.code));
  const ecMap = new Map(equipmentClasses.map((ec) => [ec.id, ec]));
  const { data: eqResp } = useAllEquipment();
  const equipment = (eqResp?.data ?? []).slice().sort((a, b) => a.code.localeCompare(b.code));
  const eqMap = new Map(equipment.map((eq) => [eq.id, eq]));

  const [mode, setMode] = useState<TargetMode>("class");
  const [targetId, setTargetId] = useState<string>("");
  const [useType, setUseType] = useState<EquipmentRequirementUseType>("required");
  const [description, setDescription] = useState<string>("");
  const [formError, setFormError] = useState<string | null>(null);

  const handleAdd = async () => {
    setFormError(null);
    if (!targetId) {
      setFormError("Select a target first.");
      return;
    }
    try {
      await createMut.mutateAsync({
        equipment_class_id: mode === "class" ? targetId : null,
        equipment_id: mode === "equipment" ? targetId : null,
        use_type: useType,
        description: description.trim() || null,
      });
      setTargetId("");
      setDescription("");
      setUseType("required");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? "Failed to add requirement.");
    }
  };

  const targetLabel = (r: (typeof reqs)[number]): string => {
    if (r.equipment_class_id) {
      const ec = ecMap.get(r.equipment_class_id);
      return ec ? `Class: ${ec.code} — ${ec.name}` : "Class: (unknown)";
    }
    if (r.equipment_id) {
      const eq = eqMap.get(r.equipment_id);
      return eq ? `Equipment: ${eq.code} — ${eq.name}` : "Equipment: (unknown)";
    }
    return "(no target)";
  };

  const useTypeBadge = (u: EquipmentRequirementUseType) => {
    const styles: Record<EquipmentRequirementUseType, string> = {
      required: "bg-red-100 text-red-800",
      preferred: "bg-indigo-100 text-indigo-800",
      alternate: "bg-gray-100 text-gray-700",
    };
    return (
      <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${styles[u]}`}>
        {u}
      </span>
    );
  };

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-gray-800">Equipment Requirements</h4>
          <p className="text-xs text-gray-500">
            Set the primary equipment class for the step and add any extra class or specific-equipment constraints. Dispatch ANDs them all.
          </p>
        </div>
      </div>

      <div className="mb-3 rounded border border-gray-200 bg-white p-2">
        <label className="block text-xs font-medium text-gray-700">
          Primary Equipment Class <span className="text-gray-400">(ISA-95)</span>
        </label>
        <select
          value={primaryEquipmentClassId ?? ""}
          onChange={(e) =>
            updateStepMut.mutate({
              id: stepId,
              equipment_class_id: e.target.value || null,
            })
          }
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-2 py-1 text-xs"
        >
          <option value="">— None —</option>
          {equipmentClasses.map((ec) => (
            <option key={ec.id} value={ec.id}>
              {ec.code} — {ec.name}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-400">
          The step-level equipment class used by dispatch and shown in the route table.
        </p>
      </div>

      {isLoading ? (
        <p className="text-xs text-gray-500">Loading…</p>
      ) : reqs.length === 0 ? (
        <p className="rounded border border-dashed border-gray-300 bg-white px-3 py-2 text-xs text-gray-500">
          No additional requirements. The primary equipment class above is the only constraint.
        </p>
      ) : (
        <ul className="space-y-1">
          {reqs.map((r) => (
            <li
              key={r.id}
              className="flex items-center gap-2 rounded border border-gray-200 bg-white px-2 py-1.5 text-xs"
            >
              <span className="flex-1 truncate text-gray-800">{targetLabel(r)}</span>
              <select
                value={r.use_type}
                onChange={(e) =>
                  updateMut.mutate({
                    id: r.id,
                    use_type: e.target.value as EquipmentRequirementUseType,
                  })
                }
                className="rounded border border-gray-300 bg-white px-1.5 py-0.5 text-xs"
              >
                <option value="required">required</option>
                <option value="preferred">preferred</option>
                <option value="alternate">alternate</option>
              </select>
              {useTypeBadge(r.use_type)}
              <button
                type="button"
                onClick={() => deleteMut.mutate(r.id)}
                className="rounded p-1 text-gray-400 hover:text-red-600"
                aria-label="Remove requirement"
              >
                <TrashIcon className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 rounded border border-gray-200 bg-white p-2">
        <div className="mb-2 flex items-center gap-3 text-xs">
          <label className="inline-flex items-center gap-1">
            <input
              type="radio"
              name={`req-mode-${stepId}`}
              value="class"
              checked={mode === "class"}
              onChange={() => {
                setMode("class");
                setTargetId("");
              }}
            />
            Equipment Class
          </label>
          <label className="inline-flex items-center gap-1">
            <input
              type="radio"
              name={`req-mode-${stepId}`}
              value="equipment"
              checked={mode === "equipment"}
              onChange={() => {
                setMode("equipment");
                setTargetId("");
              }}
            />
            Specific Equipment
          </label>
        </div>
        <div className="grid grid-cols-[1fr_auto_auto] gap-2">
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-xs"
          >
            <option value="">— Select {mode === "class" ? "class" : "equipment"} —</option>
            {mode === "class"
              ? equipmentClasses.map((ec) => (
                  <option key={ec.id} value={ec.id}>
                    {ec.code} — {ec.name}
                  </option>
                ))
              : equipment.map((eq) => (
                  <option key={eq.id} value={eq.id}>
                    {eq.code} — {eq.name}
                  </option>
                ))}
          </select>
          <select
            value={useType}
            onChange={(e) => setUseType(e.target.value as EquipmentRequirementUseType)}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-xs"
          >
            <option value="required">required</option>
            <option value="preferred">preferred</option>
            <option value="alternate">alternate</option>
          </select>
          <button
            type="button"
            onClick={handleAdd}
            disabled={createMut.isPending || !targetId}
            className="inline-flex items-center gap-1 rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            <PlusIcon className="h-3.5 w-3.5" />
            Add
          </button>
        </div>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          className="mt-2 block w-full rounded border border-gray-300 px-2 py-1 text-xs"
        />
        {formError && <p className="mt-1 text-xs text-red-600">{formError}</p>}
      </div>
    </div>
  );
}
