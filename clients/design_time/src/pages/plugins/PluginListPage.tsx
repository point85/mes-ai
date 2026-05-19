/**
 * Plugin List Page — Available vs. Installed tabs with lifecycle controls.
 */

import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  PuzzlePieceIcon,
  PlayIcon,
  StopIcon,
  InformationCircleIcon,
  ArrowDownTrayIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  usePlugins,
  useInstallPlugin,
  useUninstallPlugin,
  useEnablePlugin,
  useDisablePlugin,
} from "../../hooks/usePlugins";
import { formatApiError } from "../../api/errors";
import type { PluginSummary } from "../../types";

type Tab = "available" | "installed";

const STATUS_BADGE: Record<string, string> = {
  running: "bg-green-50 text-green-700",
  stopped: "bg-gray-100 text-gray-600",
  error: "bg-red-50 text-red-700",
  disabled: "bg-yellow-50 text-yellow-700",
  available: "bg-blue-50 text-blue-700",
};

function pluginStatus(p: PluginSummary): string {
  if (!p.installed) return "available";
  if (p.error) return "error";
  if (!p.enabled) return "disabled";
  if (p.is_running) return "running";
  return "stopped";
}

export default function PluginListPage() {
  const navigate = useNavigate();
  const { data, isLoading, error } = usePlugins();
  const installMut = useInstallPlugin();
  const uninstallMut = useUninstallPlugin();
  const enableMut = useEnablePlugin();
  const disableMut = useDisablePlugin();
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<Tab>("installed");

  const allPlugins: PluginSummary[] = data?.data ?? [];

  const { available, installed } = useMemo(() => {
    const a: PluginSummary[] = [];
    const i: PluginSummary[] = [];
    for (const p of allPlugins) {
      if (p.installed) i.push(p);
      else a.push(p);
    }
    return { available: a, installed: i };
  }, [allPlugins]);

  const list = tab === "installed" ? installed : available;

  const filtered = useMemo(() => {
    if (!search) return list;
    const q = search.toLowerCase();
    return list.filter(
      (p) =>
        p.id.toLowerCase().includes(q) ||
        p.name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        (p.category && p.category.toLowerCase().includes(q)),
    );
  }, [list, search]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <PuzzlePieceIcon className="h-6 w-6 text-indigo-600" />
          Plugins
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse available plugins, install, and manage their lifecycle.
        </p>
      </div>

      {/* Tabs + Search */}
      <div className="flex items-center gap-4">
        <div className="flex rounded-md border border-gray-300 overflow-hidden text-sm">
          <button
            onClick={() => setTab("installed")}
            className={`px-3 py-1.5 font-medium transition-colors ${
              tab === "installed"
                ? "bg-indigo-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            Installed ({installed.length})
          </button>
          <button
            onClick={() => setTab("available")}
            className={`px-3 py-1.5 font-medium transition-colors ${
              tab === "available"
                ? "bg-indigo-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            Available ({available.length})
          </button>
        </div>
        <input
          type="text"
          placeholder="Search by name, ID, or category…"
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

      {/* Mutation error banner */}
      {(enableMut.error || disableMut.error || installMut.error || uninstallMut.error) && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          <strong>
            {enableMut.error ? "Enable failed" : disableMut.error ? "Disable failed" : installMut.error ? "Install failed" : "Uninstall failed"}:
          </strong>{" "}
          {formatApiError(
            enableMut.error ?? disableMut.error ?? installMut.error ?? uninstallMut.error,
            "Request failed — see server log for details.",
          )}
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Version</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Origin</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Category</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((p) => {
                const status = pluginStatus(p);
                return (
                  <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5">
                      <div className="text-sm font-medium text-gray-900">{p.name}</div>
                      <div className="text-xs text-gray-400 font-mono">{p.id}</div>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">{p.version}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        p.origin === "system" ? "bg-purple-50 text-purple-700" : "bg-teal-50 text-teal-700"
                      }`}>
                        {p.origin}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-500">{p.category || "—"}</td>
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
                        {!p.installed ? (
                          <button
                            onClick={() =>
                              installMut.mutate({
                                pluginId: p.id,
                                parameter_values: {},
                              })
                            }
                            className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                            title="Install"
                            disabled={installMut.isPending}
                          >
                            <ArrowDownTrayIcon className="h-4 w-4" />
                          </button>
                        ) : (
                          <>
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
                            <button
                              onClick={() => uninstallMut.mutate(p.id)}
                              className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                              title="Uninstall"
                              disabled={uninstallMut.isPending}
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                    {tab === "available"
                      ? "All plugins are installed."
                      : "No installed plugins yet."}
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
