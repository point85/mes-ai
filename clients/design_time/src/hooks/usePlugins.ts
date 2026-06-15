/**
 * TanStack Query hooks for Plugin Management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPlugins,
  fetchPlugin,
  installPlugin,
  uninstallPlugin,
  enablePlugin,
  disablePlugin,
  updatePluginConfig,
  fetchAdapterCatalog,
  fetchKafkaBridgeStatus,
  prepareKafkaBridge,
  kafkaTestConnection,
} from "../api/plugins";
import type { PluginInstallRequest, PluginConfigUpdate } from "../types";

const KEYS = {
  plugins: ["plugins"] as const,
  pluginDetail: (id: string) => ["plugins", id] as const,
  catalog: ["plugins", "catalog"] as const,
};

// ─── Plugin list ──────────────────────────────────────────────────────

/** Poll every 10 s so the status column stays in sync with server state. */
const PLUGIN_POLL_INTERVAL = 10_000;

export function usePlugins() {
  return useQuery({
    queryKey: KEYS.plugins,
    queryFn: fetchPlugins,
    refetchInterval: PLUGIN_POLL_INTERVAL,
  });
}

export function usePlugin(pluginId: string) {
  return useQuery({
    queryKey: KEYS.pluginDetail(pluginId),
    queryFn: () => fetchPlugin(pluginId),
    enabled: !!pluginId,
    refetchInterval: PLUGIN_POLL_INTERVAL,
  });
}

// ─── Plugin lifecycle mutations ───────────────────────────────────────

export function useInstallPlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      pluginId,
      ...body
    }: PluginInstallRequest & { pluginId: string }) =>
      installPlugin(pluginId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.plugins }),
  });
}

export function useUninstallPlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pluginId: string) => uninstallPlugin(pluginId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.plugins }),
  });
}

export function useEnablePlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pluginId: string) => enablePlugin(pluginId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.plugins }),
  });
}

export function useDisablePlugin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pluginId: string) => disablePlugin(pluginId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.plugins }),
  });
}

// ─── Config mutation ──────────────────────────────────────────────────

export function useUpdatePluginConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      pluginId,
      ...body
    }: PluginConfigUpdate & { pluginId: string }) =>
      updatePluginConfig(pluginId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.plugins }),
  });
}

// ─── Adapter catalog ──────────────────────────────────────────────────

export function useAdapterCatalog() {
  return useQuery({ queryKey: KEYS.catalog, queryFn: fetchAdapterCatalog });
}
// ─── Kafka Java Bridge ────────────────────────────────────────────────────

export function useKafkaBridgeStatus() {
  return useQuery({
    queryKey: ["kafka-bridge-status"] as const,
    queryFn: fetchKafkaBridgeStatus,
    refetchInterval: 15_000,
  });
}

export function usePrepareKafkaBridge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ force = false }: { force?: boolean } = {}) => prepareKafkaBridge(force),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kafka-bridge-status"] }),
  });
}

export function useKafkaTestConnection() {
  return useMutation({ mutationFn: kafkaTestConnection });
}