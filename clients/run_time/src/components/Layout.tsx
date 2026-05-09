import {
  QueueListIcon,
  WrenchScrewdriverIcon,
  ChartBarIcon,
  BellAlertIcon,
  ArchiveBoxIcon,
  CpuChipIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import type { ReactNode } from "react";
import { useState } from "react";
import AboutDialog from "./AboutDialog";

export type TabId = "dashboard" | "wip" | "orders" | "inventory" | "equipment" | "events";

const tabs: { id: TabId; label: string; icon: typeof QueueListIcon }[] = [
  { id: "dashboard", label: "Dashboard", icon: ChartBarIcon },
  { id: "wip", label: "WIP", icon: WrenchScrewdriverIcon },
  { id: "orders", label: "Orders", icon: QueueListIcon },
  { id: "inventory", label: "Inventory", icon: ArchiveBoxIcon },
  { id: "equipment", label: "Equipment", icon: CpuChipIcon },
  { id: "events", label: "Live Events", icon: BellAlertIcon },
];

interface LayoutProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  wsConnected: boolean;
  children: ReactNode;
}

export default function Layout({ activeTab, onTabChange, wsConnected, children }: LayoutProps) {
  const [showAbout, setShowAbout] = useState(false);
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {showAbout && <AboutDialog onClose={() => setShowAbout(false)} />}
      {/* Header */}
      <header className="bg-indigo-700 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <WrenchScrewdriverIcon className="h-7 w-7" />
            <h1 className="text-xl font-bold tracking-tight">MES Runtime — Shop Floor</h1>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <button
              onClick={() => setShowAbout(true)}
              className="text-indigo-200 hover:text-white transition-colors"
              aria-label="About"
            >
              <InformationCircleIcon className="h-5 w-5" />
            </button>
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${wsConnected ? "bg-green-400" : "bg-red-400"}`} />
            <span>{wsConnected ? "Live" : "Offline"}</span>
          </div>
        </div>
      </header>

      {/* Tab bar */}
      <nav className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto">
          {tabs.map((t) => {
            const Icon = t.icon;
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => onTabChange(t.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  active
                    ? "border-indigo-600 text-indigo-700"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <Icon className="h-5 w-5" />
                {t.label}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  );
}
