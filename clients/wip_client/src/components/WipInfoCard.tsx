import { useQuery } from "@tanstack/react-query";
import type { StepContext, Unit, Lot } from "../types";
import { fetchProducts } from "../api/wip";

/** Status badge colors (plan §5): queued=gray, in_process=blue,
    completed=green, scrapped=red, on_hold=yellow. */
const STATUS_BADGE: Record<string, string> = {
  queued: "bg-gray-200 text-gray-700",
  in_process: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  finished: "bg-teal-100 text-teal-700",
  scrapped: "bg-red-100 text-red-700",
  on_hold: "bg-yellow-100 text-yellow-800",
};

function Row({
  label,
  value,
  wide,
  mono,
}: {
  label: string;
  value: string;
  wide?: boolean;
  mono?: boolean;
}) {
  return (
    <div className={wide ? "sm:col-span-2" : undefined}>
      <dt className="text-xs uppercase tracking-wide text-gray-400">{label}</dt>
      <dd className={`text-gray-800 ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}


interface Props {
  context: StepContext;
  /** Resolved by MainTab from the step-equipment rows (falls back to the raw id). */
  assignedEquipmentCode?: string | null;
}

export default function WipInfoCard({ context, assignedEquipmentCode }: Props) {
  const { wip_type, wip, step } = context;
  const isUnit = wip_type === "unit";
  const unit = wip as Unit;
  const lot = wip as Lot;

  // Product name display — cached per product id (["product", productId]).
  const productId = wip.product_id;
  const { data: productName } = useQuery({
    queryKey: ["product", productId],
    queryFn: async () => {
      const products = await fetchProducts();
      return products.find((p) => p.id === productId)?.name ?? null;
    },
    enabled: Boolean(productId),
    staleTime: 5 * 60_000,
  });

  return (
    <div className="bg-white rounded-lg shadow-md p-5 space-y-3">
      {/* Identity line */}
      <div className="flex items-center gap-3 flex-wrap">
        <span
          className={`px-2 py-0.5 rounded text-xs font-bold tracking-wide ${
            isUnit ? "bg-indigo-100 text-indigo-700" : "bg-purple-100 text-purple-700"
          }`}
        >
          {isUnit ? "UNIT" : "LOT"}
        </span>
        <span className="font-mono text-lg font-semibold text-gray-900">
          {isUnit ? unit.serial_number : lot.lot_number}
        </span>
        <span
          className={`ml-auto px-2.5 py-1 rounded-full text-xs font-semibold uppercase ${
            STATUS_BADGE[wip.status] ?? "bg-gray-100 text-gray-600"
          }`}
        >
          {wip.status.replace("_", " ")}
        </span>
      </div>

      {/* Detail rows */}
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <Row label="Order" value={wip.order_number ?? "—"} />
        <Row label="Product" value={productName ?? productId} />
        {!isUnit && (
          <Row
            label="Quantity"
            value={`${lot.quantity} ${lot.uom_symbol ?? ""}`.trim()}
          />
        )}
        <Row
          label="Current Step"
          value={step ? `${step.sequence} – ${step.name}` : "No current step"}
        />
        <Row
          label="Assigned Equipment"
          value={
            assignedEquipmentCode ??
            wip.current_equipment_id ??
            "None"
          }
          mono
        />
        {wip.hold_reason && <Row label="Hold Reason" value={wip.hold_reason} wide />}
      </dl>
    </div>
  );
}
