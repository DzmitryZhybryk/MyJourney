import { describe, expect, it } from "vitest";

import { type LabelBox, resolveLabelVisibility, SHOW_CLEARANCE_PX } from "./labelDeclutter";

const CENTER = { x: 400, y: 300 };
const NONE: ReadonlySet<string> = new Set();

const box = (id: string, left: number, top: number, width = 60, height = 12): LabelBox => ({
  id,
  left,
  top,
  width,
  height,
});

describe("resolveLabelVisibility", () => {
  it("не прячет ничего, когда подписи не пересекаются", () => {
    const hidden = resolveLabelVisibility([box("Ташкент", 100, 100), box("Бишкек", 300, 300)], CENTER, NONE);

    expect(hidden.size).toBe(0);
  });

  it("при пересечении прячет подпись дальше от центра диска", () => {
    // Bishkek is near the center, Tashkent overlaps it but is closer to the edge itself.
    const hidden = resolveLabelVisibility([box("Ташкент", 350, 296), box("Бишкек", 390, 294)], CENTER, NONE);

    expect(hidden).toEqual(new Set(["Ташкент"]));
  });

  it("при равном расстоянии от центра порядок стабилен: выигрывает меньшее имя", () => {
    // The label centers are mirrored about the disk center: distances match bit for bit.
    const hidden = resolveLabelVisibility([box("Бишкек", 390, 300), box("Ташкент", 350, 300)], CENTER, NONE);

    expect(hidden).toEqual(new Set(["Ташкент"]));
  });

  it("гистерезис: спрятанная подпись не возвращается без запаса зазора", () => {
    // There is no overlap anymore but the gap is below SHOW_CLEARANCE_PX: it stays hidden.
    const gap = SHOW_CLEARANCE_PX - 2;
    const hidden = resolveLabelVisibility(
      [box("Бишкек", 400, 300), box("Ташкент", 400 + 60 + gap, 300)],
      CENTER,
      new Set(["Ташкент"]),
    );

    expect(hidden).toEqual(new Set(["Ташкент"]));
  });

  it("гистерезис: подпись возвращается, когда зазор достиг запаса", () => {
    const hidden = resolveLabelVisibility(
      [box("Бишкек", 400, 300), box("Ташкент", 400 + 60 + SHOW_CLEARANCE_PX, 300)],
      CENTER,
      new Set(["Ташкент"]),
    );

    expect(hidden.size).toBe(0);
  });

  it("спрятанная подпись не отнимает место у остальных", () => {
    // Almaty overlaps Bishkek (loses), Tashkent overlaps only Almaty and gets its place: a conflict
    // counts only against ACCEPTED labels.
    const hidden = resolveLabelVisibility(
      [box("Бишкек", 400, 300), box("Алматы", 430, 302), box("Ташкент", 470, 304)],
      CENTER,
      NONE,
    );

    expect(hidden).toEqual(new Set(["Алматы"]));
  });

  it("одна подпись всегда видима", () => {
    const hidden = resolveLabelVisibility([box("Бишкек", 700, 500)], CENTER, new Set(["Бишкек"]));

    expect(hidden.size).toBe(0);
  });

  it("одноимённые города различаются ключами: прячется только проигравший", () => {
    // Two different Springfields (key = name|coordinates): exactly the farther one must hide.
    const hidden = resolveLabelVisibility(
      [box("Спрингфилд|40.0|-89.6", 350, 296), box("Спрингфилд|37.2|-93.3", 390, 294)],
      CENTER,
      NONE,
    );

    expect(hidden).toEqual(new Set(["Спрингфилд|40.0|-89.6"]));
  });
});
