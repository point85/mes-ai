/**
 * Dashboard — landing page for the DT-CLIENT.
 */

import { Link } from "react-router-dom";

const cards = [
  {
    title: "Units of Measure",
    to: "/uom",
    description:
      "Define SI, imperial, and custom packaging units with conversion factors.",
  },
  {
    title: "Sites & Plant Model",
    to: "/sites",
    description:
      "Configure sites, areas, production lines, work cells, and equipment.",
  },
  {
    title: "Products & Routes",
    to: "/products",
    description:
      "Manage product definitions, BOMs, process routes, and step parameters.",
  },
  {
    title: "Materials",
    to: "/materials",
    description:
      "Define raw, intermediate, and finished materials with shelf-life tracking.",
  },
  {
    title: "Data Definitions",
    to: "/data-definitions",
    description:
      "Set up data collection points — numeric, string, boolean, or enum values.",
  },
  {
    title: "Production Orders",
    to: "/orders",
    description:
      "Create and manage production orders through release, execution, and close.",
  },
  {
    title: "Quality Management",
    to: "/quality-tests",
    description:
      "Configure quality tests and manage non-conformances with disposition tracking.",
  },
  {
    title: "Performance Analysis",
    to: "/performance",
    description:
      "Track equipment state changes, production counters, and OEE metrics.",
  },
  {
    title: "Reason Codes",
    to: "/reasons",
    description:
      "Define hierarchical loss and downtime reason codes for OEE availability tracking.",
  },
  {
    title: "Genealogy / Traceability",
    to: "/genealogy",
    description:
      "Look up full traceability records — steps, materials, tests, and data points.",
  },
  {
    title: "Dispatch",
    to: "/dispatch",
    description:
      "Evaluate dispatch strategies, assign work, and monitor the dispatch queue.",
  },
];

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      <p className="mt-2 text-sm text-gray-500">
        Welcome to the MES AI configuration console. Use the sidebar to navigate
        to editors for units of measure, plant model, products, and more.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <Link
            key={c.to}
            to={c.to}
            className="block rounded-lg border border-gray-200 p-5 shadow-sm hover:border-indigo-300 hover:shadow-md transition-all"
          >
            <h2 className="text-base font-semibold text-gray-800">
              {c.title}
            </h2>
            <p className="mt-1 text-sm text-gray-500">{c.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
