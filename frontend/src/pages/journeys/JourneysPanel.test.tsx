import { describe, expect, it } from "vitest";

import { renderWithProviders, screen } from "../../test/render";
import { JourneysPanel } from "./JourneysPanel";

describe("JourneysPanel", () => {
  it("реализованные пункты — ссылки: «Journeys map», «Movements map», «All journeys» и «+ Add journey» ведут на свои маршруты", () => {
    renderWithProviders(<JourneysPanel />);

    expect(screen.getByRole("link", { name: "Journeys map" })).toHaveAttribute("href", "/journeys");
    expect(screen.getByRole("link", { name: "Movements map" })).toHaveAttribute(
      "href",
      "/journeys/movements",
    );
    expect(screen.getByRole("link", { name: "All journeys" })).toHaveAttribute("href", "/journeys/all");
    expect(screen.getByRole("link", { name: /Add journey/u })).toHaveAttribute(
      "href",
      "/journeys/add",
    );
  });

  it("нереализованный раздел «Wishlist» не навигирует: не ссылка, помечен «Soon», aria-disabled", () => {
    renderWithProviders(<JourneysPanel />);

    // The main invariant: the item is not a link, so it does not lead to an empty route.
    expect(screen.queryByRole("link", { name: /Wishlist/u })).toBeNull();
    const item = screen.getByText("Wishlist");
    expect(item).toHaveAttribute("aria-disabled", "true");
    expect(item).toHaveTextContent("Soon");
  });

  it("на маршруте /journeys/all подсвечивает «All journeys», «Journeys map» (end) не активен", () => {
    renderWithProviders(<JourneysPanel />, { route: "/journeys/all" });

    const active = screen.getByRole("link", { name: "All journeys" });
    expect(active).toHaveClass("journeys-nav__item--active");
    expect(active).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Journeys map" })).not.toHaveClass("journeys-nav__item--active");
  });

  it("«+ Add place» — отключённая кнопка с бейджем «Soon», не ссылка", () => {
    renderWithProviders(<JourneysPanel />);

    const addPlace = screen.getByRole("button", { name: /Add place/u });
    expect(addPlace).toBeDisabled();
    expect(addPlace).toHaveTextContent("Soon");
    expect(screen.queryByRole("link", { name: /Add place/u })).toBeNull();
  });

  it("на маршруте /journeys подсвечивает «Journeys map» активным (aria-current)", () => {
    renderWithProviders(<JourneysPanel />, { route: "/journeys" });

    const active = screen.getByRole("link", { name: "Journeys map" });
    expect(active).toHaveClass("journeys-nav__item--active");
    expect(active).toHaveAttribute("aria-current", "page");
  });

  it("на маршруте /journeys/add подсвечивает «+ Add journey», «Journeys map» (end) не активен", () => {
    renderWithProviders(<JourneysPanel />, { route: "/journeys/add" });

    const active = screen.getByRole("link", { name: /Add journey/u });
    expect(active).toHaveClass("journeys-nav__add--active");
    expect(active).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Journeys map" })).not.toHaveClass(
      "journeys-nav__item--active",
    );
  });
});
