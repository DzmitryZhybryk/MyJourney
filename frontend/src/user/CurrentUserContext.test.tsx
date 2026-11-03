import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { shouldRetry } from "../api/queryClient";
import { AuthContext, type AuthContextValue } from "../auth/useAuth";
import { server, TEST_CURRENT_USER } from "../test/handlers";
import { createTestQueryClient, makeAuthValue } from "../test/render";
import { CurrentUserProvider } from "./CurrentUserContext";
import { useCurrentUser } from "./useCurrentUser";

/** Probe: prints the state machine status (and the name for ready), without Mantine/Router. */
function Probe() {
  const state = useCurrentUser();
  return <span>{state.status === "ready" ? `ready:${state.user.displayName}` : state.status}</span>;
}

function tree(authValue: AuthContextValue, queryClient = createTestQueryClient()) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={authValue}>
        <CurrentUserProvider>
          <Probe />
        </CurrentUserProvider>
      </AuthContext.Provider>
    </QueryClientProvider>
  );
}

describe("CurrentUserProvider", () => {
  it("во время auth-bootstrap держит loading и не шлёт запрос", () => {
    render(tree(makeAuthValue({ isAuthenticated: false, isBootstrapping: true })));

    expect(screen.getByText("loading")).toBeInTheDocument();
  });

  it("без сессии переходит в anonymous", async () => {
    render(tree(makeAuthValue({ isAuthenticated: false })));

    expect(await screen.findByText("anonymous")).toBeInTheDocument();
  });

  it("после логина грузит /me и отдаёт ready с профилем", async () => {
    render(tree(makeAuthValue({ isAuthenticated: true })));

    expect(await screen.findByText("ready:traveler")).toBeInTheDocument();
  });

  it("ошибка /me переводит в error", async () => {
    server.use(
      http.get("/v1/users/me/", () =>
        HttpResponse.json({ code: "internal_error", message: "boom" }, { status: 500 }),
      ),
    );

    render(tree(makeAuthValue({ isAuthenticated: true })));

    expect(await screen.findByText("error")).toBeInTheDocument();
  });

  it("код users.user_deleted (410) разлогинивает вместо перехода в error", async () => {
    server.use(
      http.get("/v1/users/me/", () =>
        HttpResponse.json({ code: "users.user_deleted", message: "удалён" }, { status: 410 }),
      ),
    );
    const authValue = makeAuthValue({ isAuthenticated: true });

    render(tree(authValue));

    await waitFor(() => {
      expect(authValue.clearSession).toHaveBeenCalledOnce();
    });
    expect(screen.queryByText("error")).not.toBeInTheDocument();
  });

  it("код users.user_not_found (404) тоже разлогинивает", async () => {
    server.use(
      http.get("/v1/users/me/", () =>
        HttpResponse.json({ code: "users.user_not_found", message: "нет такого" }, { status: 404 }),
      ),
    );
    const authValue = makeAuthValue({ isAuthenticated: true });

    render(tree(authValue));

    await waitFor(() => {
      expect(authValue.clearSession).toHaveBeenCalledOnce();
    });
    expect(screen.queryByText("error")).not.toBeInTheDocument();
  });

  it("транзиентный сбой /me больше не терминален — боевая политика повторов доводит до ready", async () => {
    // Without retries the first failure left the profile in error forever; now a 5xx is retried.
    // A client with the real predicate (retryDelay: 0, no point waiting for backoff in a test).
    let attempts = 0;
    server.use(
      http.get("/v1/users/me/", () => {
        attempts += 1;
        return attempts === 1
          ? HttpResponse.json({ code: "internal_error", message: "boom" }, { status: 500 })
          : HttpResponse.json(TEST_CURRENT_USER);
      }),
    );

    render(tree(makeAuthValue({ isAuthenticated: true }), createTestQueryClient({ retry: shouldRetry, retryDelay: 0 })));

    expect(await screen.findByText("ready:traveler")).toBeInTheDocument();
    expect(attempts).toBe(2);
  });

  it("разлогинивающий код (410) не повторяется — бить по удалённому пользователю нечем", async () => {
    let attempts = 0;
    server.use(
      http.get("/v1/users/me/", () => {
        attempts += 1;
        return HttpResponse.json({ code: "users.user_deleted", message: "удалён" }, { status: 410 });
      }),
    );
    const authValue = makeAuthValue({ isAuthenticated: true });

    render(tree(authValue, createTestQueryClient({ retry: shouldRetry, retryDelay: 0 })));

    await waitFor(() => {
      expect(authValue.clearSession).toHaveBeenCalledOnce();
    });
    expect(attempts).toBe(1);
  });

  it("поздний ответ устаревшего запроса не затирает состояние после логаута", async () => {
    // The /me response is held manually: logout happens while the request is "in flight".
    let releaseProfile!: () => void;
    const gate = new Promise<void>((resolve) => {
      releaseProfile = resolve;
    });
    server.use(
      http.get("/v1/users/me/", async () => {
        await gate;
        return HttpResponse.json(TEST_CURRENT_USER);
      }),
    );

    // One client for both renders: a new one would reset the cache with the in-flight request and
    // there would be nothing to check.
    const queryClient = createTestQueryClient();
    const { rerender } = render(tree(makeAuthValue({ isAuthenticated: true }), queryClient));
    expect(screen.getByText("loading")).toBeInTheDocument();

    rerender(tree(makeAuthValue({ isAuthenticated: false }), queryClient));
    expect(await screen.findByText("anonymous")).toBeInTheDocument();

    releaseProfile();
    // Let the stale response arrive: the state must stay anonymous.
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.getByText("anonymous")).toBeInTheDocument();
    expect(screen.queryByText(/ready:/u)).not.toBeInTheDocument();
    expect(screen.queryByText("error")).not.toBeInTheDocument();
  });
});
