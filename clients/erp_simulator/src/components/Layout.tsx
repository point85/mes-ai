import { useState } from "react";
import type { ReactNode } from "react";

const tabs = [
  { id: "dashboard", label: "Dashboard" },
  { id: "orders", label: "Production Orders" },
  { id: "materials", label: "Materials" },
  { id: "products", label: "Products" },
  { id: "boms", label: "BOMs" },
  { id: "routings", label: "Routings" },
  { id: "work-centers", label: "Work Centers" },
  { id: "completion", label: "Report Completion" },
  { id: "consumption", label: "Report Consumption" },
  { id: "scrap", label: "Report Scrap" },
  { id: "labor", label: "Report Labor" },
  { id: "downtime", label: "Report Downtime" },
  { id: "quality", label: "Report Quality" },
  { id: "confirmations", label: "Confirmations" },
] as const;

export type TabId = (typeof tabs)[number]["id"];

interface LayoutProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  children: ReactNode;
}

export default function Layout({ activeTab, onTabChange, children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const inboundTabs = tabs.filter((t) =>
    ["dashboard", "orders", "materials", "products", "boms", "routings", "work-centers"].includes(t.id)
  );
  const outboundTabs = tabs.filter((t) =>
    ["completion", "consumption", "scrap", "labor", "downtime", "quality", "confirmations"].includes(t.id)
  );

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "w-56" : "w-0 overflow-hidden"
        } bg-gray-900 text-gray-300 flex flex-col transition-all duration-200`}
      >
        <div className="px-4 py-4 flex items-center gap-2 border-b border-gray-700">
          <div className="w-7 h-7 bg-blue-500 rounded flex items-center justify-center text-white text-xs font-bold">
            SAP
          </div>
          <span className="text-sm font-semibold text-white whitespace-nowrap">
            ERP Simulator
          </span>
        </div>

        <nav className="flex-1 overflow-y-auto py-2 text-sm">
          <div className="px-3 py-2 text-xs font-semibold uppercase text-gray-500">
            Inbound (ERP → MES)
          </div>
          {inboundTabs.map((t) => (
            <button
              key={t.id}
              onClick={() => onTabChange(t.id)}
              className={`block w-full text-left px-4 py-1.5 hover:bg-gray-800 ${
                activeTab === t.id
                  ? "bg-gray-800 text-white border-l-2 border-blue-400"
                  : ""
              }`}
            >
              {t.label}
            </button>
          ))}

          <div className="px-3 py-2 mt-3 text-xs font-semibold uppercase text-gray-500">
            Outbound (MES → ERP)
          </div>
          {outboundTabs.map((t) => (
            <button
              key={t.id}
              onClick={() => onTabChange(t.id)}
              className={`block w-full text-left px-4 py-1.5 hover:bg-gray-800 ${
                activeTab === t.id
                  ? "bg-gray-800 text-white border-l-2 border-blue-400"
                  : ""
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </aside>

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
