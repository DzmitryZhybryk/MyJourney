import { describe, expect, it } from "vitest";

import { fitView } from "./fitView";
import { WORLD_ASPECT, WORLD_VIEW_BOX, type ViewBox } from "./worldProjection";

// The map area is wider than the SVG: the map fits by height, with empty margins at the sides.
const WIDE_CANVAS = { width: 1600, height: 600 };
// A small rectangle of routes in the middle of the world.
const BOUNDS: ViewBox = { x: 480, y: 180, width: 40, height: 20 };

/** Screen x (px from the map area's left edge) of a canvas point for a given view. */
function screenX(view: ViewBox, canvas: { width: number; height: number }, x: number): number {
  const svgWidth = canvas.height * WORLD_ASPECT;
  return (canvas.width - svgWidth) / 2 + ((x - view.x) / view.width) * svgWidth;
}

describe("fitView", () => {
  it("приближает к маршрутам, держа их целиком в кадре и в пропорциях мира", () => {
    const view = fitView(BOUNDS, WIDE_CANVAS, 0);

    expect(view.width).toBeLessThan(WORLD_VIEW_BOX.width);
    expect(view.width / view.height).toBeCloseTo(WORLD_ASPECT);
    expect(view.x).toBeLessThanOrEqual(BOUNDS.x);
    expect(view.x + view.width).toBeGreaterThanOrEqual(BOUNDS.x + BOUNDS.width);
    expect(view.y).toBeLessThanOrEqual(BOUNDS.y);
    expect(view.y + view.height).toBeGreaterThanOrEqual(BOUNDS.y + BOUNDS.height);
  });

  it("не прячет маршруты под панелью: левый край маршрутов правее закрытой полосы", () => {
    const occludedLeft = 500;

    const view = fitView(BOUNDS, WIDE_CANVAS, occludedLeft);

    expect(screenX(view, WIDE_CANVAS, BOUNDS.x)).toBeGreaterThan(occludedLeft);
    expect(screenX(view, WIDE_CANVAS, BOUNDS.x + BOUNDS.width)).toBeLessThan(WIDE_CANVAS.width);
  });

  it("учитывает обрезку: в узкой области маршруты попадают в видимую середину SVG", () => {
    const narrowCanvas = { width: 300, height: 600 };

    const view = fitView(BOUNDS, narrowCanvas, 0);

    expect(screenX(view, narrowCanvas, BOUNDS.x)).toBeGreaterThanOrEqual(0);
    expect(screenX(view, narrowCanvas, BOUNDS.x + BOUNDS.width)).toBeLessThanOrEqual(narrowCanvas.width);
  });

  it("точку не раздувает на весь экран: ширина кадра не меньше четверти мира", () => {
    const view = fitView({ x: 500, y: 200, width: 0, height: 0 }, WIDE_CANVAS, 0);

    // Floating-point tolerance: the recomputation via pixels gives 249.99999999999997.
    expect(view.width).toBeGreaterThanOrEqual(WORLD_VIEW_BOX.width * 0.25 - 1e-9);
  });

  it("маршруты шире видимой части — весь мир", () => {
    expect(fitView({ x: 50, y: 50, width: 900, height: 300 }, WIDE_CANVAS, 0)).toEqual(WORLD_VIEW_BOX);
  });

  it("область без размера или целиком под панелью — весь мир", () => {
    expect(fitView(BOUNDS, { width: 0, height: 0 }, 0)).toEqual(WORLD_VIEW_BOX);
    expect(fitView(BOUNDS, WIDE_CANVAS, WIDE_CANVAS.width)).toEqual(WORLD_VIEW_BOX);
  });

  it("у края мира рамка сдвигается внутрь, а не выходит за край", () => {
    const view = fitView({ x: 0, y: 0, width: 20, height: 10 }, WIDE_CANVAS, 0);

    expect(view.x).toBe(0);
    expect(view.y).toBe(0);
  });
});
