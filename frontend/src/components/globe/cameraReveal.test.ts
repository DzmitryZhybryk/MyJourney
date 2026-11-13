import { describe, expect, it } from "vitest";

import { revealPov } from "./cameraReveal";

const TARGET = { lat: 12, lng: 40, altitude: 2.4 };
const DURATION_MS = 1400;
// globe.gl auto-rotation in degrees of camera longitude per second (it decreases longitude).
const SPIN = -2.52;

describe("revealPov", () => {
  it("старт — дальше цели и с экватора", () => {
    const start = revealPov(TARGET, 0, SPIN, DURATION_MS);

    expect(start.altitude).toBeCloseTo(TARGET.altitude * 1.45);
    expect(start.lat).toBe(0);
  });

  it("старт развёрнут против хода вращения: за подлёт глобус докручивается к цели", () => {
    const start = revealPov(TARGET, 0, SPIN, DURATION_MS);

    // Auto-rotation decreases longitude, so start east of the target.
    expect(start.lng).toBeGreaterThan(TARGET.lng);
  });

  it("в конце — ровно цель", () => {
    const end = revealPov(TARGET, 1, SPIN, DURATION_MS);

    expect(end.lat).toBeCloseTo(TARGET.lat);
    expect(end.lng).toBeCloseTo(TARGET.lng);
    expect(end.altitude).toBeCloseTo(TARGET.altitude);
  });

  it("прогресс за пределами 0..1 зажимается — камера не пролетает цель", () => {
    expect(revealPov(TARGET, 1.3, SPIN, DURATION_MS)).toEqual(revealPov(TARGET, 1, SPIN, DURATION_MS));
    expect(revealPov(TARGET, -0.2, SPIN, DURATION_MS)).toEqual(revealPov(TARGET, 0, SPIN, DURATION_MS));
  });

  it("камера только приближается — без отскока назад", () => {
    const altitudes = [0, 0.25, 0.5, 0.75, 1].map((progress) => revealPov(TARGET, progress, SPIN, DURATION_MS).altitude);

    for (let index = 1; index < altitudes.length; index += 1) {
      expect(altitudes[index]).toBeLessThan(altitudes[index - 1]);
    }
  });

  it("к концу скорость поворота равна автовращению — вращение подхватывается без шва", () => {
    const step = 0.001;
    const before = revealPov(TARGET, 1 - step, SPIN, DURATION_MS);
    const end = revealPov(TARGET, 1, SPIN, DURATION_MS);
    const degPerSec = (end.lng - before.lng) / ((step * DURATION_MS) / 1000);

    expect(degPerSec).toBeCloseTo(SPIN, 1);
  });

  it("поворот всё время идёт в сторону автовращения", () => {
    const longitudes = [0, 0.25, 0.5, 0.75, 1].map((progress) => revealPov(TARGET, progress, SPIN, DURATION_MS).lng);

    for (let index = 1; index < longitudes.length; index += 1) {
      expect(longitudes[index]).toBeLessThan(longitudes[index - 1]);
    }
  });

  it("вращение в обратную сторону — докрутка тоже по его ходу", () => {
    const start = revealPov(TARGET, 0, -SPIN, DURATION_MS);
    const middle = revealPov(TARGET, 0.5, -SPIN, DURATION_MS);

    expect(start.lng).toBeLessThan(TARGET.lng);
    expect(middle.lng).toBeGreaterThan(start.lng);
  });

  it("без автовращения глобус докручивается и останавливается в цели", () => {
    const start = revealPov(TARGET, 0, 0, DURATION_MS);
    const step = 0.001;
    const before = revealPov(TARGET, 1 - step, 0, DURATION_MS);
    const end = revealPov(TARGET, 1, 0, DURATION_MS);

    expect(start.lng).not.toBeCloseTo(TARGET.lng);
    expect((end.lng - before.lng) / ((step * DURATION_MS) / 1000)).toBeCloseTo(0, 1);
  });
});
