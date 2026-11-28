import { fireEvent } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { stubScreenLayout, type ScreenRect } from "../test/layout";
import { preferReducedMotion } from "../test/motion";
import { renderWithProviders, screen, waitFor } from "../test/render";
import { countriesWithFill } from "../test/worldMap";
import type { MapCountry, WorldMapTone } from "./WorldMap";
import { WorldMap } from "./WorldMap";
import { WORLD_VIEW_BOX, type ViewBox } from "./worldProjection";

// Unique fills per status: a country's path is found unambiguously by fill (an SVG path has no
// role/name, it is graphics).
const TONE: WorldMapTone = {
  land: "#eeeeee",
  border: "#999999",
  visited: "#00cc44",
  wishlist: "#ffaa00",
  cityDot: "#ff3366",
};

const COUNTRIES: MapCountry[] = [
  {
    id: "RU",
    status: "visited",
    cities: [{ id: "moscow", name: "Moscow", lat: 55.75, lng: 37.62, years: [2019, 2021] }],
  },
  { id: "FR", status: "wishlist", cities: [] },
];

function pathByFill(container: HTMLElement, fill: string): SVGPathElement {
  const [path] = countriesWithFill(container, fill);
  if (!path) {
    throw new Error(`Страна с заливкой ${fill} не найдена`);
  }

  return path;
}

