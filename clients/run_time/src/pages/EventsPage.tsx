import { useState } from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import type { MESEvent } from "../types";

interface Props {
  events: MESEvent[];
  onClear?: () => void;
}

const EVENT_CATEGORIES = [
  { label: "All", prefix: "" },
  { label: "WIP", prefix: "wip." },
  { label: "Orders", prefix: "operations.request." },
  { label: "Quality", prefix: "quality." },
  { label: "Dispatch", prefix: "dispatch." },
  { label: "Data", prefix: "data." },
  { label: "Equipment", prefix: "equipment." },
];

export default function EventsPage({ events, onClear }: Props) {
  const [filter, setFilter] = useState("");

  const filtered = filter
    ? events.filter((e) => e.event_type.startsWith(filter))
    : events;
  const displayed = filtered.slice(-100).reverse();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Live Events</h2>
        {onClear && (
          <button onClick={onClear} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800">
            <ArrowPathIcon className="h-4 w-4" /> Clear
          </button>
        )}
      </div>

      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        {EVENT_CATEGORIES.map((cat) => (
          <button
            key={cat.prefix}
            onClick={() => setFilter(cat.prefix)}
            className={`px-3 py-1 text-sm rounded-full font-medium ${
              filter === cat.prefix
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow">
        {displayed.length === 0 ? (
          <p className="p-5 text-gray-400">No events received yet</p>
        ) : (
          <div className="max-h-[600px] overflow-y-auto divide-y">
            {displayed.map((e) => (
              <div key={e.event_id} className="px-4 py-2 hover:bg-gray-50">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-20 shrink-0 font-mono">
                    {new Date(e.timestamp).toLocaleTimeString()}
                  </span>
                  <EventTypeBadge type={e.event_type} />
                  <span className="text-xs text-gray-400">{e.source}</span>
                </div>
                <pre className="text-xs text-gray-500 mt-1 ml-[8.5rem] overflow-hidden text-ellipsis">
                  {JSON.stringify(e.payload)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400">
        Showing {displayed.length} of {filtered.length} events ({events.length} total received)
      </p>
    </div>
  );
}

function EventTypeBadge({ type }: { type: string }) {
  let color = "bg-gray-100 text-gray-700";
  if (type.startsWith("wip.")) color = "bg-blue-100 text-blue-700";
  else if (type.startsWith("operations.request.")) color = "bg-purple-100 text-purple-700";
  else if (type.startsWith("quality.")) color = "bg-green-100 text-green-700";
  else if (type.startsWith("dispatch.")) color = "bg-orange-100 text-orange-700";
  else if (type.startsWith("data.")) color = "bg-teal-100 text-teal-700";
  else if (type.startsWith("equipment.")) color = "bg-red-100 text-red-700";

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${color}`}>
      {type}
    </span>
  );
}
