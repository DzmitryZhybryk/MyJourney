import { createContext, useContext } from "react";

import type { CurrentUserResponse } from "../api/sdk";

/**
 * Current user profile state.
 *
 * `anonymous`: no session (public pages); `loading`: auth bootstrap or the `/me` request in
 * flight; `error`: the profile failed to load (the caller decides what to show); `ready`: loaded.
 */
export type CurrentUserState =
  | { status: "anonymous" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; user: CurrentUserResponse };

export const CurrentUserContext = createContext<CurrentUserState | null>(null);

export function useCurrentUser(): CurrentUserState {
  const ctx = useContext(CurrentUserContext);
  if (ctx === null) {
    throw new Error("useCurrentUser must be used within a <CurrentUserProvider>");
  }

  return ctx;
}