describe("WorldMap", () => {
  it("рисует страны по статусу и точки городов", () => {
    const { container } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} className="test-map" />,
    );

    // Visited and wishlist countries get their fills, the rest get land.
    expect(countriesWithFill(container, TONE.visited)).toHaveLength(1);
    expect(countriesWithFill(container, TONE.wishlist)).toHaveLength(1);
    expect(countriesWithFill(container, TONE.land).length).toBeGreaterThan(0);
    // A visited country's city is one dot.
    expect(container.querySelectorAll(".world-map__city-dot")).toHaveLength(1);
    // The map's accessible name and the external modifier class.
    expect(container.querySelector(".world-map")?.getAttribute("aria-label")).toBe(
      "World map highlighting visited countries",
    );
    expect(container.querySelector(".world-map-wrap.test-map")).not.toBeNull();
  });

  it("без className не добавляет модификатор-класс", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);

    expect(container.querySelector(".world-map-wrap")?.getAttribute("class")).toBe("world-map-wrap");
  });

  it("ховер посещённой страны показывает тултип с городами и годами", async () => {
    const { container, user } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} />,
    );

    await user.hover(pathByFill(container, TONE.visited));

    // The name resolves from the ISO code via CLDR (RU -> Russia), cities come with visit years.
    expect(await screen.findByText("Russia")).toBeInTheDocument();
    expect(screen.getByText("Moscow")).toBeInTheDocument();
    expect(screen.getByText("2019, 2021")).toBeInTheDocument();
  });

  it("в тултипе города идут по году первого визита, а в одном году — по названию", async () => {
    // Alphabet and years disagree: York and London are 2019, Bristol is 2021.
    const countries: MapCountry[] = [
      {
        id: "GB",
        status: "visited",
        cities: [
          { id: "bristol", name: "Bristol", lat: 51.45, lng: -2.58, years: [2021] },
          { id: "york", name: "York", lat: 53.96, lng: -1.08, years: [2019, 2022] },
          { id: "london", name: "London", lat: 51.5, lng: -0.12, years: [2019] },
        ],
      },
    ];
    const { container, user } = renderWithProviders(<WorldMap countries={countries} tone={TONE} />);

    await user.hover(pathByFill(container, TONE.visited));

    const cityNames = (await screen.findAllByText(/^(London|Bristol|York)$/u)).map((element) => element.textContent);
    expect(cityNames).toEqual(["London", "York", "Bristol"]);
  });

  it("пока названия городов грузятся, тултип показывает только страну", async () => {
    const countries: MapCountry[] = [
      { id: "RU", status: "visited", cities: [{ id: "moscow", lat: 55.75, lng: 37.62, years: [2019] }] },
    ];
    const { container, user } = renderWithProviders(<WorldMap countries={countries} tone={TONE} />);

    await user.hover(pathByFill(container, TONE.visited));

    expect(await screen.findByText("Russia")).toBeInTheDocument();
    // The country is visited, so "not visited yet" would be false here; there are no years without a city name either.
    expect(screen.queryByText("Not visited yet")).not.toBeInTheDocument();
    expect(screen.queryByText("2019")).not.toBeInTheDocument();
    // The city dot is on the map even without a name.
    expect(container.querySelectorAll(".world-map__city-dot")).toHaveLength(1);
  });

  it("ховер страны из wishlist показывает подпись из списка желаний", async () => {
    const { container, user } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} />,
    );

    await user.hover(pathByFill(container, TONE.wishlist));

    expect(await screen.findByText("France")).toBeInTheDocument();
    expect(screen.getByText("On your wishlist")).toBeInTheDocument();
  });

  it("территория без ISO-кода (Northern Cyprus) показывает имя из geojson", async () => {
    // The only wishlist country: find its path by the unique fill.
    const { container, user } = renderWithProviders(
      <WorldMap countries={[{ id: "Northern Cyprus", status: "wishlist", cities: [] }]} tone={TONE} />,
    );

    await user.hover(pathByFill(container, TONE.wishlist));

    // An id that is not ISO alpha-2 resolves its name not via CLDR but from geojson (COUNTRY_NAMES).
    expect(await screen.findByText("Northern Cyprus")).toBeInTheDocument();
  });

  it("ховер непосещённой страны показывает «ещё не посещено»", async () => {
    const { container, user } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} />,
    );

    // Any country outside the countries prop gets status land, a muted "not visited yet".
    await user.hover(pathByFill(container, TONE.land));

    expect(await screen.findByText("Not visited yet")).toBeInTheDocument();
  });

  it("у края экрана тултип отражается к курсору (flip)", async () => {
    const { container, user } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} />,
    );

    await user.hover(pathByFill(container, TONE.visited));
    const wrap = container.querySelector<HTMLDivElement>(".world-map-wrap");
    if (!wrap) {
      throw new Error("Обёртка карты не найдена");
    }
    const tooltip = container.querySelector<HTMLDivElement>(".world-map__tooltip");
    if (!tooltip) {
      throw new Error("Тултип не найден");
    }

    // Far beyond the right/bottom viewport edge the tooltip flips toward the cursor (calc(-100%)).
    fireEvent.mouseMove(wrap, { clientX: 5000, clientY: 5000 });
    expect(tooltip.style.transform).toContain("calc(-100%");

    // Closer to the origin: the normal offset, no flip (no calc()).
    fireEvent.mouseMove(wrap, { clientX: 5, clientY: 5 });
    expect(tooltip.style.transform).not.toContain("calc(");
  });

  it("увод курсора со страны убирает тултип", async () => {
    const { container, user } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} />,
    );

    const visited = pathByFill(container, TONE.visited);
    await user.hover(visited);
    expect(container.querySelector(".world-map__tooltip")).not.toBeNull();

    await user.unhover(visited);
    expect(container.querySelector(".world-map__tooltip")).toBeNull();
  });
});

// --- Zoom, initial view and the layer over the map ----------------------------

// The map SVG fills the whole 1000x487 px area: in the whole-world view a pixel equals a canvas unit.
const SCREEN_RECTS: Record<string, ScreenRect> = {
  "world-map": { left: 0, top: 0, width: 1000, height: 487 },
  "world-map-canvas": { left: 0, top: 0, width: 1000, height: 487 },
  "world-map-wrap": { left: 0, top: 0, width: 1000, height: 487 },
  "occluder-over-map": { left: 0, top: 0, width: 400, height: 487 },
  "occluder-above-map": { left: 0, top: -300, width: 400, height: 200 },
};

// A wheel scroll of this amount gives exactly 2x zoom (the scale is exp of the scroll).
const ZOOM_IN_TWICE_DELTA = -100 * Math.LN2;

