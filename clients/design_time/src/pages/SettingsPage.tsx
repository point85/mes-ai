/**
 * SettingsPage — DT-CLIENT admin page for editing server environment configuration.
 *
 * Reads editable settings from GET /api/v1/admin/config and writes changes via
 * PATCH /api/v1/admin/config.  Secret fields are masked; Database URL is excluded
 * and must be set via the MES_DATABASE_URL environment variable.
 *
 * A restart-required banner is shown after a successful save.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchConfig, patchConfig, type ConfigEntry } from "../api/adminConfig";
import { formatApiError } from "../api/errors";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const [restartRequired, setRestartRequired] = useState(false);

  const { data: entries = [], isLoading, error } = useQuery({
    queryKey: ["admin-config"],
    queryFn: fetchConfig,
  });

  const mutation = useMutation({
    mutationFn: patchConfig,
    onSuccess: (result) => {
      setSaveError(null);
      setEdits({});
      setRestartRequired(result.restart_required);
      queryClient.invalidateQueries({ queryKey: ["admin-config"] });
    },
    onError: (err: unknown) => {
      setSaveError(formatApiError(err, "Save failed"));
    },
  });

  const handleChange = (key: string, value: string) => {
    setEdits((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    if (Object.keys(edits).length === 0) return;
    setSaveError(null);
    mutation.mutate(edits);
  };

  const getValue = (entry: ConfigEntry) =>
    edits[entry.key] !== undefined ? edits[entry.key] : entry.value;

  // Group entries by section prefix
  const sections: Record<string, ConfigEntry[]> = {};
  for (const entry of entries) {
    const section = entry.key.startsWith("MES_OIDC_")
      ? "OIDC Settings"
      : entry.key.startsWith("MES_LOG_")
      ? "Logging"
      : entry.key.startsWith("MES_PLUGIN_")
      ? "Plugins"
      : entry.key.startsWith("MES_EVENT_BUS") || entry.key === "MES_REDIS_URL"
      ? "Event Bus"
      : "Authentication";
    (sections[section] ??= []).push(entry);
  }

  const sectionOrder = [
    "Authentication",
    "OIDC Settings",
    "Event Bus",
    "Plugins",
    "Logging",
  ];

  const hasEdits = Object.keys(edits).length > 0;

  if (isLoading) {
    return (
      <div className="p-6 text-sm text-gray-500">Loading configuration…</div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-sm text-red-600">
        {formatApiError(error, "Failed to load configuration")}
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">Server Settings</h1>
      <p className="mt-1 text-sm text-gray-500">
        Edit server configuration. Changes are written to the{" "}
        <code className="rounded bg-gray-100 px-1 text-xs">.env</code> file and
        take effect after a server restart.{" "}
        <span className="font-medium text-gray-700">
          MES_DATABASE_URL is excluded — set it directly in the environment.
        </span>
      </p>

      {restartRequired && (
        <div className="mt-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          <span className="font-semibold">Restart required.</span> Settings
          saved to <code className="rounded bg-amber-100 px-1 text-xs">.env</code>.
          Restart the MES server for changes to take effect.
        </div>
      )}

      {saveError && (
        <div className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {saveError}
        </div>
      )}

      <div className="mt-6 space-y-8">
        {sectionOrder.map((sectionName) => {
          const sectionEntries = sections[sectionName];
          if (!sectionEntries?.length) return null;
          return (
            <section key={sectionName}>
              <h2 className="mb-3 text-base font-semibold text-gray-800 border-b border-gray-200 pb-1">
                {sectionName}
              </h2>
              <div className="space-y-4">
                {sectionEntries.map((entry) => (
                  <div key={entry.key}>
                    <label className="block text-sm font-medium text-gray-700">
                      {entry.label}
                      <span className="ml-2 font-mono text-xs text-gray-400">
                        {entry.key}
                      </span>
                    </label>
                    <p className="mt-0.5 text-xs text-gray-500">
                      {entry.description}
                    </p>
                    <div className="mt-1">
                      {entry.type === "select" ? (
                        <select
                          value={getValue(entry)}
                          onChange={(e) =>
                            handleChange(entry.key, e.target.value)
                          }
                          className="block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        >
                          {entry.options.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={entry.type === "password" ? "password" : entry.type === "number" ? "number" : "text"}
                          value={getValue(entry)}
                          onChange={(e) =>
                            handleChange(entry.key, e.target.value)
                          }
                          placeholder={entry.masked ? "leave blank to keep current" : ""}
                          className="block w-full rounded border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          );
        })}
      </div>

      <div className="mt-8 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={!hasEdits || mutation.isPending}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {mutation.isPending ? "Saving…" : "Save Changes"}
        </button>
        {hasEdits && (
          <button
            onClick={() => setEdits({})}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Discard
          </button>
        )}
      </div>
    </div>
  );
}
