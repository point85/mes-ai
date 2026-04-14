/**
 * Sidebar navigation for the DT-CLIENT.
 * Each section corresponds to a server module's CRUD editor.
 * New editors are added here as they're implemented.
 */

import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  HomeIcon,
  ScaleIcon,
  CubeIcon,
  Cog6ToothIcon,
  BuildingOffice2Icon,
  BeakerIcon,
  ClipboardDocumentListIcon,
  ClipboardDocumentCheckIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  LinkIcon,
  ArrowsRightLeftIcon,
  PuzzlePieceIcon,
  QueueListIcon,
  ArchiveBoxIcon,
  Square3Stack3DIcon,
  ClipboardDocumentIcon,
  ServerIcon,
  InboxArrowDownIcon,
  PaperAirplaneIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";

interface NavItem {
  label: string;
  to: string;
  icon: React.ElementType;
}

interface NavSubsection {
  title: string;
  items: NavItem[];
}

interface NavSection {
  title: string;
  items?: NavItem[];
  subsections?: NavSubsection[];
}

const sections: NavSection[] = [
  {
    title: "Definitions",
    items: [
      { label: "Units of Measure", to: "/uom", icon: ScaleIcon },
      { label: "Data Definitions", to: "/data-definitions", icon: ClipboardDocumentListIcon },
    ],
  },
  {
    title: "Plant Model",
    items: [
      { label: "Sites", to: "/sites", icon: BuildingOffice2Icon },
    ],
  },
  {
    title: "Products",
    items: [
      { label: "Products", to: "/products", icon: CubeIcon },
      { label: "Routes", to: "/routes", icon: QueueListIcon },
      { label: "Materials", to: "/materials", icon: BeakerIcon },
    ],
  },
  {
    title: "Production",
    items: [
      { label: "Orders", to: "/orders", icon: ClipboardDocumentCheckIcon },
    ],
  },
  {
    title: "Quality",
    items: [
      { label: "Quality Tests", to: "/quality-tests", icon: ShieldCheckIcon },
      { label: "Non-Conformances", to: "/non-conformances", icon: ExclamationTriangleIcon },
    ],
  },
  {
    title: "Operations",
    items: [
      { label: "Performance", to: "/performance", icon: ChartBarIcon },
      { label: "Genealogy", to: "/genealogy", icon: LinkIcon },
      { label: "Dispatch", to: "/dispatch", icon: ArrowsRightLeftIcon },
      { label: "Storage Locations", to: "/storage-locations", icon: ArchiveBoxIcon },
      { label: "Inventory Balances", to: "/inventory/balances", icon: Square3Stack3DIcon },
      { label: "Inventory Log", to: "/inventory/transactions", icon: ClipboardDocumentIcon },
    ],
  },
  {
    title: "Admin",
    items: [
      { label: "Plugins", to: "/plugins", icon: PuzzlePieceIcon },
      { label: "Settings", to: "/settings", icon: Cog6ToothIcon },
    ],
  },
  {
    title: "ERP Simulator",
    subsections: [
      {
        title: "Inbound",
        items: [
          { label: "ERP Dashboard", to: "/erp-simulator", icon: ServerIcon },
          { label: "ERP Orders", to: "/erp-simulator/orders", icon: ClipboardDocumentCheckIcon },
          { label: "ERP Materials", to: "/erp-simulator/materials", icon: BeakerIcon },
          { label: "ERP Products", to: "/erp-simulator/products", icon: CubeIcon },
        ],
      },
      {
        title: "Outbound",
        items: [
          { label: "Report Completion", to: "/erp-simulator/completion", icon: InboxArrowDownIcon },
          { label: "Report Consumption", to: "/erp-simulator/consumption", icon: InboxArrowDownIcon },
          { label: "Report Scrap", to: "/erp-simulator/scrap", icon: InboxArrowDownIcon },
          { label: "Report Labor", to: "/erp-simulator/labor", icon: InboxArrowDownIcon },
          { label: "Report Downtime", to: "/erp-simulator/downtime", icon: InboxArrowDownIcon },
          { label: "Report Quality", to: "/erp-simulator/quality", icon: InboxArrowDownIcon },
          { label: "Confirmations", to: "/erp-simulator/confirmations", icon: PaperAirplaneIcon },
        ],
      },
    ],
  },
];

