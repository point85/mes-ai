/**
 * Sidebar navigation for the DT-CLIENT.
 * Each section corresponds to a server module's CRUD editor.
 * New editors are added here as they're implemented.
 */

import { NavLink } from "react-router-dom";
import {
  ScaleIcon,
  CubeIcon,
  Cog6ToothIcon,
  BuildingOffice2Icon,
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
    ],
  },
  {
    title: "Admin",
    items: [
      { label: "Settings", to: "/settings", icon: Cog6ToothIcon },
    ],
  },
];

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
      {/* Logo / Title */}
      <div className="px-4 py-4 border-b border-gray-200">
        <h1 className="text-lg font-bold text-gray-800 tracking-tight">
          MES AI
        </h1>
        <p className="text-xs text-gray-500">Configuration</p>
      </div>

      {/* Nav sections */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        {sections.map((section) => (
          <div key={section.title}>
            <h2 className="px-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
              {section.title}
            </h2>
            <ul className="mt-1 space-y-0.5">
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
