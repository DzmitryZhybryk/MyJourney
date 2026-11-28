import { fireEvent, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { MapCountry } from "../../../components/WorldMap";
import { WORLD_VIEW_BOX } from "../../../components/worldProjection";
import { renderJourneysTabs, type JourneysTab } from "../../../test/journeysMap";
import { stubScreenLayout } from "../../../test/layout";
import { preferReducedMotion } from "../../../test/motion";
import { act, screen, waitFor } from "../../../test/render";
import { MAP_TONE } from "../journeys-data";
import { useJourneysMapScene, useJourneysMapSceneActions, type JourneysMapScene } from "./journeysMapScene";
import { usePublishMapScene } from "./usePublishMapScene";

const VISITED: readonly MapCountry[] = [
  { id: "RU", status: "visited", cities: [{ id: "moscow", lat: 55.75, lng: 37.62, years: [2020] }] },
];

// Each tab's overlay leaves a mark, so a test sees whose layer is on the map.
const JOURNEYS_SCENE: JourneysMapScene = {
  tabId: "journeys",
  countries: VISITED,
  tone: MAP_TONE,
  overlay: () => <circle className="journeys-mark" />,
};
const MOVEMENTS_SCENE: JourneysMapScene = {
  tabId: "movements",
  countries: [],
  tone: MAP_TONE,
  isInteractive: false,
  overlay: () => <circle className="movements-mark" />,
};
const FEED_SCENE: JourneysMapScene = {
  tabId: "feed",
  countries: [],
  tone: MAP_TONE,
  isDecorative: true,
  isLandMuted: true,
};

function SceneTab({ scene }: { scene: JourneysMapScene | null }) {
  usePublishMapScene(scene);
  return null;
}

// The section's routes: two map tabs, the feed (here on a narrow screen, so without a map), and
// two screens that publish nothing.
const TABS: readonly JourneysTab[] = [
  { path: "/journeys", element: <SceneTab scene={JOURNEYS_SCENE} /> },
  { path: "/journeys/movements", element: <SceneTab scene={MOVEMENTS_SCENE} /> },
  { path: "/journeys/all", element: <SceneTab scene={null} /> },
  { path: "/journeys/wishlist", element: null },
  { path: "/journeys/add", element: null },
];

function mapWrap(container: HTMLElement): HTMLElement | null {
  return container.querySelector<HTMLElement>(".world-map-wrap");
}

async function findMap(container: HTMLElement): Promise<HTMLElement> {
  return waitFor(() => {
    const wrap = mapWrap(container);
    if (!wrap) throw new Error("Карта не отрисовалась");
    return wrap;
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("JourneysMapHost", () => {
  it("одна и та же карта переживает переход между вкладками и меняет слой", async () => {
    const { container, user } = renderJourneysTabs(TABS);
    const map = await findMap(container);
    expect(map.querySelector(".journeys-mark")).not.toBeNull();

    await user.click(screen.getByRole("link", { name: "/journeys/movements" }));

    await waitFor(() => expect(map.querySelector(".movements-mark")).not.toBeNull());
    expect(mapWrap(container)).toBe(map);
  });

  it("слой прошлой вкладки гаснет во время перелёта и уходит, новый проявляется", async () => {
    const { container, user } = renderJourneysTabs(TABS);
    const map = await findMap(container);

    await user.click(screen.getByRole("link", { name: "/journeys/movements" }));

    expect(map.querySelector(".world-map__leaving .journeys-mark")).not.toBeNull();
    expect(map.querySelector(".world-map__arriving .movements-mark")).not.toBeNull();
    await waitFor(() => expect(map.querySelector(".world-map__leaving")).toBeNull());
  });

  it("при «меньше движения» прошлый слой не задерживается", async () => {
    preferReducedMotion();
    const { container, user } = renderJourneysTabs(TABS);
    const map = await findMap(container);

    await user.click(screen.getByRole("link", { name: "/journeys/movements" }));

    expect(map.querySelector(".movements-mark")).not.toBeNull();
    expect(map.querySelector(".world-map__leaving")).toBeNull();
  });

  it.each(["/journeys/wishlist", "/journeys/add"])(
    "на %s карта гаснет, но остаётся той же; возврат показывает её сразу, без перелёта",
    async (path) => {
      const { container, user } = renderJourneysTabs(TABS);
      const map = await findMap(container);

      await user.click(screen.getByRole("link", { name: path }));

      expect(map).toHaveClass("journeys-map--hidden");
      expect(map).toHaveAttribute("aria-hidden", "true");

      await user.click(screen.getByRole("link", { name: "/journeys/movements" }));

      expect(mapWrap(container)).toBe(map);
      expect(map).not.toHaveClass("journeys-map--hidden");
      // Coming back is not a flight: no fading previous layer, no staged arrival.
      expect(map.querySelector(".world-map__leaving")).toBeNull();
      expect(map.querySelector(".world-map__arriving")).toBeNull();
      expect(map.querySelector(".movements-mark")).not.toBeNull();
    },
  );

  it("возврат на ту же вкладку после экрана без карты сбрасывает ручной зум", async () => {
    stubScreenLayout({
      "world-map": { left: 0, top: 0, width: 1000, height: 487 },
      "world-map-canvas": { left: 0, top: 0, width: 1000, height: 487 },
    });
    const { container, user } = renderJourneysTabs(TABS, "/journeys/movements");
    const map = await findMap(container);
    const canvas = map.querySelector<HTMLElement>(".world-map-canvas");
    if (!canvas) throw new Error("Область карты не найдена");
    const viewBoxWidth = () => Number(map.querySelector(".world-map")?.getAttribute("viewBox")?.split(" ")[2]);
    fireEvent.wheel(canvas, { ctrlKey: true, deltaY: -100 * Math.LN2, clientX: 250, clientY: 100 });
    expect(viewBoxWidth()).toBe(WORLD_VIEW_BOX.width / 2);

    await user.click(screen.getByRole("link", { name: "/journeys/wishlist" }));
    await user.click(screen.getByRole("link", { name: "/journeys/movements" }));

    await waitFor(() => expect(viewBoxWidth()).toBe(WORLD_VIEW_BOX.width));
  });

  it("вкладка без карты (лента на узком экране) прячет карту прошлой вкладки", async () => {
    const { container, user } = renderJourneysTabs(TABS);
    const map = await findMap(container);

    await user.click(screen.getByRole("link", { name: "/journeys/all" }));

    expect(map).toHaveClass("journeys-map--hidden");
  });

  it("возврат с ленты на узком экране — как с экрана без карты: без перелёта и со сброшенным зумом", async () => {
    stubScreenLayout({
      "world-map": { left: 0, top: 0, width: 1000, height: 487 },
      "world-map-canvas": { left: 0, top: 0, width: 1000, height: 487 },
    });
    const { container, user } = renderJourneysTabs(TABS, "/journeys/movements");
    const map = await findMap(container);
    const canvas = map.querySelector<HTMLElement>(".world-map-canvas");
    if (!canvas) throw new Error("Область карты не найдена");
    const viewBoxWidth = () => Number(map.querySelector(".world-map")?.getAttribute("viewBox")?.split(" ")[2]);
    fireEvent.wheel(canvas, { ctrlKey: true, deltaY: -100 * Math.LN2, clientX: 250, clientY: 100 });
    expect(viewBoxWidth()).toBe(WORLD_VIEW_BOX.width / 2);

    await user.click(screen.getByRole("link", { name: "/journeys/all" }));
    await user.click(screen.getByRole("link", { name: "/journeys" }));

    expect(map.querySelector(".journeys-mark")).not.toBeNull();
    expect(map.querySelector(".world-map__leaving")).toBeNull();
    expect(map.querySelector(".world-map__arriving")).toBeNull();
    await waitFor(() => expect(viewBoxWidth()).toBe(WORLD_VIEW_BOX.width));
  });

  it("открытие сразу экрана без карты карту не грузит вовсе", async () => {
    const { container } = renderJourneysTabs(TABS, "/journeys/add");
    await act(async () => {
      await import("./JourneysSharedMap");
    });

    expect(mapWrap(container)).toBeNull();
  });

  it("фоновая сцена: карта не ловит жесты, приглушена и скрыта от скринридера", async () => {
    const { container } = renderJourneysTabs([{ path: "/journeys/all", element: <SceneTab scene={FEED_SCENE} /> }]);
    const map = await findMap(container);

    expect(map).toHaveClass("journeys-map--background", "world-map-wrap--muted");
    expect(map).toHaveAttribute("aria-hidden", "true");
  });
});

describe("journeysMapScene", () => {
  it("хуки канала вне провайдера падают с понятной ошибкой", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => renderHook(() => useJourneysMapScene())).toThrow(/JourneysMapSceneProvider/u);
    expect(() => renderHook(() => useJourneysMapSceneActions())).toThrow(/JourneysMapSceneProvider/u);
  });
});