/** Collect all items from a section, including items nested inside subsections */
function allSectionItems(section: NavSection): NavItem[] {
  const direct = section.items ?? [];
  const nested = (section.subsections ?? []).flatMap((s) => s.items);
  return [...direct, ...nested];
}

function isItemActive(item: NavItem, pathname: string) {
  return pathname === item.to || pathname.startsWith(item.to + "/");
}

export default function Sidebar() {
  const location = useLocation();

  // Auto-expand sections (and subsections) whose route is currently active
  const initialOpen = new Set<string>();
  for (const section of sections) {
    if (allSectionItems(section).some((item) => isItemActive(item, location.pathname))) {
      initialOpen.add(section.title);
      for (const sub of section.subsections ?? []) {
        if (sub.items.some((item) => isItemActive(item, location.pathname))) {
          initialOpen.add(sub.title);
        }
      }
    }
  }

  const [open, setOpen] = useState<Set<string>>(initialOpen);

  const toggle = (title: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(title)) next.delete(title);
      else next.add(title);
      return next;
    });

  /** Render a list of NavItems */
  const renderItems = (items: NavItem[]) => (
    <ul className="mt-0.5 mb-1 space-y-0.5">
      {items.map((item) => (
        <li key={item.to}>
          <NavLink
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-700 hover:bg-gray-100"
              }`
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        </li>
      ))}
    </ul>
  );

  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
      {/* Logo / Title */}
      <div className="px-4 py-4 border-b border-gray-200">
        <NavLink to="/" className="flex items-center gap-2 group">
          <HomeIcon className="h-5 w-5 text-indigo-600 group-hover:text-indigo-700 transition-colors" />
          <div>
            <h1 className="text-lg font-bold text-gray-800 tracking-tight group-hover:text-indigo-700 transition-colors">
              MES AI
            </h1>
            <p className="text-xs text-gray-500">Dashboard</p>
          </div>
        </NavLink>
      </div>

      {/* Nav sections — accordion */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        {sections.map((section) => {
          const isOpen = open.has(section.title);
          const hasActive = allSectionItems(section).some((item) =>
            isItemActive(item, location.pathname),
          );

          return (
            <div key={section.title}>
              <button
                onClick={() => toggle(section.title)}
                className={`flex w-full items-center justify-between rounded-md px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors ${
                  hasActive ? "text-indigo-600" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                {section.title}
                <ChevronRightIcon
                  className={`h-3 w-3 transition-transform duration-150 ${isOpen ? "rotate-90" : ""}`}
                />
              </button>

              {isOpen && section.items && renderItems(section.items)}

              {isOpen && section.subsections?.map((sub) => {
                const subOpen = open.has(sub.title);
                const subActive = sub.items.some((item) =>
                  isItemActive(item, location.pathname),
                );

                return (
                  <div key={sub.title} className="pl-2">
                    <button
                      onClick={() => toggle(sub.title)}
                      className={`flex w-full items-center justify-between rounded-md px-2 py-1 text-[10px] font-semibold uppercase tracking-wider transition-colors ${
                        subActive ? "text-indigo-600" : "text-gray-400 hover:text-gray-500"
                      }`}
                    >
                      {sub.title}
                      <ChevronRightIcon
                        className={`h-2.5 w-2.5 transition-transform duration-150 ${subOpen ? "rotate-90" : ""}`}
                      />
                    </button>

                    {subOpen && renderItems(sub.items)}
                  </div>
                );
              })}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
