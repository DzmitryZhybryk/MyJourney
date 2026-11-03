import { describe, expect, it } from "vitest";

import { renderWithProviders, screen } from "../test/render";
import { LandingPage } from "./LandingPage";

describe("LandingPage", () => {
  it("рендерит ровно один заголовок первого уровня", () => {
    renderWithProviders(<LandingPage />);

    // A structural page invariant: there is one h1, otherwise heading navigation breaks.
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("ведёт обе точки входа: на регистрацию и на вход", () => {
    renderWithProviders(<LandingPage />);

    const signup = screen.getAllByRole("link", { name: /start your map/iu });
    const login = screen.getAllByRole("link", { name: /log in/iu });

    expect(signup.length).toBeGreaterThan(0);
    expect(login.length).toBeGreaterThan(0);
    expect(signup[0]).toHaveAttribute("href", "/signup");
    expect(login[0]).toHaveAttribute("href", "/login");
  });

  it("разворачивает списки из i18n: фичи, шаги, статистика", () => {
    const { container } = renderWithProviders(<LandingPage />);

    // The three collections arrive as arrays from translations: check they reached the DOM and did
    // not collapse into nothing (which is how a broken key would fail without the guard).
    expect(container.querySelectorAll(".lp-card").length).toBeGreaterThan(0);
    expect(container.querySelectorAll(".lp-step").length).toBeGreaterThan(0);
    expect(container.querySelectorAll(".lp-stat").length).toBeGreaterThan(0);
  });

  it("шаги размечены упорядоченным списком, а не набором div", () => {
    const { container } = renderWithProviders(<LandingPage />);

    // "How it works" is a sequence, and its order must be visible to assistive technologies, not
    // only to the eye.
    const steps = container.querySelector("ol.lp-steps__list");
    expect(steps).not.toBeNull();
    expect(steps?.querySelectorAll("li").length).toBeGreaterThan(1);
  });

  it("цитата подана как blockquote с подписью", () => {
    const { container } = renderWithProviders(<LandingPage />);

    expect(container.querySelector("blockquote.lp-journal__quote")).not.toBeNull();
    expect(container.querySelector("figcaption.lp-journal__date")).not.toBeNull();
  });
});
