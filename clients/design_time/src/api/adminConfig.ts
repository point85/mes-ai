/**
 * Admin Config API — read and write server .env settings.
 */

import api from "./client";
import type { ApiResponse } from "../types";

export interface ConfigEntry {
  key: string;
  value: string;
  label: string;
  description: string;
  type: "text" | "password" | "select" | "number";
  options: string[];
  masked: boolean;
  readonly: boolean;
}

export interface ConfigData {
  entries: ConfigEntry[];
}

export interface ConfigPatchResult {
  updated_keys: string[];
  restart_required: boolean;
}

export async function fetchConfig(): Promise<ConfigEntry[]> {
  const { data } = await api.get<ApiResponse<ConfigData>>("/admin/config");
  return data.data.entries;
}

export async function patchConfig(
  updates: Record<string, string>,
): Promise<ConfigPatchResult> {
  const { data } = await api.patch<ApiResponse<ConfigPatchResult>>(
    "/admin/config",
    { updates },
  );
  return data.data;
}
