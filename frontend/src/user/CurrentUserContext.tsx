import { useQuery } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";

import { ApiError } from "../api/errors";
import { getCurrentUserOptions, type CurrentUserResponse } from "../api/sdk";
import { useAuth } from "../auth/useAuth";
import { CurrentUserContext, type CurrentUserState } from "./useCurrentUser";

// Codes meaning there is no live user: retrying is pointless and the session must be logged out.
// Branch on `code` (the stable API contract), not the HTTP status (a transport detail).
const SESSION_INVALID_CODES: ReadonlySet<string> = new Set(["users.user_deleted", "users.user_not_found"]);

function isSessionInvalid(error: unknown): boolean {
  return error instanceof ApiError && SESSION_INVALID_CODES.has(error.code);
}

interface CurrentUserProviderProps {
  children: ReactNode;
}

/**
 * Loads the profile (`/v1/users/me/`) and exposes it via context.
 *
 * Sits ABOVE `AuthProvider` and follows its state: `loading` until the auth bootstrap finishes
 * (no request, the token may not exist yet), `anonymous` without a session; login/logout flip
 * `isAuthenticated` and with it the query's `enabled`. Query retries transient failures itself,
 * so `error` here is a terminal outcome, not a first failure.
 */
export function CurrentUserProvider({ children }: CurrentUserProviderProps) {
  const { isAuthenticated, isBootstrapping, clearSession } = useAuth();
  const { data, error } = useQuery({
    ...getCurrentUserOptions(),
    enabled: !isBootstrapping && isAuthenticated,
  });

  // "The user is gone" means logout; the provider goes anonymous by itself once isAuthenticated drops.
  useEffect(() => {
    if (isSessionInvalid(error)) {
      clearSession();
    }
  }, [error, clearSession]);

  return (
    <CurrentUserContext.Provider value={toState({ isAuthenticated, isBootstrapping, data, error })}>
      {children}
    </CurrentUserContext.Provider>
  );
}

interface StateInput {
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  data: CurrentUserResponse | undefined;
  error: unknown;
}

/**
 * Folds auth state and the query outcome into the context's state machine.
 *
 * Auth beats data: a late response to a request sent before logout must not raise the profile
 * over `anonymous`. A logging-out error code holds `loading`: it is transient, `clearSession`
 * is already on its way and will move the provider to `anonymous`.
 */
function toState({ isAuthenticated, isBootstrapping, data, error }: StateInput): CurrentUserState {
  if (isBootstrapping) {
    return { status: "loading" };
  }

  if (!isAuthenticated) {
    return { status: "anonymous" };
  }

  if (data !== undefined) {
    return { status: "ready", user: data };
  }

  if (error !== null && error !== undefined) {
    return isSessionInvalid(error) ? { status: "loading" } : { status: "error" };
  }

  return { status: "loading" };
}
