import { describe, expect, it } from "vitest";

import { renderWithProviders, screen } from "../../test/render";
import { JourneysLegendCard } from "./JourneysLegendCard";
import { isLegendCollapsed } from "./legendStorage";

describe("JourneysLegendCard", () => {
  it("по умолчанию легенда развёрнута: виден список и кнопка aria-expanded", () => {
    renderWithProviders(<JourneysLegendCard />);

    expect(screen.getByRole("button", { name: "Map legend" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByText("Visited")).toBeInTheDocument();
  });

  it("клик по заголовку сворачивает легенду и запоминает выбор", async () => {
    const { user } = renderWithProviders(<JourneysLegendCard />);

    await user.click(screen.getByRole("button", { name: "Map legend" }));

    expect(screen.getByRole("button", { name: "Map legend" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.queryByText("Visited")).toBeNull();
    expect(isLegendCollapsed()).toBe(true);
  });

  it("повторный клик разворачивает легенду обратно", async () => {
    const { user } = renderWithProviders(<JourneysLegendCard />);

    await user.click(screen.getByRole("button", { name: "Map legend" }));
    await user.click(screen.getByRole("button", { name: "Map legend" }));

    expect(screen.getByRole("button", { name: "Map legend" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByText("Visited")).toBeInTheDocument();
    expect(isLegendCollapsed()).toBe(false);
  });

  it("стартует свёрнутой, если пользователь сворачивал легенду ранее (localStorage)", () => {
    // Set the flag directly so the initial-state test does not depend on setLegendCollapsed.
    localStorage.setItem("journeys-legend-collapsed", "1");
    renderWithProviders(<JourneysLegendCard />);

    expect(screen.getByRole("button", { name: "Map legend" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.queryByText("Visited")).toBeNull();
  });
});
