import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "./AuthContext";

export function ProtectedRoute({ adminOnly = false }: { adminOnly?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-message">Checking session…</div>;
  if (!user) return <Navigate replace to="/login" />;
  if (adminOnly && user.role !== "admin") return <Navigate replace to="/squad" />;
  return <Outlet />;
}
