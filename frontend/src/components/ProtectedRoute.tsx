import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const hasAccessToken = Boolean(localStorage.getItem("access_token"));

  // If not yet hydrated, don't show anything (App.tsx shows loading)
  if (!isHydrated) {
    return null;
  }

  return isAuthenticated || hasAccessToken ? <>{children}</> : <Navigate to="/login" replace />;
}