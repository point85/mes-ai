import { useState } from "react";
import ScanPage from "./ScanPage";
import ActiveWipPage from "./ActiveWipPage";

type WipTab = "scan" | "active";

const WIP_TABS: { id: WipTab; label: string }[] = [
  { id: "scan", label: "Scan WIP" },
  { id: "active", label: "Active WIP" },
];

export default function WipPage() {
  const [tab, setTab] = useState<WipTab>("scan");

  return (
    <div className="space-y-4">
      <div className="flex gap-1 border-b">
        {WIP_TABS.map((t) => (
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

      <div className={tab === "scan" ? undefined : "hidden"}>
        <ScanPage />
      </div>
      <div className={tab === "active" ? undefined : "hidden"}>
        <ActiveWipPage />
      </div>
    </div>
  );
}
