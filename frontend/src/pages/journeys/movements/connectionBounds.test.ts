import { describe, expect, it } from "vitest";

import { connectionBounds } from "./connectionBounds";

describe("connectionBounds", () => {
  it("охватывает все точки всех дуг", () => {
    const bounds = connectionBounds([
      [
        [
          [10, 40],
          [30, 20],
        ],
      ],
      [
        [
          [50, 60],
          [5, 35],
        ],
      ],
    ]);

    expect(bounds).toEqual({ x: 5, y: 20, width: 45, height: 40 });
  });

  it("без маршрутов подгонять нечего", () => {
    expect(connectionBounds([])).toBeNull();
  });

  it("дуга через антимеридиан лежит у обоих краёв — подгонять нечего", () => {
    const acrossAntimeridian = [
      [
        [990, 200],
        [999, 198],
      ],
      [
        [1, 198],
        [10, 200],
      ],
    ] as const;

    expect(
      connectionBounds([
        [
          [
            [10, 40],
            [30, 20],
          ],
        ],
        acrossAntimeridian,
      ]),
    ).toBeNull();
  });
});
