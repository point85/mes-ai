/**
 * Plugin Detail Page — shows full plugin info, parameters, config editor, and lifecycle controls.
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeftIcon,
  PlayIcon,
  StopIcon,
  ArrowDownTrayIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import {
  usePlugin,
  useInstallPlugin,
  useUninstallPlugin,
  useUpdatePluginConfig,
  useEnablePlugin,
  useDisablePlugin,
} from "../../hooks/usePlugins";
import type { ParameterSchema } from "../../types";

export default function PluginDetailPage() {
  const { pluginId } = useParams<{ pluginId: string }>();
  const navigate = useNavigate();
  const { data: plugin, isLoading, error } = usePlugin(pluginId!);
  const installMut = useInstallPlugin();
  const uninstallMut = useUninstallPlugin();
  const updateConfigMut = useUpdatePluginConfig();
  const enableMut = useEnablePlugin();
  const disableMut = useDisablePlugin();

  // Parameter values for install form
  const [paramValues, setParamValues] = useState<Record<string, string>>({});

  // Config JSON editor
  const [configJson, setConfigJson] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

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

  function handleInstall() {
    if (!pluginId) return;
    installMut.mutate({ pluginId, parameter_values: paramValues });
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

  const status = !plugin.installed
    ? "available"
    : plugin.error
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
            {plugin.origin && (
              <>
                {" "}
                &middot;{" "}
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                  plugin.origin === "system" ? "bg-purple-50 text-purple-700" : "bg-teal-50 text-teal-700"
                }`}>
                  {plugin.origin}
                </span>
              </>
            )}
          </p>
        </div>
      </div>

      {/* Status + Lifecycle Controls */}
      <div className="flex items-center gap-3">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            status === "running"
              ? "bg-green-50 text-green-700"
              : status === "error"
                ? "bg-red-50 text-red-700"
                : status === "disabled"
                  ? "bg-yellow-50 text-yellow-700"
                  : status === "available"
                    ? "bg-blue-50 text-blue-700"
                    : "bg-gray-100 text-gray-600"
          }`}
        >
          {status}
        </span>

        {!plugin.installed ? (
          <button
            onClick={handleInstall}
            disabled={installMut.isPending}
            className="inline-flex items-center gap-1 rounded-md border border-indigo-300 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50 transition-colors"
          >
            <ArrowDownTrayIcon className="h-3.5 w-3.5" /> Install
          </button>
        ) : (
          <>
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
            <button
              onClick={() => uninstallMut.mutate(pluginId!)}
              disabled={uninstallMut.isPending}
              className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-red-50 hover:text-red-700 transition-colors"
            >
              <TrashIcon className="h-3.5 w-3.5" /> Uninstall
            </button>
          </>
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
        {plugin.comment && <InfoCard label="Comment" value={plugin.comment} />}
        <InfoCard label="Category" value={plugin.category || "—"} />
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

      {/* Parameters section (for install or view) */}
      {plugin.parameters.length > 0 && (
        <div className="rounded-lg border border-gray-200 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Plugin Parameters</h2>
          {!plugin.installed ? (
            // Editable form for pre-install
            <div className="space-y-2">
              {plugin.parameters.map((param: ParameterSchema) => (
                <div key={param.name} className="flex items-start gap-3">
                  <div className="w-40">
                    <label className="text-sm font-medium text-gray-700">
                      {param.name}
                      {param.required && <span className="text-red-500 ml-0.5">*</span>}
                    </label>
                    <p className="text-xs text-gray-400">{param.description}</p>
                  </div>
                  <input
                    type={param.secret ? "password" : "text"}
                    placeholder={param.default != null ? String(param.default) : ""}
                    value={paramValues[param.name] ?? ""}
                    onChange={(e) =>
                      setParamValues((prev) => ({ ...prev, [param.name]: e.target.value }))
                    }
                    className="flex-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              ))}
            </div>
          ) : (
            // Read-only view for installed plugins
            <div className="space-y-1">
              {plugin.parameters.map((param: ParameterSchema) => (
                <div key={param.name} className="flex items-baseline gap-2 text-sm">
                  <span className="font-medium text-gray-700 w-40">
                    {param.name}
                    {param.required && <span className="text-red-500 ml-0.5">*</span>}
                  </span>
                  <span className="text-gray-500">
                    {param.secret
                      ? "••••••"
                      : plugin.parameter_values[param.name] != null
                        ? String(plugin.parameter_values[param.name])
                        : param.default != null
                          ? String(param.default)
                          : "—"}
                  </span>
                  <span className="text-xs text-gray-400">({param.type})</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Config editor (only for installed plugins) */}
      {plugin.installed && (
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
      )}

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
