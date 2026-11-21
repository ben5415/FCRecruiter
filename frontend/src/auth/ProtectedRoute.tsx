import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "./AuthContext";

export function ProtectedRoute({ managerOnly = false }: { managerOnly?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-message">Checking session…</div>;
  if (!user) return <Navigate replace to="/login" />;
  if (managerOnly && user.role !== "manager") return <Navigate replace to="/squad" />;
  return <Outlet />;
}