function viewBoxOf(container: HTMLElement): ViewBox {
  const [x, y, width, height] = (container.querySelector(".world-map")?.getAttribute("viewBox") ?? "")
    .split(" ")
    .map(Number);
  return { x, y, width, height };
}

function canvasOf(container: HTMLElement): HTMLElement {
  const canvas = container.querySelector<HTMLElement>(".world-map-canvas");
  if (!canvas) {
    throw new Error("Область карты не найдена");
  }

  return canvas;
}

/** Safari sends a trackpad pinch as separate events with `scale`. */
function gesture(type: string, scale: number, clientX: number, clientY: number): Event {
  return Object.assign(new Event(type, { bubbles: true, cancelable: true }), { scale, clientX, clientY });
}

interface OccludedMapProps {
  fitBounds: ViewBox;
  occluderClass: string;
  shouldFadeUnderOccluder?: boolean;
  isFitAnimated?: boolean;
}

/** A map with a panel over it: the panel ref, as the section shell passes it. */
function OccludedMap({ fitBounds, occluderClass, shouldFadeUnderOccluder, isFitAnimated }: OccludedMapProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  return (
    <>
      <div ref={panelRef} className={occluderClass} />
      <WorldMap
        countries={COUNTRIES}
        tone={TONE}
        fitBounds={fitBounds}
        occluderRef={panelRef}
        shouldFadeUnderOccluder={shouldFadeUnderOccluder}
        isFitAnimated={isFitAnimated}
      />
    </>
  );
}

