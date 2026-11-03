import { describe, expect, it } from "vitest";

import {
  WORLD_ASPECT,
  WORLD_VIEW_BOX,
  clampView,
  isWorldView,
  panView,
  projectToScreen,
  zoomView,
  type ViewBox,
} from "./worldProjection";

const WORLD_WIDTH = WORLD_VIEW_BOX.width;
const WORLD_HEIGHT = WORLD_VIEW_BOX.height;

/** The share of the visible area's width at which a canvas point lies. */
function relativeX(view: ViewBox, x: number): number {
  return (x - view.x) / view.width;
}

describe("projectToScreen", () => {
  it("кладёт экватор и нулевой меридиан в центр холста, антимеридиан — на края", () => {
    const [centerX, centerY] = projectToScreen(0, 0);
    expect(centerX).toBeCloseTo(WORLD_WIDTH / 2);
    expect(centerY).toBeCloseTo(WORLD_HEIGHT / 2);
    expect(projectToScreen(-180, 0)[0]).toBeCloseTo(0);
    expect(projectToScreen(180, 0)[0]).toBeCloseTo(WORLD_WIDTH);
  });

  it("север — вверху холста, полюса — на его верхней и нижней границе", () => {
    expect(projectToScreen(0, 90)[1]).toBeCloseTo(0, 0);
    expect(projectToScreen(0, -90)[1]).toBeCloseTo(WORLD_HEIGHT, 0);
    expect(projectToScreen(0, 50)[1]).toBeLessThan(projectToScreen(0, -50)[1]);
  });
});

describe("isWorldView", () => {
  it("весь мир — не приближен, область уже мира — приближена", () => {
    expect(isWorldView(WORLD_VIEW_BOX)).toBe(true);
    expect(isWorldView({ ...WORLD_VIEW_BOX, width: WORLD_WIDTH / 2 })).toBe(false);
  });
});

describe("clampView", () => {
  it("область шире мира сжимает до всего мира", () => {
    expect(clampView({ x: -50, y: -50, width: WORLD_WIDTH * 3, height: WORLD_HEIGHT * 3 })).toEqual(WORLD_VIEW_BOX);
  });

  it("сильнее ×8 не приближает и держит пропорции мира", () => {
    const view = clampView({ x: 100, y: 100, width: 1, height: 1 });

    expect(view.width).toBeCloseTo(WORLD_WIDTH / 8);
    expect(view.width / view.height).toBeCloseTo(WORLD_ASPECT);
  });

  it("не выпускает область за край мира ни с одной стороны", () => {
    const width = WORLD_WIDTH / 4;
    const height = width / WORLD_ASPECT;

    const leftTop = clampView({ x: -30, y: -30, width, height });
    expect(leftTop.x).toBe(0);
    expect(leftTop.y).toBe(0);

    const rightBottom = clampView({ x: WORLD_WIDTH, y: WORLD_HEIGHT, width, height });
    expect(rightBottom.x).toBeCloseTo(WORLD_WIDTH - width);
    expect(rightBottom.y).toBeCloseTo(WORLD_HEIGHT - height);
  });
});

describe("zoomView", () => {
  it("приближение вдвое сужает область вдвое, и точка под курсором остаётся на месте", () => {
    const anchorX = 600;
    const anchorY = 250;

    const zoomed = zoomView(WORLD_VIEW_BOX, 2, anchorX, anchorY);

    expect(zoomed.width).toBeCloseTo(WORLD_WIDTH / 2);
    expect(relativeX(zoomed, anchorX)).toBeCloseTo(relativeX(WORLD_VIEW_BOX, anchorX));
    expect((anchorY - zoomed.y) / zoomed.height).toBeCloseTo((anchorY - WORLD_VIEW_BOX.y) / WORLD_VIEW_BOX.height);
  });

  it("не приближает сильнее ×8 и не отдаляет дальше всего мира", () => {
    expect(zoomView(WORLD_VIEW_BOX, 1000, 500, 250).width).toBeCloseTo(WORLD_WIDTH / 8);
    expect(zoomView(WORLD_VIEW_BOX, 0.1, 500, 250)).toEqual(WORLD_VIEW_BOX);
  });
});

describe("panView", () => {
  it("сдвигает приближенную область и упирается в край мира", () => {
    const zoomed = zoomView(WORLD_VIEW_BOX, 4, 500, 250);

    const moved = panView(zoomed, 40, -20);
    expect(moved.x).toBeCloseTo(zoomed.x + 40);
    expect(moved.y).toBeCloseTo(zoomed.y - 20);

    const pushedPastLeft = panView(zoomed, -WORLD_WIDTH, 0);
    expect(pushedPastLeft.x).toBe(0);
  });

  it("весь мир сдвинуть нельзя", () => {
    expect(panView(WORLD_VIEW_BOX, 100, 100)).toEqual(WORLD_VIEW_BOX);
  });
});
