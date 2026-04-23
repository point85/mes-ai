/**
 * "+N" indicator shown next to a step's primary Equipment Class, representing
 * how many additional SegmentEquipmentRequirement rows exist for that step.
 */

import { useStepEquipmentRequirements } from "../../hooks/useProductDef";

interface Props {
  stepId: string;
}

export default function StepEquipReqCountBadge({ stepId }: Props) {
  const { data } = useStepEquipmentRequirements(stepId);
  const count = data?.data?.length ?? 0;
  if (count === 0) return null;
  return (
    <span
      className="ml-1 inline-flex items-center rounded-full bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-800"
      title={`${count} additional equipment requirement${count === 1 ? "" : "s"}`}
    >
      +{count}
    </span>
  );
}
