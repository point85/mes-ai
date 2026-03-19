/**
 * TanStack Query hooks for Plugin Management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPlugins,
  fetchPlugin,
  updatePluginConfig,
  enablePlugin,
  disablePlugin,
  fetchAdapterCatalog,
} from "../api/plugins";
import type { PluginConfigUpdate } from "../types";

const KEYS = {
  plugins: ["plugins"] as const,
  pluginDetail: (id: string) => ["plugins", id] as const,
  catalog: ["plugins", "catalog"] as const,
};

// ─── Plugin list ──────────────────────────────────────────────────────

export function usePlugins() {
  return useQuery({ queryKey: KEYS.plugins, queryFn: fetchPlugins });
}

export function usePlugin(pluginId: string) {
  return useQuery({
    queryKey: KEYS.pluginDetail(pluginId),
    queryFn: () => fetchPlugin(pluginId),
    enabled: !!pluginId,
  });
}

// ─── Plugin mutations ─────────────────────────────────────────────────

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

// ─── Adapter catalog ──────────────────────────────────────────────────

export function useAdapterCatalog() {
  return useQuery({ queryKey: KEYS.catalog, queryFn: fetchAdapterCatalog });
}
