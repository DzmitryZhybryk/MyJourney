import type { ReactNode } from "react";
import { Navigate } from "react-router";

import { useIsAdmin } from "../auth/roles";
import { ProtectedRoute } from "../components/ProtectedRoute";

interface AdminRouteProps {
  children: ReactNode;
}

/** A signed-in route for admins only; anyone else goes to the dashboard. */
export function AdminRoute({ children }: AdminRouteProps) {
  return (
    <ProtectedRoute>
      <AdminGate>{children}</AdminGate>
    </ProtectedRoute>
  );
}

function AdminGate({ children }: AdminRouteProps) {
  const isAdmin = useIsAdmin();

  if (!isAdmin) {
    return <Navigate to="/home" replace />;
  }

  return <>{children}</>;
}
