/**
 * Plugin Detail Page — shows full plugin info, config editor, and controls.
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeftIcon,
  PlayIcon,
  StopIcon,
} from "@heroicons/react/24/outline";
import {
  usePlugin,
  useUpdatePluginConfig,
  useEnablePlugin,
  useDisablePlugin,
} from "../../hooks/usePlugins";

export default function PluginDetailPage() {
  const { pluginId } = useParams<{ pluginId: string }>();
  const navigate = useNavigate();
  const { data: plugin, isLoading, error } = usePlugin(pluginId!);
  const updateConfigMut = useUpdatePluginConfig();
  const enableMut = useEnablePlugin();
  const disableMut = useDisablePlugin();

  // Local state for config editing
  const [configJson, setConfigJson] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  // Initialize the config text area once data loads
  const configText =
    configJson ?? (plugin ? JSON.stringify(plugin.config_values, null, 2) : "{}");

  function handleSaveConfig() {
    if (!pluginId) return;
    try {
      const parsed = JSON.parse(configText);
      setConfigError(null);
      updateConfigMut.mutate(
        { pluginId, config_overrides: parsed },
        { onSuccess: () => setConfigJson(null) },
      );
    } catch {
      setConfigError("Invalid JSON");
    }
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500 p-6">Loading plugin…</p>;
  }
  if (error || !plugin) {
    return (
      <div className="p-6">
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          Plugin not found or failed to load.
        </div>
      </div>
    );
  }

  const status = plugin.error
    ? "error"
    : !plugin.enabled
      ? "disabled"
      : plugin.is_running
        ? "running"
        : "stopped";

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/plugins")}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{plugin.name}</h1>
          <p className="text-sm text-gray-500">
            {plugin.id} v{plugin.version}
            {plugin.author && <> &middot; {plugin.author}</>}
          </p>
        </div>
      </div>

      {/* Status + Controls */}
      <div className="flex items-center gap-3">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            status === "running"
              ? "bg-green-50 text-green-700"
              : status === "error"
                ? "bg-red-50 text-red-700"
                : status === "disabled"
                  ? "bg-yellow-50 text-yellow-700"
                  : "bg-gray-100 text-gray-600"
          }`}
        >
          {status}
        </span>
        {plugin.enabled ? (
          <button
            onClick={() => disableMut.mutate(pluginId!)}
            disabled={disableMut.isPending}
            className="inline-flex items-center gap-1 rounded-md border border-red-300 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-50 transition-colors"
          >
            <StopIcon className="h-3.5 w-3.5" /> Disable
          </button>
        ) : (
          <button
            onClick={() => enableMut.mutate(pluginId!)}
            disabled={enableMut.isPending}
            className="inline-flex items-center gap-1 rounded-md border border-green-300 px-2.5 py-1 text-xs font-medium text-green-700 hover:bg-green-50 transition-colors"
          >
            <PlayIcon className="h-3.5 w-3.5" /> Enable
          </button>
        )}
      </div>

      {plugin.error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          <strong>Error:</strong> {plugin.error}
        </div>
      )}

      {/* Info grid */}
      <div className="grid grid-cols-2 gap-4">
        <InfoCard label="Description" value={plugin.description || "—"} />
        <InfoCard label="Min MES Version" value={plugin.min_mes_version} />
        <InfoCard
          label="Extension Points"
          value={plugin.extension_points.join(", ") || "—"}
        />
        <InfoCard
          label="Event Subscriptions"
          value={plugin.event_subscriptions.join(", ") || "—"}
        />
        <InfoCard
          label="Dependencies"
          value={plugin.dependencies.join(", ") || "—"}
        />
        <InfoCard
          label="Required Permissions"
          value={plugin.required_core_permissions.join(", ") || "—"}
        />
      </div>

      {/* Config editor */}
      <div className="rounded-lg border border-gray-200 p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Configuration</h2>
        {plugin.config_schema?.properties ? (
          <div className="text-xs text-gray-400">
            Schema keys:{" "}
            {Object.keys(
              plugin.config_schema.properties as Record<string, unknown>,
            ).join(", ")}
          </div>
        ) : null}
        <textarea
          value={configText}
          onChange={(e) => {
            setConfigJson(e.target.value);
            setConfigError(null);
          }}
          rows={8}
          className="w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 font-mono text-sm text-gray-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
        {configError && (
          <p className="text-xs text-red-600">{configError}</p>
        )}
        <button
          onClick={handleSaveConfig}
          disabled={updateConfigMut.isPending}
          className="inline-flex items-center rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors disabled:opacity-50"
        >
          {updateConfigMut.isPending ? "Saving…" : "Save Configuration"}
        </button>
      </div>

      {/* Notes */}
      {plugin.notes && (
        <div className="rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-1">Admin Notes</h2>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{plugin.notes}</p>
        </div>
      )}

      {/* Permissions */}
      {plugin.permissions.length > 0 && (
        <div className="rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">
            Custom Permissions
          </h2>
          <ul className="text-sm text-gray-600 space-y-1">
            {plugin.permissions.map((perm) => (
              <li key={perm.id}>
                <code className="text-xs bg-gray-100 px-1 rounded">{perm.id}</code>
                {perm.description && (
                  <span className="text-gray-400 ml-2">— {perm.description}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
      <dt className="text-xs font-medium text-gray-400 uppercase tracking-wider">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-gray-700">{value}</dd>
    </div>
  );
}
