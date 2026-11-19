import { describe, expect, it } from "vitest";

import { layOutCityLabels, type LabelledCity, type LabelMetrics, type PlacedLabel } from "./labelPlacement";

const METRICS: LabelMetrics = { fontSize: 10, gap: 4, dotRadius: 2, clearance: 1 };

// The same ratios as the layout: the test reconstructs the label rectangle from them.
const CHAR_WIDTH_RATIO = 0.62;
const LINE_HEIGHT_RATIO = 1.25;

function city(cityId: string, x: number, y: number, label: string, routeCount = 1): LabelledCity {
  return { cityId, x, y, label, routeCount };
}

/** A label rectangle on the canvas. */
function boxOf(label: PlacedLabel): { left: number; right: number; top: number; bottom: number } {
  const width = label.label.length * METRICS.fontSize * CHAR_WIDTH_RATIO;
  const height = METRICS.fontSize * LINE_HEIGHT_RATIO;
  const left = label.anchor === "start" ? label.x : label.anchor === "end" ? label.x - width : label.x - width / 2;
  return { left, right: left + width, top: label.y - height / 2, bottom: label.y + height / 2 };
}

function overlaps(a: PlacedLabel, b: PlacedLabel): boolean {
  const first = boxOf(a);
  const second = boxOf(b);
  return first.left < second.right && second.left < first.right && first.top < second.bottom && second.top < first.bottom;
}

describe("layOutCityLabels", () => {
  it("свободная точка подписана справа", () => {
    const [label] = layOutCityLabels([city("minsk", 100, 100, "Minsk")], [], METRICS);

    expect(label).toMatchObject({ cityId: "minsk", anchor: "start", y: 100 });
    expect(label.x).toBeGreaterThan(100);
  });

  it("соседние точки получают непересекающиеся подписи", () => {
    const labels = layOutCityLabels(
      [city("minsk", 100, 100, "Minsk"), city("borisov", 108, 98, "Borisov")],
      [],
      METRICS,
    );

    expect(labels).toHaveLength(2);
    expect(overlaps(labels[0], labels[1])).toBe(false);
  });

  it("подпись уходит с линии, проходящей справа от точки", () => {
    // A horizontal arc to the right of the dot would cover the label in the "right" position.
    const arc = [
      [
        [100, 100],
        [300, 100],
      ],
    ] as const;

    const [label] = layOutCityLabels([city("minsk", 100, 100, "Minsk")], [arc], METRICS);

    const box = boxOf(label);
    expect(box.top > 100 || box.bottom < 100 || box.right < 100).toBe(true);
  });

  it("если без линий места нет, подпись всё равно ставится, но не на соседей", () => {
    // A grid of arcs in every direction: any position touches a line.
    const arcs = [
      [
        [
          [0, 100],
          [200, 100],
        ],
      ],
      [
        [
          [100, 0],
          [100, 200],
        ],
      ],
      [
        [
          [0, 0],
          [200, 200],
        ],
      ],
      [
        [
          [0, 200],
          [200, 0],
        ],
      ],
      [
        [
          [0, 90],
          [200, 90],
        ],
      ],
      [
        [
          [0, 110],
          [200, 110],
        ],
      ],
    ] as const;

    const labels = layOutCityLabels([city("minsk", 100, 100, "Minsk")], arcs, METRICS);

    expect(labels).toHaveLength(1);
  });

  it("точка, зажатая чужими точками со всех сторон, остаётся без подписи, а подписи соседей не пересекаются", () => {
    const center = city("center", 100, 100, "Center");
    // Other dots in all eight directions: every position of the center label touches a dot, and
    // dots block the label at the fallback step too (only crossing lines is allowed there).
    const neighbours = [
      [115, 100],
      [85, 100],
      [100, 90],
      [100, 110],
      [115, 90],
      [115, 110],
      [85, 90],
      [85, 110],
    ].map(([x, y], index) => city(`n${index}`, x, y, "X"));

    const labels = layOutCityLabels([center, ...neighbours], [], METRICS);

    expect(labels.map((label) => label.cityId)).not.toContain("center");
    for (const [index, first] of labels.entries()) {
      for (const second of labels.slice(index + 1)) {
        expect(overlaps(first, second)).toBe(false);
      }
    }
  });

  it("первыми раскладываются города, через которые проходит больше маршрутов", () => {
    // Dots one above another closer than a line height: labels on the right would overlap, while
    // the dots themselves do not block each other's right labels, so the right spot is shared by
    // two and goes to the busy one. By id the quiet city would go first, which lets the test tell
    // route priority from key priority.
    const quiet = city("a-quiet", 100, 100, "Quiet", 1);
    const busy = city("z-busy", 100, 108, "Busy", 3);

    const labels = layOutCityLabels([quiet, busy], [], METRICS);
    const labelOf = (cityId: string) => labels.find((label) => label.cityId === cityId);

    expect(labelOf("z-busy")).toMatchObject({ anchor: "start", y: busy.y });
    expect(labelOf("a-quiet")).not.toMatchObject({ anchor: "start", y: quiet.y });
  });

  it("раскладка не зависит от порядка городов на входе", () => {
    const cities = [city("b", 108, 98, "Borisov"), city("a", 100, 100, "Minsk")];

    const straight = layOutCityLabels(cities, [], METRICS);
    const reversed = layOutCityLabels([...cities].reverse(), [], METRICS);

    expect(reversed).toEqual(straight);
  });
});
