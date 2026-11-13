import { renderHook } from "@testing-library/react";
import type { GlobeMethods } from "react-globe.gl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import carIcon from "../../assets/emoji/car.svg";
import planeIcon from "../../assets/emoji/plane.svg";
import shipIcon from "../../assets/emoji/ship.svg";
import { GEO_CITIES } from "../../test/handlers";
import { act } from "../../test/render";
import { ROUTE_FADE_MS, type GlobeRoute } from "./route";
import { createRouteElement, useRouteScene } from "./routeScene";

// On the equator the path midpoint is known without repeating the production great-circle math.
const EASTBOUND_ROUTE: GlobeRoute = {
  origin: { ...GEO_CITIES[0], latitude: 0, longitude: 10 },
  destination: { ...GEO_CITIES[1], latitude: 0, longitude: 70 },
  originLabel: "Запад",
  destinationLabel: "Восток",
  transportType: "air",
};

describe("createRouteElement", () => {
  it.each(["left", "right"] as const)("пин с подписью на стороне %s показывает название текстом", (side) => {
    const name = "<img src=x onerror=alert(1)>";
    const element = createRouteElement({ kind: "route-pin", lat: 0, lng: 10, alt: 0.01, name, side });

    expect(element).toHaveClass("globe-route", "globe-route-pin");
    expect(element.classList.contains("globe-route-pin--left")).toBe(side === "left");
    expect(element.querySelector(".globe-route-pin__dot")).not.toBeNull();
    expect(element.querySelector(".globe-route-pin__name")?.textContent).toBe(name);
    expect(element.querySelector("img")).toBeNull();
  });

  it("пин без названия и стороны получает пустую подпись справа", () => {
    const element = createRouteElement({ kind: "route-pin", lat: 0, lng: 10, alt: 0.01 });

    expect(element).toHaveClass("globe-route", "globe-route-pin");
    expect(element).not.toHaveClass("globe-route-pin--left");
    expect(element.querySelector(".globe-route-pin__name")?.textContent).toBe("");
  });

  it("транспорт без иконки сохраняет обёртку поворота и пустое декоративное изображение", () => {
    const element = createRouteElement({ kind: "route-vehicle", lat: 0, lng: 10, alt: 0 });
    const image = element.querySelector(".globe-route-vehicle__icon img");

    expect(element).toHaveClass("globe-route", "globe-route-vehicle");
    expect(image).toHaveAttribute("src", "");
    expect(image).toHaveAttribute("alt", "");
  });
});

