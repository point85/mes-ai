import { useEffect, useState } from "react";
import { fetchStateModels } from "../api/endpoints";
import StateBadge from "../components/StateBadge";
import type { StateModel } from "../types";

export default function ModelsPage() {
  const [models, setModels] = useState<StateModel[]>([]);
  const [selected, setSelected] = useState<StateModel | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStateModels()
      .then((m) => {
        setModels(m);
        if (m.length > 0) setSelected(m[0]);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading…</p>;

  if (models.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No state models registered. Enable the PackML or SEMI E10 availability plugin.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Model selector tabs */}
      <div className="flex gap-2">
        {models.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelected(m)}
            className={`px-3 py-1.5 rounded text-sm font-medium border ${
              selected?.id === m.id
                ? "bg-emerald-600 text-white border-emerald-600"
                : "bg-white text-gray-700 hover:bg-gray-50"
            }`}
          >
            {m.name}
          </button>
        ))}
      </div>

      {selected && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Model info */}
          <div className="bg-white border rounded-lg p-4 space-y-3">
            <h2 className="text-sm font-semibold text-gray-600 uppercase">Model Info</h2>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-500 text-xs">Model ID</span>
                <p className="font-mono">{selected.model_id}</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs">Initial State</span>
                <p className="font-medium">{selected.initial_state}</p>
              </div>
            </div>
            {selected.description && (
              <p className="text-sm text-gray-600">{selected.description}</p>
            )}
          </div>

          {/* States table */}
          <div className="bg-white border rounded-lg p-4 space-y-3">
            <h2 className="text-sm font-semibold text-gray-600 uppercase">
              States ({selected.states.length})
            </h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">Dispatch</th>
                    <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">OEE Bucket</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {selected.states.map((s) => (
                    <tr key={s.name} className={s.name === selected.initial_state ? "bg-emerald-50" : ""}>
                      <td className="px-2 py-1 font-medium">
                        {s.display_name ?? s.name}
                        {s.name === selected.initial_state && (
                          <span className="ml-1 text-xs text-emerald-600">(initial)</span>
                        )}
                      </td>
                      <td className="px-2 py-1"><StateBadge category={s.dispatch_category} /></td>
                      <td className="px-2 py-1 text-xs">{s.oee_bucket}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Transitions table */}
          <div className="bg-white border rounded-lg p-4 space-y-3 lg:col-span-2">
            <h2 className="text-sm font-semibold text-gray-600 uppercase">
              Transitions ({selected.transitions.length})
            </h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">From</th>
                    <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">To</th>
                    <th className="px-2 py-1 text-left text-xs font-medium text-gray-500 uppercase">Trigger</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {selected.transitions.map((t, i) => (
                    <tr key={i}>
                      <td className="px-2 py-1 font-medium">{t.from_state}</td>
                      <td className="px-2 py-1">{t.to_state}</td>
                      <td className="px-2 py-1 text-gray-500">{t.trigger ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
