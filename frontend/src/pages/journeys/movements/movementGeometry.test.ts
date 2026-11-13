import { describe, expect, it } from "vitest";

import { projectToScreen } from "../../../components/worldProjection";
import { piecePath, projectArc, splitEdgeFade } from "./movementGeometry";

const MOSCOW = { latitude: 55.75, longitude: 37.62 };
const LONDON = { latitude: 51.5, longitude: -0.12 };
// Tokyo -> Los Angeles: the short great-circle path crosses the Pacific, over the antimeridian.
const TOKYO = { latitude: 35.69, longitude: 139.69 };
const LOS_ANGELES = { latitude: 34.05, longitude: -118.24 };

describe("projectArc", () => {
  it("дуга без антимеридиана — один кусок от точки отправления до точки назначения", () => {
    const pieces = projectArc(MOSCOW, LONDON);

    expect(pieces).toHaveLength(1);
    const [start, end] = [pieces[0][0], pieces[0][pieces[0].length - 1]];
    const [moscowX, moscowY] = projectToScreen(MOSCOW.longitude, MOSCOW.latitude);
    const [londonX, londonY] = projectToScreen(LONDON.longitude, LONDON.latitude);
    expect(start[0]).toBeCloseTo(moscowX);
    expect(start[1]).toBeCloseTo(moscowY);
    expect(end[0]).toBeCloseTo(londonX);
    expect(end[1]).toBeCloseTo(londonY);
  });

  it("дуга большого круга выгибается к полюсу, а не идёт по прямой на холсте", () => {
    const pieces = projectArc(MOSCOW, LONDON);
    const middle = pieces[0][Math.floor(pieces[0].length / 2)];
    const straightMiddleY = (projectToScreen(MOSCOW.longitude, MOSCOW.latitude)[1] + projectToScreen(LONDON.longitude, LONDON.latitude)[1]) / 2;

    // North is at the top of the canvas: the arc midpoint is above the segment midpoint.
    expect(middle[1]).toBeLessThan(straightMiddleY);
  });

  it("дуга через антимеридиан разрезана на два куска у противоположных краёв карты", () => {
    const pieces = projectArc(TOKYO, LOS_ANGELES);

    expect(pieces).toHaveLength(2);
    const firstEnd = pieces[0][pieces[0].length - 1];
    const secondStart = pieces[1][0];
    expect(firstEnd[0]).toBeGreaterThan(900);
    expect(secondStart[0]).toBeLessThan(100);
  });
});

describe("piecePath", () => {
  it("кусок начинается командой M, остальные точки — L, координаты с одним знаком после точки", () => {
    expect(
      piecePath([
        [1, 2],
        [3, 4],
        [7.25, 8],
      ]),
    ).toBe("M1.0 2.0L3.0 4.0L7.3 8.0");
  });
});

describe("splitEdgeFade", () => {
  // A straight piece along the x axis: points every 10 units, from 0 to 100.
  const piece = Array.from({ length: 11 }, (_, index) => [index * 10, 50] as const);

  it("у конца куска гаснет только хвост заданной длины, остальное сплошное", () => {
    expect(splitEdgeFade(piece, "end", 25)).toEqual({
      solid: [...piece.slice(0, 8), [75, 50]],
      fade: [
        [75, 50],
        [80, 50],
        [90, 50],
        [100, 50],
      ],
      fadeAxis: [
        [75, 50],
        [100, 50],
      ],
    });
  });

  it("у начала куска — то же с другой стороны, обе части в порядке рисования", () => {
    expect(splitEdgeFade(piece, "start", 25)).toEqual({
      solid: [[25, 50], ...piece.slice(3)],
      fade: [
        [0, 50],
        [10, 50],
        [20, 50],
        [25, 50],
      ],
      fadeAxis: [
        [25, 50],
        [0, 50],
      ],
    });
  });

  it("дуга, повернувшая после края, не гаснет: прозрачность ложится только на хвост у края", () => {
    // From the edge it goes right, then steeply down, like the Washington -> Singapore arc over Siberia.
    const hooked = [
      [0, 0],
      [40, 0],
      [60, 0],
      [80, 100],
    ] as const;

    const split = splitEdgeFade(hooked, "start", 40);

    expect(split.fade).toEqual([
      [0, 0],
      [40, 0],
    ]);
    expect(split.solid).toEqual([
      [40, 0],
      [60, 0],
      [80, 100],
    ]);
  });

  it("кусок короче длины затухания гаснет целиком — от дальнего конца, сплошной части нет", () => {
    expect(splitEdgeFade(piece, "end", 500)).toEqual({
      solid: [],
      fade: piece,
      fadeAxis: [
        [0, 50],
        [100, 50],
      ],
    });
  });
});
