import { describe, expect, it } from "vitest";

import { makeAuthValue, renderWithProviders, screen } from "../test/render";
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

  it("после загрузки профиля аватар показывает инициалы displayName", async () => {
    renderWithProviders(<AppHeader />, {
      authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
    });

    // Mantine Avatar renders the first two letters of a single-word name: "traveler" -> "TR".
    expect(await screen.findByText("TR")).toBeInTheDocument();
  });
});
