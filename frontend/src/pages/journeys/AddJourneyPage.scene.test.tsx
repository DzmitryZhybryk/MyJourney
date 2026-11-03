import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useGlobeScene } from "../../components/globe/globeScene";
import { pickCity, pickOption, submitMoscowToLondon } from "../../test/addJourney";
import { server } from "../../test/handlers";
import { renderWithProviders, screen } from "../../test/render";
import { AddJourneyPage } from "./AddJourneyPage";

/**
 * A probe of the scene channel: what `PersistentGlobeHost` reads in production. It stands OUTSIDE
 * the routes to survive leaving the page and show that the page cleaned up after itself.
 */
function SceneProbe() {
  const { route, slot } = useGlobeScene();
  return (
    <output
      data-testid="scene"
      data-origin={route?.origin?.name ?? "none"}
      data-destination={route?.destination?.name ?? "none"}
      data-transport={route?.transportType ?? "none"}
      data-slot={slot ? `${slot.left},${slot.top},${slot.width},${slot.height}` : "none"}
    />
  );
}

/** The form at /journeys/add with the scene probe beside it; submit navigates to /journeys. */
function renderWithSceneProbe() {
  return renderWithProviders(
    <>
      <Routes>
        <Route path="/journeys/add" element={<AddJourneyPage />} />
        <Route path="/journeys" element={<div>journeys-landing</div>} />
      </Routes>
      <SceneProbe />
    </>,
    { route: "/journeys/add" },
  );
}

describe("AddJourneyPage — сцена глобуса", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("публикует глобусу маршрут по мере заполнения формы", async () => {
    const { user } = renderWithSceneProbe();
    const scene = screen.getByTestId("scene");

    expect(scene).toHaveAttribute("data-origin", "none");

    await pickCity({ user, label: "From", query: "Mos", option: /Moscow/iu });
    await pickCity({ user, label: "To", query: "Lon", option: /London/iu });
    await pickOption({ user, trigger: screen.getByPlaceholderText("Choose transport"), option: "Air" });

    expect(scene).toHaveAttribute("data-origin", "Moscow");
    expect(scene).toHaveAttribute("data-destination", "London");
    expect(scene).toHaveAttribute("data-transport", "air");
  });

  it("публикует прямоугольник колонки глобуса во viewport-координатах", () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
      DOMRect.fromRect({ x: 700, y: 100, width: 300, height: 600 }),
    );

    renderWithSceneProbe();

    expect(screen.getByTestId("scene")).toHaveAttribute("data-slot", "700,100,300,600");
  });

  it("сдвиг от transform-анимации слоя страницы не попадает в прямоугольник колонки", () => {
    // The banner-close glide moves the page layer by `translateY`; the slot must be published where
    // the layout settles, not where the glide happens to be at that moment.
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
      DOMRect.fromRect({ x: 700, y: 166, width: 300, height: 600 }),
    );
    const computedStyle = window.getComputedStyle.bind(window);
    vi.spyOn(window, "getComputedStyle").mockImplementation((element, pseudo) =>
      element.classList.contains("add-journey")
        ? ({ transform: "matrix(1, 0, 0, 1, 0, 66)" } as CSSStyleDeclaration)
        : computedStyle(element, pseudo),
    );
    // jsdom has no DOMMatrix: a minimal one that reads the translation out of `matrix(a, b, c, d, e, f)`.
    vi.stubGlobal(
      "DOMMatrixReadOnly",
      class {
        m41: number;
        m42: number;

        constructor(transform: string) {
          const values = transform.replace(/^matrix\(|\)$/gu, "").split(",").map(Number);
          [this.m41, this.m42] = [values[4], values[5]];
        }
      },
    );

    renderWithSceneProbe();

    expect(screen.getByTestId("scene")).toHaveAttribute("data-slot", "700,100,300,600");
  });

  it("колонка нулевого размера (узкий экран, display:none) — места под глобус нет", () => {
    // jsdom does no layout: every element's rect is zero, exactly like a hidden column.
    renderWithSceneProbe();

    expect(screen.getByTestId("scene")).toHaveAttribute("data-slot", "none");
  });

  it("уход со страницы снимает маршрут и колонку — глобусу больше нечего показывать", async () => {
    server.use(http.post("/v1/journeys/", () => new HttpResponse(null, { status: 201 })));
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
      DOMRect.fromRect({ x: 700, y: 100, width: 300, height: 600 }),
    );
    const { user } = renderWithSceneProbe();

    await submitMoscowToLondon(user);

    expect(await screen.findByText("journeys-landing")).toBeInTheDocument();
    expect(screen.getByTestId("scene")).toHaveAttribute("data-origin", "none");
    expect(screen.getByTestId("scene")).toHaveAttribute("data-slot", "none");
  });
});
