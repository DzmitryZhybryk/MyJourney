import type { QueryClient } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { act } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { emit } from "./events";
import { useAuth } from "./useAuth";
import { dismissVerifyBanner, isVerifyBannerDismissed } from "./verifyBannerStorage";
import { getJourneysMapQueryKey } from "../api/sdk";
import { makeAccessToken, server } from "../test/handlers";
import { createTestQueryClient, renderWithProviders, screen } from "../test/render";

/** Context probe: renders auth state as text plus a login button to observe from outside. */
function AuthProbe() {
  const { isBootstrapping, isAuthenticated, emailVerified, setAccessToken, openVerifyDialog } = useAuth();
  return (
    <div>
      <p>{`bootstrapping: ${isBootstrapping}`}</p>
      <p>{`authenticated: ${isAuthenticated}`}</p>
      <p>{`verified: ${emailVerified}`}</p>
      <button onClick={() => setAccessToken(makeAccessToken())}>sign in</button>
      <button onClick={openVerifyDialog}>open verification</button>
    </div>
  );
}

/** Renders the probe under the real `<AuthProvider>` (the bootstrap hits the MSW refresh). */
function renderAuth(queryClient?: QueryClient) {
  return renderWithProviders(<AuthProbe />, { withAuthProvider: true, queryClient });
}

/** Replaces the default 401 refresh with a successful one: the probe starts logged in. */
function withLiveSession(): void {
  server.use(
    http.post("/v1/auth/refresh/", () =>
      HttpResponse.json({ accessToken: makeAccessToken() }, { status: 200 }),
    ),
  );
}

describe("AuthProvider", () => {
  it("bootstrap без сессии (refresh 401) завершается неаутентифицированным", async () => {
    // The default refresh handler returns 401: no session.
    renderAuth();

    expect(await screen.findByText("bootstrapping: false")).toBeInTheDocument();
    expect(screen.getByText("authenticated: false")).toBeInTheDocument();
  });

  it("bootstrap восстанавливает сессию (refresh 200) — аутентифицирован, claims из токена", async () => {
    server.use(
      http.post("/v1/auth/refresh/", () =>
        HttpResponse.json(
          { accessToken: makeAccessToken({ email_verified: true }) },
          { status: 200 },
        ),
      ),
    );

    renderAuth();

    expect(await screen.findByText("authenticated: true")).toBeInTheDocument();
    expect(screen.getByText("verified: true")).toBeInTheDocument();
    expect(screen.getByText("bootstrapping: false")).toBeInTheDocument();
  });

  it("openVerifyDialog открывает диалог подтверждения email", async () => {
    const { user } = renderAuth();
    await screen.findByText("bootstrapping: false");

    await user.click(screen.getByRole("button", { name: "open verification" }));

    expect(await screen.findByRole("button", { name: "Send code" })).toBeInTheDocument();
  });

  it("диалог подтверждения email закрывается и открывается повторно", async () => {
    const { user } = renderAuth();
    await screen.findByText("bootstrapping: false");
    await user.click(screen.getByRole("button", { name: "open verification" }));
    await user.click(await screen.findByRole("button", { name: "Later" }));

    expect(screen.queryByRole("button", { name: "Send code" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "open verification" }));

    expect(await screen.findByRole("button", { name: "Send code" })).toBeInTheDocument();
  });

  it("событие auth-required сбрасывает сессию", async () => {
    withLiveSession();
    renderAuth();
    await screen.findByText("authenticated: true");

    act(() => emit("auth-required", undefined));

    expect(await screen.findByText("authenticated: false")).toBeInTheDocument();
  });

  it("недобровольный разлогин чистит кэш server-state — данные не достаются следующему входу", async () => {
    // Logout via a transport event, not the button: the cache must clear on a session state CHANGE,
    // otherwise the previous user's map and profile are visible to the next one, and the globe
    // background (`staleTime: Infinity`) would never refetch them.
    withLiveSession();
    const queryClient = createTestQueryClient();
    renderAuth(queryClient);
    await screen.findByText("authenticated: true");
    act(() => {
      queryClient.setQueryData(getJourneysMapQueryKey(), { countries: [] });
    });

    act(() => emit("auth-required", undefined));

    await screen.findByText("authenticated: false");
    expect(queryClient.getQueryData(getJourneysMapQueryKey())).toBeUndefined();
  });

  it("setAccessToken (вход) сбрасывает флаг скрытия verify-баннера", async () => {
    dismissVerifyBanner();
    expect(isVerifyBannerDismissed()).toBe(true);

    const { user } = renderAuth();
    await screen.findByText("bootstrapping: false");

    await user.click(screen.getByRole("button", { name: "sign in" }));

    expect(isVerifyBannerDismissed()).toBe(false);
  });
});
