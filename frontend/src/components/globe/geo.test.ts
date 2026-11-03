import { describe, expect, it } from "vitest";

import { centralAngleRad } from "./geo";

describe("centralAngleRad", () => {
  it("возвращает 0 для совпадающих точек", () => {
    expect(centralAngleRad(55, 37, 55, 37)).toBeCloseTo(0);
  });

  it("возвращает π для антиподов по экватору", () => {
    // (0,0) and (0,180) are opposite points of the equator, central angle = pi.
    expect(centralAngleRad(0, 0, 0, 180)).toBeCloseTo(Math.PI);
  });

  it("возвращает π/2 для четверти экватора", () => {
    expect(centralAngleRad(0, 0, 0, 90)).toBeCloseTo(Math.PI / 2);
  });

  it("симметричен по перестановке точек", () => {
    const ab = centralAngleRad(55, 37, 40, -74);
    const ba = centralAngleRad(40, -74, 55, 37);
    expect(ab).toBeCloseTo(ba);
  });
});
