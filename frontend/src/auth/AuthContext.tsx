import { useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { ensureRefreshed } from "../api/client";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { on as onAuthEvent } from "./events";
import { decodeAccessTokenClaims, type AccessTokenClaims } from "./jwt";
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken as writeAccessToken,
  subscribeAccessToken,
} from "./tokenStore";
import { AuthContext, type AuthContextValue } from "./useAuth";
import { resetVerifyBannerDismissed } from "./verifyBannerStorage";

// The provider sits at the root but the dialog is opened rarely, and only when logged in. A static
// import would pull Modal, PinInput and scroll lock into every page load, landing included.
const VerifyEmailDialog = lazy(() =>
  import("./VerifyEmailDialog").then((m) => ({ default: m.VerifyEmailDialog })),
);

// The dialog is absent until first opened; after that it stays mounted so closing can finish
// its animation and reopening does not wait for a load.
type VerifyDialogState = "never-opened" | "open" | "closed";

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const queryClient = useQueryClient();
  const [accessToken, setAccessTokenState] = useState<string | null>(() => getAccessToken());
  const [isBootstrapping, setIsBootstrapping] = useState<boolean>(() => getAccessToken() === null);
  const [verifyDialog, setVerifyDialog] = useState<VerifyDialogState>("never-opened");
  const isAuthenticated = accessToken !== null;

  useEffect(() => {
    return subscribeAccessToken((token) => setAccessTokenState(token));
  }, []);

  // The Query cache holds the previous session's data (profile, journeys map); without a reset
  // the next user in this tab would see it, and the globe background (`staleTime: Infinity`)
  // would never refetch. Clear on an auth-state CHANGE, not in a button handler: logout arrives
  // three ways (button, the transport's `auth-required` event, `users.user_deleted` on /me),
  // and their only common point is the token disappearing.
  useEffect(() => {
    if (!isAuthenticated) {
      queryClient.clear();
    }
  }, [isAuthenticated, queryClient]);

  useEffect(() => {
    if (!isBootstrapping) {
      return;
    }

    let cancelled = false;
    (async () => {
      // Go through single-flight `ensureRefreshed`, not a direct refresh(): the double effect run
      // under StrictMode would send two parallel /refresh/ calls and backend reuse detection
      // would kill the session. `ensureRefreshed` stores the token itself on success, and the
      // subscription updates state.
      const refreshed = await ensureRefreshed();
      if (cancelled) {
        return;
      }

      if (!refreshed) {
        clearAccessToken();
      }

      setIsBootstrapping(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [isBootstrapping]);

  useEffect(() => {
    const offAuth = onAuthEvent("auth-required", () => clearAccessToken());
    return () => {
      offAuth();
    };
  }, []);

  const claims = useMemo<AccessTokenClaims | null>(
    () => (accessToken !== null ? decodeAccessTokenClaims(accessToken) : null),
    [accessToken],
  );

  const setAccessToken = useCallback((token: string) => {
    // Login/signup starts a new session: reset the banner dismiss so the previous account's
    // dismiss does not leak into this tab (see verifyBannerStorage).
    resetVerifyBannerDismissed();
    writeAccessToken(token);
  }, []);
  const clearSession = useCallback(() => clearAccessToken(), []);
  const openVerifyDialog = useCallback(() => setVerifyDialog("open"), []);
  const closeVerifyDialog = useCallback(() => setVerifyDialog("closed"), []);

  const value: AuthContextValue = {
    accessToken,
    claims,
    isAuthenticated,
    isBootstrapping,
    emailVerified: claims?.email_verified ?? false,
    setAccessToken,
    clearSession,
    openVerifyDialog,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
      {/* If the dialog chunk fails to load, drop only the dialog, not the whole app. */}
      {verifyDialog !== "never-opened" && (
        <ErrorBoundary fallback={null}>
          <Suspense fallback={null}>
            <VerifyEmailDialog opened={verifyDialog === "open"} onClose={closeVerifyDialog} />
          </Suspense>
        </ErrorBoundary>
      )}
    </AuthContext.Provider>
  );
}
