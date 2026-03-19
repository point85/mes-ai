/**
 * Plugin Management API — thin wrappers around axios calls.
 */

import api from "./client";
import type {
  PluginSummary,
  PluginDetail,
  PluginConfigUpdate,
  AdapterInfo,
  ApiResponse,
  ApiListResponse,
} from "../types";

// ─── Plugins ──────────────────────────────────────────────────────────

export async function fetchPlugins(): Promise<ApiListResponse<PluginSummary>> {
  const { data } = await api.get<ApiListResponse<PluginSummary>>("/plugins");
  return data;
}

export async function fetchPlugin(pluginId: string): Promise<PluginDetail> {
  const { data } = await api.get<ApiResponse<PluginDetail>>(
    `/plugins/${encodeURIComponent(pluginId)}`,
  );
  return data.data;
}

export async function updatePluginConfig(
  pluginId: string,
  body: PluginConfigUpdate,
): Promise<Record<string, unknown>> {
  const { data } = await api.put<ApiResponse<Record<string, unknown>>>(
    `/plugins/${encodeURIComponent(pluginId)}/config`,
    body,
  );
  return data.data;
}

export async function enablePlugin(pluginId: string): Promise<Record<string, unknown>> {
  const { data } = await api.post<ApiResponse<Record<string, unknown>>>(
    `/plugins/${encodeURIComponent(pluginId)}/enable`,
  );
  return data.data;
}

export async function disablePlugin(pluginId: string): Promise<Record<string, unknown>> {
  const { data } = await api.post<ApiResponse<Record<string, unknown>>>(
    `/plugins/${encodeURIComponent(pluginId)}/disable`,
  );
  return data.data;
}

// ─── Adapter Catalog ──────────────────────────────────────────────────

export async function fetchAdapterCatalog(): Promise<ApiListResponse<AdapterInfo>> {
  const { data } = await api.get<ApiListResponse<AdapterInfo>>("/plugins/catalog");
  return data;
}
