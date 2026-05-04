/**
 * Sidebar navigation for the DT-CLIENT.
 * Each section corresponds to a server module's CRUD editor.
 * New editors are added here as they're implemented.
 */

import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  HomeIcon,
  ScaleIcon,
  CubeIcon,
  Cog6ToothIcon,
  BuildingOffice2Icon,
  BeakerIcon,
  ClipboardDocumentListIcon,
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
  TagIcon,
  WrenchScrewdriverIcon,
  QuestionMarkCircleIcon,
  CalendarDaysIcon,
  InformationCircleIcon,
  UsersIcon,
  ArrowRightOnRectangleIcon,
} from "@heroicons/react/24/outline";
import HelpDialog, { type HelpTopic } from "../HelpDialog";
import AboutDialog from "../AboutDialog";
import { useAuth } from "../../contexts/AuthContext";

interface NavItem {
  label: string;
  to: string;
  icon: React.ElementType;
  helpTopic?: HelpTopic;
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
      { label: "Work Schedules", to: "/work-schedules", icon: CalendarDaysIcon },
      { label: "Data Definitions", to: "/data-definitions", icon: ClipboardDocumentListIcon },
    ],
  },
  {
    title: "Plant Model",
    items: [
      { label: "Sites", to: "/sites", icon: BuildingOffice2Icon },
      { label: "Equipment Classes", to: "/equipment-classes", icon: WrenchScrewdriverIcon },
    ],
  },
  {
    title: "Products",
    items: [
      { label: "Products", to: "/products", icon: CubeIcon, helpTopic: "products" as HelpTopic },
      { label: "Routes", to: "/routes", icon: QueueListIcon },
      { label: "Dispositions", to: "/dispositions", icon: TagIcon },
      { label: "Materials", to: "/materials", icon: BeakerIcon, helpTopic: "materials" as HelpTopic },
      { label: "Material Lots", to: "/material-lots", icon: BeakerIcon },
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
      { label: "Users", to: "/admin/users", icon: UsersIcon },
      { label: "Roles", to: "/admin/roles", icon: ShieldCheckIcon },
      { label: "Plugins", to: "/plugins", icon: PuzzlePieceIcon },
      { label: "Settings", to: "/settings", icon: Cog6ToothIcon },
    ],
  },
];

export default function Sidebar() {
  const [helpTopic, setHelpTopic] = useState<HelpTopic | null>(null);
  const [showAbout, setShowAbout] = useState(false);
  const { authMode, currentUser, logout } = useAuth();

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
                <li key={item.to} className="flex items-center">
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      `flex flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-indigo-50 text-indigo-700"
                          : "text-gray-700 hover:bg-gray-100"
                      }`
                    }
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                  {item.helpTopic && (
                    <button
                      onClick={() => setHelpTopic(item.helpTopic!)}
                      className="ml-0.5 rounded p-0.5 text-gray-400 hover:text-indigo-600 hover:bg-gray-100 transition-colors"
                      title={`Help: ${item.label}`}
                    >
                      <QuestionMarkCircleIcon className="h-3.5 w-3.5" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {helpTopic && (
        <HelpDialog topic={helpTopic} onClose={() => setHelpTopic(null)} />
      )}
      {showAbout && (
        <AboutDialog onClose={() => setShowAbout(false)} />
      )}

      {/* Footer — current user + About */}
      <div className="border-t border-gray-200 px-4 py-3 space-y-2">
        {/* Current user (only when auth is active) */}
        {authMode !== "none" && currentUser && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 font-medium truncate">{currentUser.username}</span>
            <button
              onClick={logout}
              className="ml-2 rounded p-0.5 text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
              title="Sign out"
            >
              <ArrowRightOnRectangleIcon className="h-4 w-4" />
            </button>
          </div>
        )}
        <button
          onClick={() => setShowAbout(true)}
          className="flex items-center gap-2 text-xs text-gray-500 hover:text-indigo-600 transition-colors"
        >
          <InformationCircleIcon className="h-4 w-4" />
          About MES AI
        </button>
      </div>
    </aside>
  );
}
