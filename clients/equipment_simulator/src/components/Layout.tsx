import { useState } from "react";
import type { ReactNode } from "react";

const tabs = [
  { id: "dashboard", label: "Dashboard", section: "Overview" },
  { id: "equipment", label: "Equipment", section: "Operations" },
  { id: "history", label: "State History", section: "Operations" },
  { id: "oee", label: "OEE Analysis", section: "Operations" },
  { id: "simulator", label: "Auto-Simulator", section: "Tools" },
  { id: "models", label: "State Models", section: "Reference" },
] as const;

export type TabId = (typeof tabs)[number]["id"];

interface LayoutProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  children: ReactNode;
  treePanel?: ReactNode;
}

export default function Layout({ activeTab, onTabChange, children, treePanel }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const sections = [...new Set(tabs.map((t) => t.section))];

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "w-56" : "w-0 overflow-hidden"
        } bg-gray-900 text-gray-300 flex flex-col transition-all duration-200`}
      >
        <div className="px-4 py-4 flex items-center gap-2 border-b border-gray-700">
          <div className="w-7 h-7 bg-emerald-600 rounded flex items-center justify-center text-white text-xs font-bold">
            AVL
          </div>
          <span className="text-sm font-semibold text-white whitespace-nowrap">
            Availability Sim
          </span>
        </div>

        <nav className="flex-1 overflow-y-auto py-2 text-sm">
          {sections.map((section) => (
            <div key={section}>
              <div className="px-3 py-2 text-xs font-semibold uppercase text-gray-500">
                {section}
              </div>
              {tabs
                .filter((t) => t.section === section)
                .map((t) => (
                  <button
                    key={t.id}
                    onClick={() => onTabChange(t.id)}
                    className={`block w-full text-left px-4 py-1.5 hover:bg-gray-800 ${
                      activeTab === t.id
                        ? "bg-gray-800 text-white border-l-2 border-emerald-400"
                        : ""
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
            </div>
          ))}
        </nav>
      </aside>

      {/* Equipment tree panel */}
      {treePanel && (
        <div className="w-64 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
          <div className="px-3 py-3 border-b border-gray-200">
            <h2 className="text-xs font-semibold uppercase text-gray-500">Equipment</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {treePanel}
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white shadow-sm px-4 py-2 flex items-center gap-3 border-b">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="text-base font-semibold text-gray-800">
            {tabs.find((t) => t.id === activeTab)?.label}
          </h1>
        </header>
        <main className="flex-1 overflow-auto p-4">{children}</main>
      </div>
    </div>
  );
}
