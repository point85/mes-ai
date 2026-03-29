import { useEffect, useState } from "react";
import api from "../api/client";
import { fetchStateModels } from "../api/endpoints";
import type { StateModel } from "../types";

export default function DashboardPage() {
  const [health, setHealth] = useState<"ok" | "error" | null>(null);
  const [models, setModels] = useState<StateModel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await api.get("/health");
        if (!cancelled) setHealth(res.status === 200 ? "ok" : "error");
      } catch {
        if (!cancelled) setHealth("error");
      }

      try {
        const m = await fetchStateModels();
        if (!cancelled) setModels(m);
      } catch {
        /* no models yet */
      }

      if (!cancelled) setLoading(false);
    }

    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <p className="text-gray-500">Loading…</p>;
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Server health */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-sm font-semibold text-gray-600 uppercase mb-2">MES Server</h2>
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-3 h-3 rounded-full ${
              health === "ok" ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-sm">
            {health === "ok" ? "Connected" : "Unreachable"}
          </span>
        </div>
      </div>

      {/* Registered state models */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-sm font-semibold text-gray-600 uppercase mb-2">
          Registered State Models
        </h2>
        {models.length === 0 ? (
          <p className="text-sm text-gray-500">
            No state models registered. Enable the PackML or SEMI E10 plugin.
          </p>
        ) : (
          <ul className="space-y-1 text-sm">
            {models.map((m) => (
              <li key={m.id} className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
                <span className="font-medium">{m.name}</span>
                <span className="text-gray-400">
                  ({m.states.length} states, {m.transitions.length} transitions)
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
