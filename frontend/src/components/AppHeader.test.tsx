import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server, TEST_CURRENT_ACCOUNT, TEST_CURRENT_USER } from "../test/handlers";
import { findMenuItem, makeAuthValue, renderRoutes, renderWithProviders, screen } from "../test/render";
import { AppHeader } from "./AppHeader";

describe("AppHeader", () => {
  it("«Journeys» — ссылка на раздел, «Mind» (не реализован) — не ссылка с бейджем «Soon»", () => {
    // emailVerified: true, so there is no verification banner cluttering the DOM.
    renderWithProviders(<AppHeader />, {
      authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
    });

    expect(screen.getByRole("link", { name: "Journeys" })).toHaveAttribute("href", "/journeys");

    // "Mind" does not navigate: it renders not as a link (it leads nowhere) and is marked "Soon".
    expect(screen.queryByRole("link", { name: /Mind/u })).toBeNull();
    const mind = screen.getByText("Mind");
    expect(mind).toHaveAttribute("aria-disabled", "true");
    expect(mind).toHaveTextContent("Soon");
  });

  it("на активном разделе таб подсвечен и помечен aria-current", () => {
    renderWithProviders(<AppHeader />, {
      route: "/journeys",
      authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
    });

    const tab = screen.getByRole("link", { name: "Journeys" });
    expect(tab).toHaveClass("app-tab--active");
    expect(tab).toHaveAttribute("aria-current", "page");
  });

  it("в бургер-Drawer активный раздел тоже подсвечен", async () => {
    const { user } = renderWithProviders(<AppHeader />, {
      route: "/journeys",
      authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
    });

    // The burger shows on narrow screens (always rendered in jsdom) and opens the side menu.
    await user.click(screen.getByRole("button", { name: "Primary sections" }));

    // In the Drawer is the same "Journeys" link, now active (the desktop tab is present too).
    const links = await screen.findAllByRole("link", { name: "Journeys" });
    const drawerLink = links.find((link) => link.className.includes("app-drawer-link"));
    expect(drawerLink).toHaveClass("app-drawer-link--active");
    expect(drawerLink).toHaveAttribute("aria-current", "page");
  });

  it("меню профиля подписано именем и email текущего пользователя", async () => {
    const { user } = renderWithProviders(<AppHeader />, {
      authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
    });

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));

    expect(await screen.findByText(TEST_CURRENT_USER.displayName)).toBeInTheDocument();
    expect(await screen.findByText(TEST_CURRENT_ACCOUNT.email)).toBeInTheDocument();
  });

  it("пока профиль не загрузился, меню подписано «Account»", async () => {
    server.use(http.get("/v1/users/me/", () => HttpResponse.json({ code: "temporary", message: "" }, { status: 503 })));
    const { user } = renderWithProviders(<AppHeader />, {
      authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
    });

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));

    expect(await screen.findByText("Account")).toBeInTheDocument();
  });

  it("пункт «Profile» ведёт на страницу профиля", async () => {
    const { user } = renderRoutes({
      element: <AppHeader />,
      path: "/home",
      landings: [{ path: "/profile", label: "profile-landing" }],
      authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
    });

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.click(await findMenuItem("Profile"));

    expect(await screen.findByText("profile-landing")).toBeInTheDocument();
  });
});
