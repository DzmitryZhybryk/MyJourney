import type { ReactNode } from "react";
import { Navigate } from "react-router";

import { useAuth } from "../auth/useAuth";

interface PublicOnlyRouteProps {
  children: ReactNode;
}

/**
 * Mirror of `ProtectedRoute`: admits only UNauthenticated users and sends logged-in ones to the
 * dashboard. Used on all three public routes (`/`, `/login`, `/signup`), otherwise a logged-in
 * user opening `/login` via a bookmark or Back would get a login form inside an open session.
 *
 * While `isBootstrapping` it renders `null`, not a redirect: the session is still being restored
 * from the refresh cookie, so an early redirect either way would be a guess.
 */
export function PublicOnlyRoute({ children }: PublicOnlyRouteProps) {
  const { isAuthenticated, isBootstrapping } = useAuth();

  if (isBootstrapping) {
    return null;
  }

  if (isAuthenticated) {
    return <Navigate to="/home" replace />;
  }

  return <>{children}</>;
}
