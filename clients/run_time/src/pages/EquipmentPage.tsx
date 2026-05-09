import { useState } from "react";
import EquipmentStatusPage from "./EquipmentStatusPage";
import PerformancePage from "./performance/PerformancePage";

type EquipTab = "monitor" | "performance";

const TABS: { id: EquipTab; label: string }[] = [
  { id: "monitor", label: "Monitor" },
  { id: "performance", label: "Performance" },
];

export default function EquipmentPage() {
  const [tab, setTab] = useState<EquipTab>("monitor");

  return (
    <div className="space-y-4">
      <div className="flex gap-1 border-b">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className={tab === "monitor" ? undefined : "hidden"}>
        <EquipmentStatusPage />
      </div>
      <div className={tab === "performance" ? undefined : "hidden"}>
        <PerformancePage />
      </div>
    </div>
  );
}