describe("WorldMap: масштаб и слой поверх карты", () => {
  beforeEach(() => {
    stubScreenLayout(SCREEN_RECTS);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("щипок тачпада над картой приближает только её, вокруг курсора", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);

    const isPassedToPage = fireEvent.wheel(canvasOf(container), {
      ctrlKey: true,
      deltaY: ZOOM_IN_TWICE_DELTA,
      clientX: 250,
      clientY: 100,
    });

    const view = viewBoxOf(container);
    // The page did not get the gesture: there is nothing for the browser to zoom.
    expect(isPassedToPage).toBe(false);
    expect(view.width).toBeCloseTo(WORLD_VIEW_BOX.width / 2);
    // The point under the cursor (canvas x=250) stayed at its screen position, a quarter of the width.
    expect((250 - view.x) / view.width).toBeCloseTo(0.25);
    expect(container.querySelector(".world-map-wrap--zoomed")).not.toBeNull();
  });

  it("обычная прокрутка над картой во весь мир достаётся странице", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);

    const isPassedToPage = fireEvent.wheel(canvasOf(container), { deltaY: 120 });

    expect(isPassedToPage).toBe(true);
    expect(viewBoxOf(container)).toEqual(WORLD_VIEW_BOX);
  });

  it("приближенную карту прокрутка двигает, а не листает страницу", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);
    const canvas = canvasOf(container);
    fireEvent.wheel(canvas, { ctrlKey: true, deltaY: ZOOM_IN_TWICE_DELTA, clientX: 500, clientY: 240 });
    const zoomed = viewBoxOf(container);

    const isPassedToPage = fireEvent.wheel(canvas, { deltaX: 40, deltaY: 20 });

    const moved = viewBoxOf(container);
    expect(isPassedToPage).toBe(false);
    // The SVG is 1000 px on screen with half the world in frame: a pixel is half a canvas unit.
    expect(moved.x).toBeCloseTo(zoomed.x + 20);
    expect(moved.y).toBeCloseTo(zoomed.y + 10);
  });

  it("перетаскивание двигает приближенную карту, двойной клик возвращает весь мир", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);
    const canvas = canvasOf(container);
    fireEvent.wheel(canvas, { ctrlKey: true, deltaY: ZOOM_IN_TWICE_DELTA, clientX: 500, clientY: 240 });
    const zoomed = viewBoxOf(container);

    fireEvent.pointerDown(canvas, { pointerId: 1, pointerType: "mouse", button: 0, clientX: 300, clientY: 200 });
    fireEvent.pointerMove(canvas, { pointerId: 1, pointerType: "mouse", clientX: 260, clientY: 180 });
    fireEvent.pointerUp(canvas, { pointerId: 1, pointerType: "mouse" });

    // The map is dragged along: cursor left-up moves the area right-down.
    const dragged = viewBoxOf(container);
    expect(dragged.x).toBeCloseTo(zoomed.x + 20);
    expect(dragged.y).toBeCloseTo(zoomed.y + 10);

    // After release, mouse movement does not move the map.
    fireEvent.pointerMove(canvas, { pointerId: 1, pointerType: "mouse", clientX: 100, clientY: 100 });
    expect(viewBoxOf(container)).toEqual(dragged);

    fireEvent.doubleClick(canvas);
    expect(viewBoxOf(container)).toEqual(WORLD_VIEW_BOX);
  });

  it("щипок двумя пальцами приближает карту", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);
    const canvas = canvasOf(container);

    fireEvent.pointerDown(canvas, { pointerId: 1, pointerType: "touch", clientX: 400, clientY: 200 });
    fireEvent.pointerDown(canvas, { pointerId: 2, pointerType: "touch", clientX: 600, clientY: 200 });
    // The fingers moved apart from 200 to 400 px: twice as far.
    fireEvent.pointerMove(canvas, { pointerId: 2, pointerType: "touch", clientX: 800, clientY: 200 });

    expect(viewBoxOf(container).width).toBeCloseTo(WORLD_VIEW_BOX.width / 2);
  });

  it("щипок тачпада в Safari приближает карту и не масштабирует страницу", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);
    const canvas = canvasOf(container);

    fireEvent(canvas, gesture("gesturestart", 1, 500, 240));
    const change = gesture("gesturechange", 2, 500, 240);
    fireEvent(canvas, change);
    fireEvent(canvas, gesture("gestureend", 2, 500, 240));

    expect(change.defaultPrevented).toBe(true);
    expect(viewBoxOf(container).width).toBeCloseTo(WORLD_VIEW_BOX.width / 2);
  });

  it("слой поверх карты и точки городов держат экранный размер при приближении", () => {
    const { container } = renderWithProviders(
      <WorldMap
        countries={COUNTRIES}
        tone={TONE}
        overlay={(view) => <rect className="overlay-probe" width={view.width} height={view.height} />}
      />,
    );
    const probe = () => container.querySelector(".overlay-probe");
    const cityDot = () => container.querySelector(".world-map__city-dot");
    expect(probe()?.getAttribute("width")).toBe(String(WORLD_VIEW_BOX.width));
    const worldRadius = Number(cityDot()?.getAttribute("r"));

    fireEvent.wheel(canvasOf(container), { ctrlKey: true, deltaY: ZOOM_IN_TWICE_DELTA, clientX: 500, clientY: 240 });

    // The layer receives the current area, and the city dot in canvas units is half as large.
    expect(Number(probe()?.getAttribute("width"))).toBeCloseTo(WORLD_VIEW_BOX.width / 2);
    expect(Number(cityDot()?.getAttribute("r"))).toBeCloseTo(worldRadius / 2);
  });

  it("статичная карта не показывает тултип и не подсвечивает страны, но приближается", async () => {
    const { container, user } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} isInteractive={false} />,
    );

    await user.hover(pathByFill(container, TONE.visited));

    expect(container.querySelector(".world-map__tooltip")).toBeNull();
    expect(container.querySelector(".world-map-wrap--static")).not.toBeNull();

    fireEvent.wheel(canvasOf(container), { ctrlKey: true, deltaY: ZOOM_IN_TWICE_DELTA, clientX: 500, clientY: 240 });
    expect(viewBoxOf(container).width).toBeLessThan(WORLD_VIEW_BOX.width);
  });

  it("стартовый вид приближен к содержимому и не прячет его под панелью поверх карты", () => {
    const bounds: ViewBox = { x: 400, y: 180, width: 200, height: 20 };
    const panelWidth = SCREEN_RECTS["occluder-over-map"].width;
    const leftOnScreen = (view: ViewBox) => ((bounds.x - view.x) / view.width) * SCREEN_RECTS["world-map"].width;

    const free = renderWithProviders(<OccludedMap fitBounds={bounds} occluderClass="occluder-above-map" />);
    const freeView = viewBoxOf(free.container);
    free.unmount();
    const occluded = renderWithProviders(<OccludedMap fitBounds={bounds} occluderClass="occluder-over-map" />);
    const occludedView = viewBoxOf(occluded.container);

    // A panel above the map (mobile layout) covers nothing: the content is centered in frame, and
    // its left edge would fall right under the panel if it were over the map.
    expect(freeView.width).toBeLessThan(WORLD_VIEW_BOX.width);
    expect(freeView.x + freeView.width / 2).toBeCloseTo(bounds.x + bounds.width / 2);
    expect(leftOnScreen(freeView)).toBeLessThan(panelWidth);
    // A panel over the left 400 px: the frame is shifted, the content's left edge is right of the panel.
    expect(leftOnScreen(occludedView)).toBeGreaterThan(panelWidth);

    // A double click restores the initial view specifically, not the whole world.
    fireEvent.doubleClick(canvasOf(occluded.container));
    expect(viewBoxOf(occluded.container)).toEqual(occludedView);
  });

  it("новый стартовый вид не затирает масштаб, который пользователь уже выставил", () => {
    const first: ViewBox = { x: 400, y: 180, width: 200, height: 20 };
    const second: ViewBox = { x: 300, y: 160, width: 300, height: 30 };
    const { container, rerender } = renderWithProviders(
      <OccludedMap fitBounds={first} occluderClass="occluder-above-map" />,
    );

    // An untouched view moves to the new initial one.
    rerender(<OccludedMap fitBounds={second} occluderClass="occluder-above-map" />);
    const untouchedView = viewBoxOf(container);
    expect(untouchedView.width).toBeLessThan(WORLD_VIEW_BOX.width);

    fireEvent.wheel(canvasOf(container), { ctrlKey: true, deltaY: ZOOM_IN_TWICE_DELTA, clientX: 250, clientY: 100 });
    const zoomedView = viewBoxOf(container);
    rerender(<OccludedMap fitBounds={first} occluderClass="occluder-above-map" />);

    expect(zoomedView.width).toBeLessThan(untouchedView.width);
    expect(viewBoxOf(container)).toEqual(zoomedView);
  });

  it("карта растворяется к кромке панели поверх неё — и только когда панель действительно поверх", () => {
    const bounds: ViewBox = { x: 400, y: 180, width: 200, height: 20 };

    const over = renderWithProviders(<OccludedMap fitBounds={bounds} occluderClass="occluder-over-map" />);
    // The fade starts at the panel edge: exactly as much is covered as the panel occupies.
    expect(over.container.querySelector(".world-map-wrap--occluded")).not.toBeNull();
    expect(canvasOf(over.container).style.getPropertyValue("--map-occluded-left")).toBe(
      `${SCREEN_RECTS["occluder-over-map"].width}px`,
    );
    over.unmount();

    // A panel above the map (mobile layout) covers nothing, so there is nothing to fade. "No strip"
    // is a zero width rather than an unset variable, so the panel mask can glide in and out.
    const above = renderWithProviders(<OccludedMap fitBounds={bounds} occluderClass="occluder-above-map" />);
    expect(above.container.querySelector(".world-map-wrap--occluded")).toBeNull();
    expect(canvasOf(above.container).style.getPropertyValue("--map-occluded-left")).toBe("0px");
  });

  it("масштаб канваса при закрытии плашки не сдвигает кромку панели и кадр", () => {
    const bounds: ViewBox = { x: 400, y: 180, width: 200, height: 20 };
    const steady = renderWithProviders(<OccludedMap fitBounds={bounds} occluderClass="occluder-over-map" />);
    const steadyView = viewBoxOf(steady.container);
    steady.unmount();

    // The banner glide scales the canvas from its bottom centre; the wrap around it keeps the real box.
    stubScreenLayout({ ...SCREEN_RECTS, "world-map-canvas": { left: 45, top: 45, width: 910, height: 442 } });
    const { container } = renderWithProviders(<OccludedMap fitBounds={bounds} occluderClass="occluder-over-map" />);

    expect(canvasOf(container).style.getPropertyValue("--map-occluded-left")).toBe(
      `${SCREEN_RECTS["occluder-over-map"].width}px`,
    );
    expect(viewBoxOf(container)).toEqual(steadyView);
  });

  it("сквозь прозрачную панель карта видна целиком, а кадр всё равно правее панели", () => {
    const bounds: ViewBox = { x: 400, y: 180, width: 200, height: 20 };
    const faded = renderWithProviders(<OccludedMap fitBounds={bounds} occluderClass="occluder-over-map" />);
    const fadedView = viewBoxOf(faded.container);
    faded.unmount();

    const { container } = renderWithProviders(
      <OccludedMap fitBounds={bounds} occluderClass="occluder-over-map" shouldFadeUnderOccluder={false} />,
    );

    expect(container.querySelector(".world-map-wrap--occluded")).toBeNull();
    expect(canvasOf(container).style.getPropertyValue("--map-occluded-left")).toBe("0px");
    expect(viewBoxOf(container)).toEqual(fadedView);
  });

  it("с плавной сменой кадра карта переезжает к новому кадру, а не прыгает", async () => {
    const first: ViewBox = { x: 400, y: 180, width: 200, height: 20 };
    const second: ViewBox = { x: 100, y: 100, width: 300, height: 30 };
    const target = renderWithProviders(<OccludedMap fitBounds={second} occluderClass="occluder-above-map" />);
    const secondView = viewBoxOf(target.container);
    target.unmount();
    const { container, rerender } = renderWithProviders(
      <OccludedMap fitBounds={first} occluderClass="occluder-above-map" isFitAnimated />,
    );
    const firstView = viewBoxOf(container);

    rerender(<OccludedMap fitBounds={second} occluderClass="occluder-above-map" isFitAnimated />);

    // Right after the change the frame is still the old one, after animation frames an intermediate one, finally the new one.
    expect(viewBoxOf(container)).toEqual(firstView);
    await waitFor(() => {
      const view = viewBoxOf(container);
      expect(view.x).not.toBe(firstView.x);
      expect(view.x).not.toBe(secondView.x);
    });
    await waitFor(() => expect(viewBoxOf(container)).toEqual(secondView));
  });

  it("при «меньше движения» новый кадр показывается сразу, без переезда", () => {
    preferReducedMotion();
    const first: ViewBox = { x: 400, y: 180, width: 200, height: 20 };
    const second: ViewBox = { x: 100, y: 100, width: 300, height: 30 };
    const target = renderWithProviders(<OccludedMap fitBounds={second} occluderClass="occluder-above-map" />);
    const secondView = viewBoxOf(target.container);
    target.unmount();
    const { container, rerender } = renderWithProviders(
      <OccludedMap fitBounds={first} occluderClass="occluder-above-map" isFitAnimated />,
    );

    rerender(<OccludedMap fitBounds={second} occluderClass="occluder-above-map" isFitAnimated />);

    expect(viewBoxOf(container)).toEqual(secondView);
  });
});

