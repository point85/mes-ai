/**
 * AUTH: React context providing auth state and operations to all DT-CLIENT components.
 *
 * authMode is read from GET /health so the rest of the app knows whether login is required.
 * When authMode === "none" all auth gates are skipped (dev convenience).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import axios from "axios";
import { login as apiLogin, getMe, type UserRead } from "../api/auth";
import { tokenStorage } from "../api/client";

interface AuthContextValue {
  /** "none" | "local" | "oidc" — loaded from /health on startup */
  authMode: string;
  isLoading: boolean;
  currentUser: UserRead | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  authMode: "none",
  isLoading: true,
  currentUser: null,
  login: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authMode, setAuthMode] = useState<string>("none");
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<UserRead | null>(null);

  useEffect(() => {
    async function init() {
      try {
        // Discover auth_mode from the server
        const { data } = await axios.get("/health");
        setAuthMode(data.auth_mode ?? "none");

        // If we already have a token, fetch the current user
        if (tokenStorage.getToken()) {
          try {
            const user = await getMe();
            setCurrentUser(user);
          } catch {
            // Token is invalid/expired — clear it; interceptor will redirect if needed
            tokenStorage.clear();
          }
        }
      } catch {
        // Server not reachable; fall back to none so UI is not completely blocked
        setAuthMode("none");
      } finally {
        setIsLoading(false);
      }
    }
    init();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const tokens = await apiLogin(username, password);
    tokenStorage.setTokens(tokens.access_token, tokens.refresh_token ?? "");
    const user = await getMe();
    setCurrentUser(user);
  }, []);

  const logout = useCallback(() => {
    tokenStorage.clear();
    setCurrentUser(null);
    window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider value={{ authMode, isLoading, currentUser, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
