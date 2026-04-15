/**
 * Sidebar navigation for the DT-CLIENT.
 * Each section corresponds to a server module's CRUD editor.
 * New editors are added here as they're implemented.
 */

import { NavLink } from "react-router-dom";
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
} from "@heroicons/react/24/outline";

interface NavItem {
  label: string;
  to: string;
  icon: React.ElementType;
}

interface NavSection {
  title: string;
  items: NavItem[];
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
];

export default function Sidebar() {
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

      {/* Nav sections */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        {sections.map((section) => (
          <div key={section.title}>
            <span className="block px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
              {section.title}
            </span>
            <ul className="mt-0.5 mb-1 space-y-0.5">
              {section.items.map((item) => (
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
          </div>
        ))}
      </nav>
    </aside>
  );
}