describe("WorldMap: смена сцены", () => {
  const SCENE_BOUNDS: ViewBox = { x: 100, y: 100, width: 300, height: 30 };

  beforeEach(() => {
    stubScreenLayout(SCREEN_RECTS);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** The view a map fitted to `SCENE_BOUNDS` opens on: the end of every scene change below. */
  function sceneView(): ViewBox {
    const { container, unmount } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} fitBounds={SCENE_BOUNDS} />,
    );
    const view = viewBoxOf(container);
    unmount();
    return view;
  }

  /** A map on the whole world, zoomed in 2x by the user; returns its view after the zoom. */
  function renderZoomedScene() {
    const rendered = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} sceneKey="first" />);
    fireEvent.wheel(canvasOf(rendered.container), {
      ctrlKey: true,
      deltaY: ZOOM_IN_TWICE_DELTA,
      clientX: 250,
      clientY: 100,
    });
    return { ...rendered, zoomedView: viewBoxOf(rendered.container) };
  }

  it("новая сцена сбрасывает ручной зум и перелетает к своему кадру от того, что на экране", async () => {
    const targetView = sceneView();
    const { container, rerender, zoomedView } = renderZoomedScene();
    expect(zoomedView.width).toBe(WORLD_VIEW_BOX.width / 2);

    rerender(<WorldMap countries={COUNTRIES} tone={TONE} sceneKey="second" fitBounds={SCENE_BOUNDS} />);

    // The flight starts at the zoomed view on screen, passes an intermediate frame, lands on the scene's frame.
    expect(viewBoxOf(container)).toEqual(zoomedView);
    await waitFor(() => {
      const view = viewBoxOf(container);
      expect(view.x).not.toBe(zoomedView.x);
      expect(view.x).not.toBe(targetView.x);
    });
    await waitFor(() => expect(viewBoxOf(container)).toEqual(targetView));
    // The new scene's layer arrives staged, as the flight lands.
    expect(container.querySelector(".world-map__arriving")).not.toBeNull();
  });

  it.each([
    ["без анимации смены", false, () => {}],
    ["при «меньше движения»", true, preferReducedMotion],
  ] as const)("%s новая сцена встаёт в свой кадр сразу и тоже сбрасывает зум", async (_, isAnimated, setUp) => {
    setUp();
    const targetView = sceneView();
    const { container, rerender } = renderZoomedScene();

    rerender(
      <WorldMap
        countries={COUNTRIES}
        tone={TONE}
        sceneKey="second"
        fitBounds={SCENE_BOUNDS}
        isSceneChangeAnimated={isAnimated}
      />,
    );

    await waitFor(() => expect(viewBoxOf(container)).toEqual(targetView));
    expect(container.querySelector(".world-map__arriving")).toBeNull();
  });

  it("первая сцена появляется как есть, без постановки", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} sceneKey="first" />);

    expect(container.querySelector(".world-map__arriving")).toBeNull();
    expect(container.querySelectorAll(".world-map__city-dot")).toHaveLength(1);
  });

  it("слой прошлой сцены — её точки и наложение — рисуется поверх стран, пока гаснет", () => {
    const { container } = renderWithProviders(
      <WorldMap
        countries={[]}
        tone={TONE}
        leaving={{ key: "previous", countries: COUNTRIES, overlay: () => <circle className="previous-overlay" /> }}
      />,
    );

    const leaving = container.querySelector(".world-map__leaving");
    expect(leaving?.querySelectorAll(".world-map__city-dot")).toHaveLength(1);
    expect(leaving?.querySelector(".previous-overlay")).not.toBeNull();
    // The current scene has no cities: the only dot belongs to the leaving layer.
    expect(container.querySelectorAll(".world-map__city-dot")).toHaveLength(1);
  });
});

