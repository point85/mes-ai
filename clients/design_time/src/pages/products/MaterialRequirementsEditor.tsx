/**
 * Material Requirements sub-editor — manages a ProcessSegment's
 * SegmentMaterialRequirement rows (ISA-95 Part 4 step-level BOM).
 *
 * Each requirement references a Material with quantity, UoM,
 * material_use (consumed/produced) and an ordering position.
 * Unique on (step_id, material_id, material_use) server-side.
 */

import { useState } from "react";
import { TrashIcon, PlusIcon } from "@heroicons/react/24/outline";
import {
  useStepMaterialRequirements,
  useCreateStepMaterialRequirement,
  useUpdateStepMaterialRequirement,
  useDeleteStepMaterialRequirement,
  useRouteMaterials,
} from "../../hooks/useProductDef";
import { useMaterials } from "../../hooks/useMaterial";
import { useUoMs } from "../../hooks/useUoM";
import type { MaterialUse } from "../../types";

interface Props {
  stepId: string;
  routeId: string;
}

export default function MaterialRequirementsEditor({ stepId, routeId }: Props) {
  const { data: reqsResp, isLoading } = useStepMaterialRequirements(stepId);
  const reqs = reqsResp?.data ?? [];
  const createMut = useCreateStepMaterialRequirement(stepId);
  const updateMut = useUpdateStepMaterialRequirement(stepId);
  const deleteMut = useDeleteStepMaterialRequirement(stepId);

  const { data: routeMatsResp } = useRouteMaterials(routeId);
  const routeMaterialIds = new Set((routeMatsResp?.data ?? []).map((a) => a.material_id));

  const stepMaterialIds = new Set(reqs.map((r) => r.material_id));

  const { data: matResp } = useMaterials();
  const allMaterials = matResp?.data ?? [];
  // Full lookup used to display already-assigned requirements
  const matMap = new Map(allMaterials.map((m) => [m.id, m]));
  // Dropdown only shows route-assigned materials not yet on this step
  const materials = allMaterials
    .filter((m) => routeMaterialIds.has(m.id) && !stepMaterialIds.has(m.id))
    .sort((a, b) => a.code.localeCompare(b.code));

  const { data: uomData } = useUoMs();
  const nonRateUoMs = (uomData?.data ?? []).filter((u) => u.uom_type !== "rate");

  const [materialId, setMaterialId] = useState<string>("");
  const [quantity, setQuantity] = useState<string>("1");
  const [uomId, setUomId] = useState<string>("");
  const [materialUse, setMaterialUse] = useState<MaterialUse>("consumed");
  const [position, setPosition] = useState<string>("0");
  const [description, setDescription] = useState<string>("");
  const [formError, setFormError] = useState<string | null>(null);

  const handleMaterialChange = (id: string) => {
    setMaterialId(id);
    const m = matMap.get(id);
    if (m) setUomId(m.uom_id);
  };

  const handleAdd = async () => {
    setFormError(null);
    if (!materialId) {
      setFormError("Select a material.");
      return;
    }
    const qty = parseFloat(quantity);
    if (!(qty > 0)) {
      setFormError("Quantity must be greater than 0.");
      return;
    }
    const pos = parseInt(position, 10);
    try {
      await createMut.mutateAsync({
        material_id: materialId,
        quantity: qty,
        uom_id: uomId || (nonRateUoMs[0]?.id ?? ""),
        material_use: materialUse,
        position: Number.isFinite(pos) ? pos : 0,
        description: description.trim() || null,
      });
      setMaterialId("");
      setQuantity("1");
      setUomId("");
      setMaterialUse("consumed");
      setPosition("0");
      setDescription("");
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? "Failed to add material requirement.");
    }
  };

  const materialLabel = (r: (typeof reqs)[number]): string => {
    const m = matMap.get(r.material_id);
    return m ? `${m.code} — ${m.name}` : "(unknown material)";
  };

  const useBadge = (u: MaterialUse) => {
    const styles: Record<MaterialUse, string> = {
      consumed: "bg-amber-100 text-amber-800",
      produced: "bg-emerald-100 text-emerald-800",
    };
    return (
      <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${styles[u]}`}>
        {u}
      </span>
    );
  };

  const sortedReqs = reqs.slice().sort((a, b) => a.position - b.position);

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-gray-800">Material Requirements</h4>
          <p className="text-xs text-gray-500">
            Step-level BOM: materials consumed or produced at this segment.
          </p>
        </div>
      </div>

      {isLoading ? (
        <p className="text-xs text-gray-500">Loading…</p>
      ) : sortedReqs.length === 0 ? (
        <p className="rounded border border-dashed border-gray-300 bg-white px-3 py-2 text-xs text-gray-500">
          No material requirements defined for this segment.
        </p>
      ) : (
        <ul className="space-y-1">
          {sortedReqs.map((r) => (
            <li
              key={r.id}
              className="flex items-center gap-2 rounded border border-gray-200 bg-white px-2 py-1.5 text-xs"
            >
              <span className="w-8 shrink-0 text-gray-400">#{r.position}</span>
              <span className="flex-1 truncate text-gray-800">{materialLabel(r)}</span>
              <input
                type="number"
                step="any"
                min="0"
                value={r.quantity}
                onChange={(e) => {
                  const v = parseFloat(e.target.value);
                  if (v > 0) updateMut.mutate({ id: r.id, quantity: v });
                }}
                className="w-20 rounded border border-gray-300 px-1.5 py-0.5 text-right text-xs"
              />
              <input
                type="text"
                value={r.uom_symbol ?? ""}
                readOnly
                className="w-14 rounded border border-gray-300 bg-gray-50 px-1.5 py-0.5 text-xs"
              />
              <select
                value={r.material_use}
                onChange={(e) =>
                  updateMut.mutate({
                    id: r.id,
                    material_use: e.target.value as MaterialUse,
                  })
                }
                className="rounded border border-gray-300 bg-white px-1.5 py-0.5 text-xs"
              >
                <option value="consumed">consumed</option>
                <option value="produced">produced</option>
              </select>
              {useBadge(r.material_use)}
              <button
                type="button"
                onClick={() => deleteMut.mutate(r.id)}
                className="rounded p-1 text-gray-400 hover:text-red-600"
                aria-label="Remove material requirement"
              >
                <TrashIcon className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 rounded border border-gray-200 bg-white p-2 space-y-2">
        {/* Row 1: material selector */}
        <select
          value={materialId}
          onChange={(e) => handleMaterialChange(e.target.value)}
          className="block w-full rounded border border-gray-300 bg-white px-2 py-1 text-xs"
        >
          <option value="">— Select material —</option>
          {materials.map((m) => (
            <option key={m.id} value={m.id}>
              {m.code} — {m.name} ({m.material_type})
            </option>
          ))}
        </select>
        {/* Row 2: qty, UoM, use, position, Add */}
        <div className="flex items-end gap-2">
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-medium text-gray-500">Quantity</label>
            <input
              type="number"
              step="any"
              min="0"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-16 rounded border border-gray-300 px-2 py-1 text-right text-xs"
            />
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <label className="text-[10px] font-medium text-gray-500">UoM</label>
            <select
              value={uomId}
              onChange={(e) => setUomId(e.target.value)}
              className="w-full rounded border border-gray-300 bg-white px-2 py-1 text-xs"
            >
              <option value="">— UoM —</option>
              {nonRateUoMs.map((u) => (
                <option key={u.id} value={u.id}>{u.symbol}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-medium text-gray-500">Use</label>
            <select
              value={materialUse}
              onChange={(e) => setMaterialUse(e.target.value as MaterialUse)}
              className="rounded border border-gray-300 bg-white px-2 py-1 text-xs"
            >
              <option value="consumed">consumed</option>
              <option value="produced">produced</option>
            </select>
          </div>
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-medium text-gray-500">Position</label>
            <input
              type="number"
              min="0"
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              title="Sort order within the step's material list"
              className="w-16 rounded border border-gray-300 px-2 py-1 text-right text-xs"
            />
          </div>
          <button
            type="button"
            onClick={handleAdd}
            disabled={createMut.isPending || !materialId}
            className="inline-flex shrink-0 items-center gap-1 rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
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
