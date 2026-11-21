import { useAuth } from "./useAuth";

const ADMIN_ROLE = "admin";

/**
 * Whether the current session belongs to an admin. UI only (the admin entry and its route guard):
 * the backend checks a permission on every admin request.
 */
export function useIsAdmin(): boolean {
  const { claims } = useAuth();
  return claims?.role === ADMIN_ROLE;
}
