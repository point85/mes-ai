/**
 * AUTH GUARD — wraps protected routes.
 * When authMode === "none", passes straight through (dev convenience).
 * When authMode === "local" | "oidc", requires a valid access token;
 * redirects to /login if absent.
 */

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function AuthGuard() {
  const { authMode, isLoading, currentUser } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-gray-500">Loading…</p>
      </div>
    );
  }

  // Auth disabled — allow everything
  if (authMode === "none") return <Outlet />;

  // Auth enabled — require a logged-in user
  if (!currentUser) return <Navigate to="/login" replace />;

  return <Outlet />;
}