describe("WorldMap: фон", () => {
  it("приглушённая суша и декоративная карта: класс приглушения, карта скрыта от скринридера", () => {
    const { container } = renderWithProviders(
      <WorldMap countries={COUNTRIES} tone={TONE} isLandMuted isDecorative />,
    );

    const wrap = container.querySelector(".world-map-wrap");
    expect(wrap).toHaveClass("world-map-wrap--muted");
    expect(wrap).toHaveAttribute("aria-hidden", "true");
  });

  it("обычная карта не приглушена и видна скринридеру", () => {
    const { container } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);

    const wrap = container.querySelector(".world-map-wrap");
    expect(wrap).not.toHaveClass("world-map-wrap--muted");
    expect(wrap).not.toHaveAttribute("aria-hidden");
  });

  it("карта, ставшая неинтерактивной, убирает показанный тултип", async () => {
    const { container, user, rerender } = renderWithProviders(<WorldMap countries={COUNTRIES} tone={TONE} />);
    await user.hover(pathByFill(container, TONE.visited));
    expect(await screen.findByText("Russia")).toBeInTheDocument();

    rerender(<WorldMap countries={COUNTRIES} tone={TONE} isInteractive={false} />);

    expect(screen.queryByText("Russia")).not.toBeInTheDocument();
  });
});
