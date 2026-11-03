import { describe, expect, it } from "vitest";

import { placeCard, type Box } from "./cardPlacement";

// The map area is 1200x800; the navigation panel is on the left: from (32, 100), 260x400, bottom at 500.
const AREA = { width: 1200, height: 800 };
const CARD = { width: 260, height: 160 };
const PANEL: Box = { left: 32, top: 100, width: 260, height: 400 };
const LAYOUT = { area: AREA, card: CARD, overhangTop: 0, panel: PANEL };

describe("placeCard", () => {
  it("свободное место внутри рамки — карточка встаёт куда просили", () => {
    expect(placeCard({ left: 500, top: 300 }, LAYOUT)).toEqual({ left: 500, top: 300 });
  });

  it("рамка выровнена по панели: не левее её левого края и не выше её верха", () => {
    // The frame corner is not allowed because the panel is there: the nearest spot is right of it, with a 16 gap.
    expect(placeCard({ left: 0, top: 0 }, LAYOUT)).toEqual({ left: 32 + 260 + 16, top: 100 });
    // There is no room left of the panel but there is under it: the left edge matches the panel.
    expect(placeCard({ left: 0, top: 700 }, LAYOUT)).toEqual({ left: 32, top: AREA.height - 32 - CARD.height });
  });

  it("справа и снизу — тот же отступ от края, что у панели слева", () => {
    expect(placeCard({ left: 5000, top: 5000 }, LAYOUT)).toEqual({
      left: AREA.width - 32 - CARD.width,
      top: AREA.height - 32 - CARD.height,
    });
  });

  it("на панель не наезжает: встаёт правее неё или под ней — что ближе", () => {
    // It slightly overlaps the panel from the right: moving it right is closer.
    expect(placeCard({ left: 250, top: 150 }, LAYOUT)).toEqual({ left: 32 + 260 + 16, top: 150 });
    // It overlaps the panel from below: moving it under is closer.
    expect(placeCard({ left: 40, top: 480 }, LAYOUT)).toEqual({ left: 40, top: 100 + 400 + 16 });
  });

  it("выступ над карточкой (ушко) тоже держится внутри рамки", () => {
    const placed = placeCard({ left: 500, top: 0 }, { ...LAYOUT, overhangTop: 18 });

    expect(placed.top - 18).toBe(PANEL.top);
  });

  it("без панели (мобильная раскладка) — рамка с отступом 32 от всех краёв", () => {
    expect(placeCard({ left: -50, top: -50 }, { ...LAYOUT, panel: null })).toEqual({ left: 32, top: 32 });
  });
});
