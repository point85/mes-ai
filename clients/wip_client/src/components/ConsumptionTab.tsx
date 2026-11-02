import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { BOMItem, StepContext } from "../types";
import {
  apiErrorMessage,
  consumeMaterial,
  fetchConsumedMaterials,
  fetchMaterialLotByNumber,
  fetchMaterialLots,
  fetchMaterials,
  fetchStepBomItems,
} from "../api/wip";

interface Props {
  context: StepContext;
}

export default function ConsumptionTab({ context }: Props) {
  const queryClient = useQueryClient();
  const { wip, wip_type, step } = context;
  const isUnit = wip_type === "unit";

  const [lotInputs, setLotInputs] = useState<Record<string, string>>({});
  const [qtyInputs, setQtyInputs] = useState<Record<string, string>>({});
  const [consumingId, setConsumingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // BOM items for the current step (visible in any status; consuming
  // requires the WIP to be in_process).
  const { data: bomItems = [] } = useQuery({
    queryKey: ["step-bom-items", step?.id],
    queryFn: () => fetchStepBomItems(step!.id),
    enabled: !!step,
  });

  // Reference data + pick lists (only needed while processing).
  const { data: materials = [] } = useQuery({
    queryKey: ["materials"],
    queryFn: fetchMaterials,
    enabled: !!step && wip.status === "in_process",
  });
  const { data: materialLots = [] } = useQuery({
    queryKey: ["material-lots-available"],
    queryFn: () => fetchMaterialLots(),
    enabled: !!step && wip.status === "in_process",
  });
  const { data: consumedMaterials = [], refetch: refetchConsumed } = useQuery({
    queryKey: ["consumed-materials", wip_type, wip.id],
    queryFn: () => fetchConsumedMaterials(wip_type, wip.id),
    enabled: !!step,
  });

  const handleConsumeLine = async (bomItem: BOMItem, materialId: string | undefined) => {
    const lotNumber = lotInputs[bomItem.id]?.trim();
    const qty = qtyInputs[bomItem.id];
    if (!lotNumber) return;
    setConsumingId(bomItem.id);
    setError(null);
    setMessage(null);
    try {
      // The operator scans or types a lot / serial number; resolve it to the material lot.
      const materialLot = await fetchMaterialLotByNumber(lotNumber);
      if (!materialLot || (materialId && materialLot.material_id !== materialId)) {
        setError(`'${lotNumber}' is not a valid lot or serial number for ${bomItem.material_code}`);
        return;
      }
      // Unit-tracked material is always consumed one at a time; no quantity is entered.
      const isUnitTracked = materialLot.tracking_method === "unit";
      if (!isUnitTracked && !(parseFloat(qty ?? "") > 0)) {
        setError("Enter the quantity to consume");
        return;
      }
      await consumeMaterial(materialLot.id, {
        ...(isUnit ? { unit_id: wip.id } : { lot_id: wip.id }),
        step_id: step?.id,
        ...(isUnitTracked ? {} : { quantity_consumed: parseFloat(qty) }),
      });
      setMessage(
        isUnitTracked
          ? `Consumed ${lotNumber} of ${bomItem.material_code}`
          : `Consumed ${qty} ${bomItem.uom_symbol ?? ""} of ${bomItem.material_code}`,
      );
      // Keep the lot so the operator can consume more from it; a unit
      // (serial number) is gone once consumed, so clear it.
      if (isUnitTracked) setLotInputs((prev) => ({ ...prev, [bomItem.id]: "" }));
      setQtyInputs((prev) => ({ ...prev, [bomItem.id]: "" }));
      await refetchConsumed();
      await queryClient.invalidateQueries({ queryKey: ["material-lots-available"] });
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setConsumingId(null);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-5 space-y-4">
      <h4 className="font-semibold text-gray-700">Material Consumption</h4>

      {error && (
        <div role="alert" className="p-3 bg-red-50 text-red-700 text-sm rounded-md">
          {error}
        </div>
      )}
      {message && !error && (
        <div role="status" className="p-3 bg-green-50 text-green-700 text-sm rounded-md">
          {message}
        </div>
      )}

      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
            <th className="px-3 py-2.5">Material</th>
            <th className="px-3 py-2.5">Required</th>
            <th className="px-3 py-2.5">UoM</th>
            <th className="px-3 py-2.5">Consumed</th>
            {wip.status === "in_process" && (
              <>
                <th className="px-3 py-2.5 min-w-[180px]">Lot / Serial #</th>
                <th className="px-3 py-2.5 w-24">Qty</th>
                <th className="px-3 py-2.5"></th>
              </>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {bomItems.map((bi) => {
            // Resolve the material id for this BOM item's code so we can
            // offer only the available lots of that material.
            const mat = materials.find((m) => m.code === bi.material_code);
            // All lots of the material are used to total what was consumed; only
            // available ones are offered as suggestions.
            const materialLotsOfBom = mat
              ? materialLots.filter((ml) => ml.material_id === mat.id)
              : [];
            const matchingLots = materialLotsOfBom.filter((ml) => ml.status === "available");
            // Sum what has already been consumed for this material.
            const matchingLotIds = new Set(materialLotsOfBom.map((ml) => ml.id));
            const totalConsumed = consumedMaterials
              .filter((c) => matchingLotIds.has(c.material_lot_id))
              .reduce((sum, c) => sum + c.quantity_consumed, 0);
            const typedNumber = (lotInputs[bi.id] ?? "").trim();
            // Quantity is only asked for when the entered number is not a unit-tracked serial number.
            const isUnitTracked = matchingLots.some(
              (ml) => ml.lot_number === typedNumber && ml.tracking_method === "unit",
            );
            return (
              <tr key={bi.id}>
                <td className="px-3 py-2.5 font-mono font-medium text-gray-900">
                  {bi.material_code}
                </td>
                <td className="px-3 py-2.5 text-gray-700">{bi.quantity}</td>
                <td className="px-3 py-2.5 text-gray-700">{bi.uom_symbol ?? "—"}</td>
                <td
                  className={`px-3 py-2.5 font-mono ${
                    totalConsumed >= bi.quantity ? "text-green-600" : "text-gray-500"
                  }`}
                >
                  {totalConsumed > 0 ? totalConsumed : "—"}
                </td>
                {wip.status === "in_process" && (
                  <>
                    <td className="px-3 py-2.5">
                      <input
                        type="text"
                        list={`lots-${bi.id}`}
                        value={lotInputs[bi.id] ?? ""}
                        onChange={(e) =>
                          setLotInputs((prev) => ({ ...prev, [bi.id]: e.target.value }))
                        }
                        placeholder="Scan or enter number"
                        aria-label={`Lot or serial number for ${bi.material_code}`}
                        className="input-field max-w-[180px]"
                      />
                      <datalist id={`lots-${bi.id}`}>
                        {matchingLots.map((ml) => (
                          <option
                            key={ml.id}
                            value={ml.lot_number}
                            label={
                              ml.tracking_method === "unit"
                                ? undefined
                                : `${ml.lot_number} (${ml.quantity_on_hand})`
                            }
                          />
                        ))}
                      </datalist>
                    </td>
                    <td className="px-3 py-2.5">
                      {!isUnitTracked && (
                        <input
                          type="number"
                          min="0"
                          value={qtyInputs[bi.id] ?? ""}
                          onChange={(e) =>
                            setQtyInputs((prev) => ({ ...prev, [bi.id]: e.target.value }))
                          }
                          aria-label={`Quantity to consume of ${bi.material_code}`}
                          className="input-field w-20"
                        />
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <button
                        onClick={() => handleConsumeLine(bi, mat?.id)}
                        disabled={
                          consumingId !== null ||
                          !typedNumber ||
                          (!isUnitTracked && !(parseFloat(qtyInputs[bi.id] ?? "") > 0))
                        }
                        className="btn-primary !px-3 !py-1.5 text-xs"
                      >
                        {consumingId === bi.id ? "…" : "Consume"}
                      </button>
                    </td>
                  </>
                )}
              </tr>
            );
          })}
          {bomItems.length === 0 && (
            <tr>
              <td colSpan={7} className="px-3 py-6 text-center text-gray-400">
                No materials are defined for this step.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {wip.status === "in_process" && bomItems.length > 0 && (
        <p className="text-xs text-gray-400">
          Scan or enter the lot or serial number for each required material; enter a quantity when asked.
        </p>
      )}
    </div>
  );
}

