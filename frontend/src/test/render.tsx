/**
 * Custom `render` with the app providers: the single entry point for all component tests.
 *
 * Sets up `MantineProvider` (app theme) + `MemoryRouter` (Link/Navigate/useNavigate need a Router
 * ancestor). Auth state comes by one of two paths:
 *  - `authValue`: a stub `AuthContext.Provider` with a controlled value (for components that need
 *    a fixed `{emailVerified, isAuthenticated...}` without the real bootstrap: HomePage,
 *    ProtectedRoute);
 *  - `withAuthProvider`: the real `<AuthProvider>` (for pages where the `setAccessToken` ->
 *    navigation flow itself is checked: LoginPage, SignUpPage).
 *
 * Navigation is observed "as a user": `renderRoutes` mounts the component at its path and adds
 * landing markers for target paths, so after `navigate("/")` the landing text appears in the DOM.
 * `useNavigate` is not mocked.
 */

import { useState, type ReactElement, type ReactNode } from "react";

import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider, type DefaultOptions } from "@tanstack/react-query";
import { render, screen, type RenderResult } from "@testing-library/react";
import userEvent, { type UserEvent } from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";

import { AuthProvider } from "../auth/AuthContext";
import { AuthContext, type AuthContextValue } from "../auth/useAuth";
import { GlobeSceneProvider } from "../components/globe/GlobeSceneProvider";
import { theme } from "../theme";
import { CurrentUserProvider } from "../user/CurrentUserContext";

/**
 * Query client for one test; with production defaults it would be a source of flakiness.
 *
 * `retry: false`, otherwise a "request failed" case would wait for three retries with backoff and
 * hit the timeout instead of showing the error. `refetchOnWindowFocus: false`: jsdom sends focus
 * during `userEvent`, and a background refetch would hit MSW after `server.resetHandlers()`. The
 * cache is fresh per render, so state does not leak between cases.
 */
export function createTestQueryClient(queries: DefaultOptions["queries"] = {}): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, ...queries },
    },
  });
}

type AuthOptions = {
  /** Stub context value; takes priority over `withAuthProvider`. */
  authValue?: AuthContextValue;
  /** Wrap in the real `<AuthProvider>` (if `authValue` is not set). */
  withAuthProvider?: boolean;
  /**
   * Own Query client instead of the default: when a test looks at the cache from outside the tree
   * (invalidation, clearing on logout) or changes the retry policy.
   */
  queryClient?: QueryClient;
};

type ProvidersProps = AuthOptions & {
  children: ReactNode;
  initialPath: string;
};

function Providers({ children, initialPath, authValue, withAuthProvider, queryClient }: ProvidersProps) {
  // The client is fixed at tree mount: a `rerender` in a test must not reset the cache with it.
  const [client] = useState(() => queryClient ?? createTestQueryClient());

  // The real CurrentUserProvider in both auth modes (an MSW handler for `/v1/users/me/` covers the
  // network); the default branch has none, since useAuth would throw without an Auth ancestor.
  let withAuth: ReactNode = children;
  if (authValue !== undefined) {
    withAuth = (
      <AuthContext.Provider value={authValue}>
        <CurrentUserProvider>{children}</CurrentUserProvider>
      </AuthContext.Provider>
    );
  } else if (withAuthProvider) {
    withAuth = (
      <AuthProvider>
        <CurrentUserProvider>{children}</CurrentUserProvider>
      </AuthProvider>
    );
  }

  return (
    // The scheme is "dark", as in `main.tsx`: tests must use the same scheme as production, or the
    // gate cannot see contrast bugs that exist only in the dark scheme.
    //
    // env="test" disables Mantine transitions and portals: the Menu/Modal dropdown mounts
    // synchronously on open, with no animation timers. Without it Menu flaps in jsdom, opening and
    // closing in the middle of an async userEvent chain, and `findAllByRole("menuitem")`
    // intermittently times out.
    <MantineProvider theme={theme} defaultColorScheme="dark" env="test">
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[initialPath]}>
          <GlobeSceneProvider>{withAuth}</GlobeSceneProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

type RenderOptions = AuthOptions & {
  /** Initial MemoryRouter path (default "/"). */
  route?: string;
};

/**
 * Renders arbitrary UI in the providers. Returns `user` (a ready `userEvent.setup()`) on top of
 * the standard `RenderResult`.
 */
export function renderWithProviders(
  ui: ReactElement,
  options: RenderOptions = {},
): RenderResult & { user: UserEvent } {
  const { route = "/", ...auth } = options;
  const result = render(ui, {
    wrapper: ({ children }) => (
      <Providers initialPath={route} {...auth}>
        {children}
      </Providers>
    ),
  });

  return { ...result, user: userEvent.setup() };
}

type Landing = {
  /** Path of the marker route (the navigation target). */
  path: string;
  /** Text the test uses to find the landing (`findByText`). */
  label: string;
};

type RenderRoutesOptions = AuthOptions & {
  /** The component under test and the path it is mounted at. */
  element: ReactElement;
  path: string;
  /** Initial path (default = `path`). */
  initialPath?: string;
  /** Markers for navigation target paths. */
  landings?: Landing[];
};

/**
 * Renders a component in `<Routes>` with landing markers, to check navigation by what the user
 * sees (not by spying on `useNavigate`).
 */
export function renderRoutes(
  options: RenderRoutesOptions,
): RenderResult & { user: UserEvent } {
  const { element, path, initialPath = path, landings = [], ...auth } = options;
  const result = render(
    <Routes>
      <Route path={path} element={element} />
      {landings.map((landing) => (
        <Route key={landing.path} path={landing.path} element={<div>{landing.label}</div>} />
      ))}
    </Routes>,
    {
      wrapper: ({ children }) => (
        <Providers initialPath={initialPath} {...auth}>
          {children}
        </Providers>
      ),
    },
  );

  return { ...result, user: userEvent.setup() };
}

/**
 * Builds a full `AuthContextValue` with default stub spies; a test overrides the fields it needs
 * (`emailVerified`, `isAuthenticated`, ...).
 */
export function makeAuthValue(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    accessToken: null,
    claims: null,
    isAuthenticated: false,
    isBootstrapping: false,
    emailVerified: false,
    setAccessToken: vi.fn(),
    clearSession: vi.fn(),
    openVerifyDialog: vi.fn(),
    ...overrides,
  };
}

/**
 * Returns a Mantine menu item by exact text. Grab all items with one `findAllByRole` and match by
 * `textContent`: more reliable and clearer than `findByRole("menuitem", { name })` for one item.
 * The dropdown renders synchronously thanks to `env="test"` on `MantineProvider` (see above).
 */
export async function findMenuItem(text: string): Promise<HTMLElement> {
  const items = await screen.findAllByRole("menuitem");
  const item = items.find((entry) => entry.textContent === text);
  if (item === undefined) {
    const present = items.map((entry) => entry.textContent).join(", ");
    throw new Error(`Пункт меню "${text}" не найден. Доступны: ${present}`);
  }

  return item;
}

export { act, waitFor, within } from "@testing-library/react";
export { screen, userEvent };