describe("useRouteScene", () => {
  const getScreenCoords = vi.fn<GlobeMethods["getScreenCoords"]>();
  let container: HTMLDivElement;
  let options: Parameters<typeof useRouteScene>[0];

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
    // The WebGL boundary: a predictable screen projection, the route geometry stays real.
    getScreenCoords.mockReset().mockImplementation((lat, lng) => ({ x: lng, y: -lat }));
    container = document.createElement("div");
    options = {
      route: EASTBOUND_ROUTE,
      globeRef: { current: { getScreenCoords } as unknown as GlobeMethods },
      containerRef: { current: container },
      reducedMotion: false,
      fading: false,
    };
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it.each([
    { transportType: "air", durationMs: 3600, apex: 0.14, icon: planeIcon, transform: "rotate(45deg)" },
    { transportType: "land", durationMs: 5200, apex: 0.07, icon: carIcon, transform: "scaleX(-1)" },
    { transportType: "water", durationMs: 6000, apex: 0.07, icon: shipIcon, transform: "scaleX(-1)" },
  ] as const)("транспорт $transportType движется вместе со следом и повторяет путь за $durationMs мс", ({
    transportType, durationMs, apex, icon, transform,
  }) => {
    const { result } = renderHook(useRouteScene, {
      initialProps: { ...options, route: { ...EASTBOUND_ROUTE, transportType } },
    });
    const vehicle = result.current.htmlData.find((datum) => datum.kind === "route-vehicle");
    if (!vehicle) throw new Error("транспорт отсутствует в сцене");
    const element = createRouteElement(vehicle);
    container.append(element);

    expect(element.querySelector("img")).toHaveAttribute("src", icon);
    expect(element.querySelector("img")).toHaveAttribute("alt", "");
    act(() => vi.advanceTimersToNextFrame());
    expect(vehicle).toMatchObject({ lat: 0, lng: expect.closeTo(10), alt: 0 });
    const initialTrailLength = result.current.trails[0].coords.length;

    act(() => vi.advanceTimersByTime(durationMs / 2));
    expect(vehicle.lat).toBeCloseTo(0);
    // rAF runs in 16 ms steps; the cycle midpoint may fall between adjacent frames.
    expect(vehicle.lng).toBeCloseTo(40, 0);
    expect(vehicle.alt).toBeCloseTo(apex, 3);
    expect(element.querySelector<HTMLElement>(".globe-route-vehicle__icon")?.style.transform).toBe(transform);
    const trail = result.current.trails[0];
    expect(trail.coords.length).toBeGreaterThan(initialTrailLength);
    expect(trail.coords[0]).toEqual({ lat: 0, lng: expect.closeTo(10), alt: 0 });
    expect(trail.coords.at(-1)).toEqual({ lat: vehicle.lat, lng: vehicle.lng, alt: vehicle.alt });

    act(() => vi.advanceTimersByTime(durationMs / 2));
    expect(vehicle).toMatchObject({ lat: 0, lng: expect.closeTo(10), alt: 0 });
    expect(result.current.trails[0].coords).toHaveLength(initialTrailLength);
    expect(result.current.trails[0].coords.at(-1)).toEqual({ lat: 0, lng: expect.closeTo(10), alt: 0 });
  });

  it("подписи концов смотрят наружу и меняют стороны при развороте маршрута", () => {
    const { result, rerender } = renderHook(useRouteScene, { initialProps: options });
    const [origin, destination] = result.current.htmlData.map(createRouteElement);

    expect(origin).toHaveTextContent("Запад");
    expect(origin).toHaveClass("globe-route-pin--left");
    expect(destination).toHaveTextContent("Восток");
    expect(destination).not.toHaveClass("globe-route-pin--left");

    rerender({
      ...options,
      route: {
        ...EASTBOUND_ROUTE,
        origin: EASTBOUND_ROUTE.destination,
        destination: EASTBOUND_ROUTE.origin,
        originLabel: "Восток",
        destinationLabel: "Запад",
      },
    });
    const [reversedOrigin, reversedDestination] = result.current.htmlData.map(createRouteElement);
    expect(reversedOrigin).toHaveTextContent("Восток");
    expect(reversedOrigin).not.toHaveClass("globe-route-pin--left");
    expect(reversedDestination).toHaveTextContent("Запад");
    expect(reversedDestination).toHaveClass("globe-route-pin--left");
  });

  it.each([
    { transportType: "air", transform: "rotate(180deg)" },
    { transportType: "land", transform: "scaleX(1)" },
    { transportType: "water", transform: "scaleX(1)" },
  ] as const)("при reduced motion транспорт $transportType стоит в конце с полным следом и верным курсом", ({
    transportType, transform,
  }) => {
    // A diagonal projection checks both heading components at the last path point.
    getScreenCoords.mockImplementation((_lat, lng) => ({ x: lng, y: -lng }));
    const sceneOptions = {
      ...options,
      route: { ...EASTBOUND_ROUTE, origin: EASTBOUND_ROUTE.destination, destination: EASTBOUND_ROUTE.origin, transportType },
    };
    const { result, rerender } = renderHook(useRouteScene, { initialProps: sceneOptions });
    const vehicle = result.current.htmlData.find((datum) => datum.kind === "route-vehicle");
    if (!vehicle) throw new Error("транспорт отсутствует в сцене");
    const element = createRouteElement(vehicle);
    container.append(element);

    rerender({ ...sceneOptions, reducedMotion: true });

    expect(vehicle.lat).toBeCloseTo(0);
    expect(vehicle.lng).toBeCloseTo(10);
    expect(vehicle.alt).toBeCloseTo(0);
    expect(element.querySelector<HTMLElement>(".globe-route-vehicle__icon")?.style.transform).toBe(transform);
    const trail = result.current.trails[0].coords;
    expect(trail[0]).toEqual({ lat: 0, lng: expect.closeTo(70), alt: 0 });
    expect(trail.at(-1)).toEqual({ lat: vehicle.lat, lng: vehicle.lng, alt: vehicle.alt });
    expect(trail.some((point) => point.lng > 39 && point.lng < 41 && point.alt > 0)).toBe(true);

    const settled = structuredClone(result.current);
    act(() => vi.advanceTimersByTime(6000));
    expect(result.current).toEqual(settled);
  });

  it("угасание обнуляет прозрачность следа за отведённое время, пока транспорт продолжает путь", () => {
    const { result, rerender } = renderHook(useRouteScene, { initialProps: options });
    act(() => vi.advanceTimersToNextFrame());
    act(() => vi.advanceTimersByTime(800));
    const beforeFade = result.current.trails[0].coords.at(-1);
    expect(result.current.trails[0].color).toBe("rgba(232, 147, 92, 1)");

    rerender({ ...options, fading: true });
    act(() => vi.advanceTimersToNextFrame());
    act(() => vi.advanceTimersByTime(ROUTE_FADE_MS / 2));
    const alpha = Number(result.current.trails[0].color.match(/, ([\d.]+)\)$/u)?.[1]);
    expect(alpha).toBeCloseTo(0.5, 1);
    expect(result.current.trails[0].coords.at(-1)?.lng).toBeGreaterThan(beforeFade?.lng ?? 70);

    act(() => vi.advanceTimersByTime(ROUTE_FADE_MS));
    expect(result.current.trails[0].color).toBe("rgba(232, 147, 92, 0)");
    const fadedHead = result.current.trails[0].coords.at(-1);
    act(() => vi.advanceTimersByTime(160));
    expect(result.current.trails[0].color).toBe("rgba(232, 147, 92, 0)");
    expect(result.current.trails[0].coords.at(-1)?.lng).toBeGreaterThan(fadedHead?.lng ?? 70);
  });

  it("прерванное угасание восстанавливает непрозрачный след и не гасит его старыми кадрами", () => {
    const { result, rerender } = renderHook(useRouteScene, { initialProps: { ...options, fading: true } });
    act(() => vi.advanceTimersToNextFrame());
    act(() => vi.advanceTimersByTime(ROUTE_FADE_MS / 2));
    expect(result.current.trails[0].color).not.toBe("rgba(232, 147, 92, 1)");

    rerender(options);
    act(() => vi.advanceTimersToNextFrame());
    expect(result.current.trails[0].color).toBe("rgba(232, 147, 92, 1)");
    act(() => vi.advanceTimersByTime(ROUTE_FADE_MS));
    expect(result.current.trails[0].color).toBe("rgba(232, 147, 92, 1)");
  });

  it("удаление маршрута очищает слои и останавливает движение прежнего транспорта", () => {
    const { result, rerender } = renderHook(useRouteScene, { initialProps: options });
    act(() => vi.advanceTimersToNextFrame());
    act(() => vi.advanceTimersByTime(800));
    const vehicle = result.current.htmlData.find((datum) => datum.kind === "route-vehicle");
    if (!vehicle) throw new Error("транспорт отсутствует в сцене");
    expect(vehicle.lng).toBeGreaterThan(10);
    const stopped = { ...vehicle };

    rerender({ ...options, route: null });
    act(() => vi.advanceTimersByTime(1600));

    expect(result.current).toEqual({ htmlData: [], trails: [] });
    expect(vehicle).toEqual(stopped);
  });

  it("размонтирование останавливает движение транспорта", () => {
    const { result, unmount } = renderHook(useRouteScene, { initialProps: options });
    act(() => vi.advanceTimersToNextFrame());
    act(() => vi.advanceTimersByTime(800));
    const vehicle = result.current.htmlData.find((datum) => datum.kind === "route-vehicle");
    if (!vehicle) throw new Error("транспорт отсутствует в сцене");
    expect(vehicle.lng).toBeGreaterThan(10);
    const stopped = { ...vehicle };

    unmount();
    act(() => vi.advanceTimersByTime(1600));

    expect(vehicle).toEqual(stopped);
  });
});
