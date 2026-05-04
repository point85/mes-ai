/**
 * AUTH: API functions for authentication and user/role management.
 * Login/refresh return TokenResponse directly (not wrapped in success_response).
 * All other endpoints return success_response({ data: ... }).
 */

import api from "./client";

// ── Types ──────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
}

export interface UserRead {
  id: string;
  username: string;
  email: string | null;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
  idp_issuer: string | null;
  roles: string[];
}

export interface RoleRead {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: string[];
}

// ── Auth endpoints ────────────────────────────────────────────────────────

export async function login(username: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/local/login", { username, password });
  return data;
}

export async function refreshAccessToken(refresh_token: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/local/refresh", { refresh_token });
  return data;
}

export async function getMe(): Promise<UserRead> {
  const { data } = await api.get<{ data: UserRead }>("/auth/me");
  return data.data;
}

// ── User CRUD ─────────────────────────────────────────────────────────────

export async function listUsers(): Promise<UserRead[]> {
  const { data } = await api.get<{ data: UserRead[] }>("/auth/users");
  return data.data;
}

export async function createUser(body: {
  username: string;
  email?: string;
  full_name?: string;
  password: string;
}): Promise<UserRead> {
  const { data } = await api.post<{ data: UserRead }>("/auth/users", body);
  return data.data;
}

export async function updateUser(
  id: string,
  body: { email?: string; full_name?: string; is_active?: boolean; password?: string },
): Promise<UserRead> {
  const { data } = await api.put<{ data: UserRead }>(`/auth/users/${id}`, body);
  return data.data;
}

export async function deleteUser(id: string): Promise<void> {
  await api.delete(`/auth/users/${id}`);
}

export async function assignRole(userId: string, roleId: string): Promise<void> {
  await api.post(`/auth/users/${userId}/roles/${roleId}`);
}

export async function removeRole(userId: string, roleId: string): Promise<void> {
  await api.delete(`/auth/users/${userId}/roles/${roleId}`);
}

// ── Role CRUD ─────────────────────────────────────────────────────────────

export async function listRoles(): Promise<RoleRead[]> {
  const { data } = await api.get<{ data: RoleRead[] }>("/auth/roles");
  return data.data;
}

export async function createRole(body: { name: string; description?: string }): Promise<RoleRead> {
  const { data } = await api.post<{ data: RoleRead }>("/auth/roles", body);
  return data.data;
}

export async function updateRolePermissions(
  roleId: string,
  add: string[],
  remove: string[],
): Promise<void> {
  await api.post(`/auth/roles/${roleId}/permissions`, { add, remove });
}

export async function deleteRole(roleId: string): Promise<void> {
  await api.delete(`/auth/roles/${roleId}`);
}
