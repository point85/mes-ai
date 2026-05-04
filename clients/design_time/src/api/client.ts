/**
 * Axios instance configured for the MES API.
 * In dev, Vite proxies /api → http://localhost:8000.
 *
 * Interceptors:
 *  - Request: attaches Bearer token from localStorage if present
 *  - Response: on 401, attempts silent token refresh; redirects to /login on failure
 */

import axios from "axios";

const TOKEN_KEY = "mes_access_token";
const REFRESH_KEY = "mes_refresh_token";

export const tokenStorage = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  setTokens: (access: string, refresh: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor: attach Bearer token ──────────────────────────────
api.interceptors.request.use((config) => {
  const token = tokenStorage.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Response interceptor: silent refresh on 401 ───────────────────────────
let isRefreshing = false;
type QueueEntry = { resolve: (token: string) => void; reject: (err: unknown) => void };
let failedQueue: QueueEntry[] = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)));
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      });
    }

    original._retry = true;
    isRefreshing = true;

    const refreshToken = tokenStorage.getRefresh();
    if (!refreshToken) {
      isRefreshing = false;
      tokenStorage.clear();
      window.location.href = "/login";
      return Promise.reject(error);
    }

    try {
      // Use a plain axios call to avoid the interceptor loop
      const { data } = await axios.post("/api/v1/auth/local/refresh", {
        refresh_token: refreshToken,
      });
      const { access_token, refresh_token: newRefresh } = data;
      tokenStorage.setTokens(access_token, newRefresh ?? refreshToken);
      api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
      processQueue(null, access_token);
      original.headers.Authorization = `Bearer ${access_token}`;
      return api(original);
    } catch (refreshError) {
      processQueue(refreshError, null);
      tokenStorage.clear();
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default api;
