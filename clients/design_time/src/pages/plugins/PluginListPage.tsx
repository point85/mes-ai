/**
 * Plugin List Page — shows all discovered plugins with status and controls.
 */

import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  PuzzlePieceIcon,
  PlayIcon,
  StopIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import { usePlugins, useEnablePlugin, useDisablePlugin } from "../../hooks/usePlugins";
import type { PluginSummary } from "../../types";

const STATUS_BADGE: Record<string, string> = {
  running: "bg-green-50 text-green-700",
  stopped: "bg-gray-100 text-gray-600",
  error: "bg-red-50 text-red-700",
  disabled: "bg-yellow-50 text-yellow-700",
};

function pluginStatus(p: PluginSummary): string {
  if (p.error) return "error";
  if (!p.enabled) return "disabled";
  if (p.is_running) return "running";
  return "stopped";
}

export default function PluginListPage() {
  const navigate = useNavigate();
  const { data, isLoading, error } = usePlugins();
  const enableMut = useEnablePlugin();
  const disableMut = useDisablePlugin();
  const [search, setSearch] = useState("");

  const plugins: PluginSummary[] = data?.data ?? [];

  const filtered = useMemo(() => {
    if (!search) return plugins;
    const q = search.toLowerCase();
    return plugins.filter(
      (p) =>
        p.id.toLowerCase().includes(q) ||
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q),
    );
  }, [plugins, search]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <PuzzlePieceIcon className="h-6 w-6 text-indigo-600" />
            Plugins
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage installed plugins, view status, and configure settings.
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search by name, ID, or description…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-72"
        />
        <span className="text-xs text-gray-400">
          {filtered.length} plugin{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / error */}
      {isLoading && <p className="text-sm text-gray-500">Loading plugins…</p>}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Failed to load plugins.
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Version</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Extensions</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((p) => {
                const status = pluginStatus(p);
                return (
                  <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5 text-sm font-mono font-medium text-gray-900">
                      {p.id}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-700">{p.name}</td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">{p.version}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {p.extension_points.map((ep) => (
                          <span
                            key={ep}
                            className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700"
                          >
                            {ep}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[status] ?? "bg-gray-100 text-gray-700"}`}
                      >
                        {status}
                      </span>
                      {p.error && (
                        <p className="text-xs text-red-500 mt-0.5 truncate max-w-[200px]" title={p.error}>
                          {p.error}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => navigate(`/plugins/${encodeURIComponent(p.id)}`)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                          title="Details"
                        >
                          <InformationCircleIcon className="h-4 w-4" />
                        </button>
                        {p.enabled ? (
                          <button
                            onClick={() => disableMut.mutate(p.id)}
                            className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                            title="Disable"
                            disabled={disableMut.isPending}
                          >
                            <StopIcon className="h-4 w-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => enableMut.mutate(p.id)}
                            className="rounded p-1 text-gray-400 hover:bg-green-50 hover:text-green-600 transition-colors"
                            title="Enable"
                            disabled={enableMut.isPending}
                          >
                            <PlayIcon className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                    No plugins found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
